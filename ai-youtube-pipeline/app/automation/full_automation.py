"""Full automation workflow integrating all pipeline stages."""

from __future__ import annotations

import json
import time
from uuid import uuid4
from typing import Any, Dict, Optional
from datetime import datetime, timedelta, timezone

from app.audio.narration_generator import NarrationGenerator
from app.automation.automation_executor import AutomationExecutor
from app.automation.automation_manager import AutomationManager
from app.automation.automation_pipeline import AutomationPipeline
from app.automation.notifier import ConsoleNotifier, DurableNotifier, Notifier
from app.automation.observability import Observability
from app.content.content_generator import ContentGenerator
from app.content.content_generator import ContentValidationError
from app.content.quality import check_content_quality
from app.images.image_generator import ImageGenerator
from app.pipeline.orchestrator import PipelineOrchestrator
from app.pipeline.orchestrator import JobStatus
from app.video.video_builder import VideoBuilder
from app.video.media_enhancements import (
    CaptionGenerator,
    MusicMixer,
    SceneTimingValidator,
    ThumbnailGenerator,
    write_media_manifest,
)
from app.youtube.youtube_client import YouTubeClient, YouTubeUploadResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FullAutomation:
    """
    Execute scheduled jobs through all pipeline stages:
    content generation → images → narration → video → completion.
    """

    def __init__(
        self,
        orchestrator: Optional[PipelineOrchestrator] = None,
        history_manager: Optional[AutomationManager] = None,
        content_gen: Optional[ContentGenerator] = None,
        image_gen: Optional[ImageGenerator] = None,
        narration_gen: Optional[NarrationGenerator] = None,
        video_builder: Optional[VideoBuilder] = None,
        youtube_client: Optional[YouTubeClient] = None,
        notifier: Optional[Notifier] = None,
        max_retries: int = 3,
        music_path: Optional[str] = None,
        music_volume: float = 0.15,
    ) -> None:
        self.orchestrator = orchestrator or PipelineOrchestrator()
        self.history_manager = history_manager or AutomationManager()
        self.executor = AutomationExecutor(
            orchestrator=self.orchestrator,
            history_manager=self.history_manager,
        )
        self.automation_pipeline = AutomationPipeline(
            orchestrator=self.orchestrator,
            generator=content_gen or ContentGenerator(),
            history_manager=self.history_manager,
        )
        self.image_gen = image_gen or ImageGenerator()
        self.narration_gen = narration_gen or NarrationGenerator()
        self.video_builder = video_builder or VideoBuilder()
        self.youtube_client = youtube_client or YouTubeClient()
        self.notifier = notifier or DurableNotifier(
            ConsoleNotifier(),
            notification_path=self.orchestrator.base_dir / "notifications.json",
        )
        self.observability = Observability(self.orchestrator.base_dir.parent)
        if max_retries <= 0:
            raise ValueError("max_retries must be greater than zero")
        self.max_retries = max_retries
        self.music_path = music_path
        self.music_volume = music_volume

    @staticmethod
    def _stage_number(stage: Optional[str]) -> int:
        return {"content": 0, "images": 1, "audio": 2, "video": 3, "youtube": 4}.get(
            stage or "", -1
        )

    def _notify_safely(self, **kwargs: Any) -> None:
        if self.notifier is None:
            return
        try:
            self.notifier.notify(**kwargs)
        except Exception as exc:
            logger.error("Notification failure for job %s: %s", kwargs.get("job_id"), exc)

    def _observe(self, **kwargs: Any) -> None:
        try:
            self.observability.record_event(**kwargs)
        except Exception as exc:
            logger.warning("Observability failure for job %s: %s", kwargs.get("job_id"), exc)

    def run_job(self, scheduled_job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute a scheduled job through all pipeline stages.
        
        Args:
            scheduled_job: Dict with job_id, topic, status, timestamp from JobRunner
            
        Returns:
            Dict with final job status or None if job is invalid
        """
        if not scheduled_job:
            logger.error("Cannot run full automation with None job")
            return None

        job_id = scheduled_job.get("job_id")
        topic = scheduled_job.get("topic")
        video_format = scheduled_job.get("format", "LONG_FORM")
        publish_at = scheduled_job.get("publish_at")

        logger.info(f"Full automation starting for job {job_id}: {topic}")
        current_stage = "content"
        started_at = time.perf_counter()
        correlation_id = str(uuid4())
        self._observe(
            event="job_started",
            job_id=job_id,
            stage=current_stage,
            status="STARTED",
            correlation_id=correlation_id,
        )

        try:
            try:
                existing_state = json.loads(
                    self.orchestrator._state_path(job_id).read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                existing_state = {}
            if existing_state.get("status") == JobStatus.COMPLETED.value:
                return {
                    "job_id": job_id,
                    "topic": topic,
                    "format": video_format,
                    "publish_at": publish_at,
                    "status": "COMPLETED",
                    "youtube_video_id": existing_state.get("youtube_video_id"),
                    "youtube_upload_url": existing_state.get("youtube_upload_url"),
                }
            pipeline_result = self.automation_pipeline.run(scheduled_job)
            if not pipeline_result or not pipeline_result.get("content_generated"):
                raise ContentValidationError(
                    (pipeline_result or {}).get("error", "Content generation failed")
                )

            content = self.orchestrator.load_content(job_id)
            persisted_job = self.orchestrator.load_job(job_id)
            quality_report = check_content_quality(content)
            if not quality_report.passed:
                message = "; ".join(quality_report.errors)
                self.orchestrator.update_job_status(
                    job_id,
                    JobStatus.REJECTED,
                    stage="content_quality",
                    error=message,
                    details={
                        "quality_passed": False,
                        "quality_issues": quality_report.issues,
                        "moderation_flags": quality_report.moderation_flags,
                        "publishable": False,
                    },
                )
                return {"job_id": job_id, "topic": topic, "status": "REJECTED", "error": message}
            self.orchestrator.update_job_status(
                job_id,
                persisted_job.status,
                details={
                    "quality_passed": True,
                    "publishable": persisted_job.approval_status != "rejected",
                },
            )
            if self.orchestrator.load_job(job_id).approval_status == "rejected":
                return {
                    "job_id": job_id,
                    "topic": topic,
                    "status": "REJECTED",
                    "error": "Content was rejected and must be revised before publishing",
                }
            privacy_status = self.youtube_client.settings.youtube_privacy_status
            if privacy_status != "private":
                approval_status = self.orchestrator.load_job(job_id).approval_status
                if approval_status != "approved":
                    self.orchestrator.update_job_status(
                        job_id,
                        JobStatus.APPROVAL_PENDING,
                        stage="approval",
                        details={"publishable": False},
                    )
                    return {
                        "job_id": job_id,
                        "topic": topic,
                        "status": "AWAITING_APPROVAL",
                        "approval_status": approval_status or "pending",
                    }
            failed_stage = persisted_job.failed_stage
            current_stage = "images"
            logger.info(f"Generating images for job {job_id}")
            image_paths = self.image_gen.generate(job_id, content)
            if self._stage_number(failed_stage) <= self._stage_number("images"):
                self.orchestrator.update_job_status(job_id, JobStatus.IMAGES_GENERATED)

            current_stage = "audio"
            logger.info(f"Generating narration for job {job_id}")
            audio_paths = self.narration_gen.generate(job_id, content)
            if self._stage_number(failed_stage) <= self._stage_number("audio"):
                self.orchestrator.update_job_status(job_id, JobStatus.AUDIO_GENERATED)

            current_stage = "video"
            logger.info(f"Building video for job {job_id}")
            video_path = self.video_builder.build(
                job_id,
                content,
                image_paths=image_paths,
                audio_paths=audio_paths,
            )
            if self._stage_number(failed_stage) <= self._stage_number("video"):
                self.orchestrator.update_job_status(job_id, JobStatus.VIDEO_GENERATED)

            if video_path is not None:
                timing = SceneTimingValidator().validate(content)
                if not timing.passed:
                    raise ValueError("; ".join(timing.issues))
                image_for_thumbnail = (
                    image_paths[0]
                    if image_paths and isinstance(image_paths[0], __import__("pathlib").Path)
                    else None
                )
                if self.music_path:
                    mixed_path = self.orchestrator.base_dir / job_id / "video_with_music.mp4"
                    video_path = MusicMixer().mix(
                        video_path,
                        __import__("pathlib").Path(self.music_path),
                        mixed_path,
                        volume=self.music_volume,
                    )
                thumbnail_path = ThumbnailGenerator().generate(
                    content.youtube.title,
                    image_for_thumbnail,
                    self.orchestrator.base_dir / job_id / "thumbnail.jpg",
                )
                caption_path = CaptionGenerator().generate(
                    content,
                    self.orchestrator.base_dir / job_id / "captions.srt",
                )
                manifest_path = write_media_manifest(
                    self.orchestrator.base_dir / job_id / "media_manifest.json",
                    content,
                    video_path,
                    thumbnail_path=thumbnail_path,
                    caption_path=caption_path,
                )
                self.orchestrator.update_job_status(
                    job_id,
                    self.orchestrator.load_job(job_id).status,
                    details={
                        "thumbnail_path": str(thumbnail_path),
                        "caption_path": str(caption_path),
                        "media_manifest_path": str(manifest_path),
                        "media_duration_seconds": timing.total_duration_seconds,
                    },
                )

            upload_result = None
            if video_path is not None:
                current_stage = "youtube"
                state_path = self.orchestrator._state_path(job_id)
                upload_state_path = state_path.parent / "upload_state.json"
                upload_result = None
                if isinstance(self.youtube_client, YouTubeClient):
                    upload_result = self.youtube_client.recover_upload(upload_state_path)
                if upload_result is None and state_path.exists():
                    try:
                        persisted_state = json.loads(state_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        persisted_state = {}
                    if persisted_state.get("youtube_video_id"):
                        upload_result = YouTubeUploadResult(
                            success=True,
                            message="Recovered confirmed upload from job state.",
                            dry_run=bool(persisted_state.get("youtube_dry_run", False)),
                            video_id=persisted_state["youtube_video_id"],
                            upload_url=persisted_state.get("youtube_upload_url"),
                        )
                if upload_result is None:
                    if isinstance(self.youtube_client, YouTubeClient):
                        self.youtube_client.set_upload_context(
                            upload_state_path, idempotency_key=job_id
                        )
                    self.orchestrator.update_job_status(
                        job_id,
                        JobStatus.VIDEO_GENERATED,
                        details={
                            "upload_in_progress": True,
                            "upload_idempotency_key": job_id,
                        },
                    )
                upload_kwargs = {
                    "video_path": video_path,
                    "title": content.youtube.title,
                    "description": content.youtube.description,
                    "tags": content.youtube.tags,
                    "category_id": self.youtube_client.settings.youtube_category_id,
                    "privacy_status": self.youtube_client.settings.youtube_privacy_status,
                }
                if publish_at:
                    upload_kwargs["scheduled_publish_time"] = publish_at
                if upload_result is None:
                    upload_result = self.youtube_client.upload_video(**upload_kwargs)
                if not upload_result.success:
                    raise RuntimeError(upload_result.message)
                self.orchestrator.update_job_status(
                    job_id,
                    JobStatus.UPLOADED,
                    details={
                        "youtube_video_id": upload_result.video_id,
                        "youtube_upload_url": upload_result.upload_url,
                        "youtube_dry_run": upload_result.dry_run,
                        "upload_in_progress": False,
                        "upload_confirmed": bool(upload_result.video_id),
                        "upload_idempotency_key": job_id,
                    },
                )

            upload_details = {}
            if upload_result:
                upload_details = {
                    "youtube_video_id": upload_result.video_id,
                    "youtube_upload_url": upload_result.upload_url,
                    "youtube_dry_run": upload_result.dry_run,
                    "upload_in_progress": False,
                    "upload_confirmed": bool(upload_result.video_id),
                    "upload_idempotency_key": job_id,
                }
            self.orchestrator.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                details={
                    **upload_details,
                    "attempts": persisted_job.attempts,
                    "next_retry_at": None,
                    "failed_stage": None,
                    "last_error": None,
                },
            )
            self.history_manager.history.record(
                job_id=job_id,
                topic=topic,
                status="COMPLETED",
                attempts=persisted_job.attempts,
                video_format=video_format,
            )

            logger.info(f"Full automation completed for job {job_id}")
            self._notify_safely(
                    job_id=job_id,
                    topic=topic,
                    status="COMPLETED",
                    message="Job completed successfully.",
                    payload={
                        "video_id": upload_result.video_id if upload_result else None,
                        "watch_url": upload_result.upload_url if upload_result else None,
                    },
                )

            self._observe(
                event="job_completed",
                job_id=job_id,
                stage="youtube" if upload_result else "video",
                status="COMPLETED",
                duration_seconds=time.perf_counter() - started_at,
                correlation_id=correlation_id,
                fields={
                    "retry_count": persisted_job.attempts,
                    "upload_outcome": "confirmed" if upload_result else "skipped",
                    "provider_usage": {
                        "image": getattr(getattr(self.image_gen, "provider", None), "last_usage", {}),
                        "voice": getattr(getattr(self.narration_gen, "provider", None), "last_usage", {}),
                    },
                },
            )

            return {
                "job_id": job_id,
                "topic": topic,
                "format": video_format,
                "publish_at": publish_at,
                "status": "COMPLETED",
                "youtube_video_id": upload_result.video_id if upload_result else None,
                "youtube_upload_url": upload_result.upload_url if upload_result else None,
            }

        except Exception as exc:
            logger.error(f"Full automation failed during {current_stage} for job {job_id}: {exc}")
            try:
                previous_attempts = self.orchestrator.load_job(job_id).attempts
            except FileNotFoundError:
                previous_attempts = self.history_manager.get_attempts(job_id)
            attempts = previous_attempts + 1
            retryable = (
                self.history_manager.is_transient_error(exc)
                and attempts < self.max_retries
            )
            retry_at = None
            if retryable:
                retry_at = datetime.now(timezone.utc) + timedelta(
                    seconds=self.history_manager.retry_delay_seconds(attempts)
                )
            self.history_manager.record_attempt(job_id, attempts)
            self.orchestrator.update_job_status(
                job_id,
                JobStatus.FAILED,
                stage=current_stage,
                error=str(exc),
                details={
                    "attempts": attempts,
                    "next_retry_at": retry_at.isoformat() if retry_at else None,
                    "failed_stage": current_stage,
                    "last_error": str(exc),
                    "retryable": retryable,
                },
            )
            self._notify_safely(
                job_id=job_id,
                topic=topic,
                status="FAILED",
                message=f"Job failed during {current_stage}.",
                payload={"stage": current_stage, "error": str(exc)},
            )
            self._observe(
                event="job_failed",
                job_id=job_id,
                stage=current_stage,
                status="FAILED",
                duration_seconds=time.perf_counter() - started_at,
                correlation_id=correlation_id,
                fields={"retry_count": attempts, "upload_outcome": "failed"},
            )
            return {
                "job_id": job_id,
                "topic": topic,
                "status": "FAILED",
                "attempts": attempts,
                "failed_stage": current_stage,
                "retryable": retryable,
                "next_retry_at": retry_at.isoformat() if retry_at else None,
            }
