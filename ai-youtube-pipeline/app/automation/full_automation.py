"""Full automation workflow integrating all pipeline stages."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.audio.narration_generator import NarrationGenerator
from app.automation.automation_executor import AutomationExecutor
from app.automation.automation_manager import AutomationManager
from app.automation.automation_pipeline import AutomationPipeline
from app.content.content_generator import ContentGenerator
from app.images.image_generator import ImageGenerator
from app.pipeline.orchestrator import PipelineOrchestrator
from app.pipeline.orchestrator import JobStatus
from app.video.video_builder import VideoBuilder
from app.youtube.youtube_client import YouTubeClient
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

        logger.info(f"Full automation starting for job {job_id}: {topic}")
        current_stage = "content"

        try:
            pipeline_result = self.automation_pipeline.run(scheduled_job)
            if not pipeline_result or not pipeline_result.get("content_generated"):
                logger.error(f"Content generation failed for job {job_id}")
                self.orchestrator.update_job_status(job_id, JobStatus.FAILED)
                return {
                    "job_id": job_id,
                    "topic": topic,
                    "status": "FAILED",
                }

            content = self.orchestrator.load_content(job_id)
            current_stage = "images"
            logger.info(f"Generating images for job {job_id}")
            image_paths = self.image_gen.generate(job_id, content)
            self.orchestrator.update_job_status(job_id, JobStatus.IMAGES_GENERATED)

            current_stage = "audio"
            logger.info(f"Generating narration for job {job_id}")
            audio_paths = self.narration_gen.generate(job_id, content)
            self.orchestrator.update_job_status(job_id, JobStatus.AUDIO_GENERATED)

            current_stage = "video"
            logger.info(f"Building video for job {job_id}")
            video_path = self.video_builder.build(
                job_id,
                content,
                image_paths=image_paths,
                audio_paths=audio_paths,
            )
            self.orchestrator.update_job_status(job_id, JobStatus.VIDEO_GENERATED)

            upload_result = None
            if video_path is not None:
                current_stage = "youtube"
                upload_result = self.youtube_client.upload_video(
                    video_path=video_path,
                    title=content.youtube.title,
                    description=content.youtube.description,
                    tags=content.youtube.tags,
                    category_id=self.youtube_client.settings.youtube_category_id,
                    privacy_status=self.youtube_client.settings.youtube_privacy_status,
                )
                if not upload_result.success:
                    raise RuntimeError(upload_result.message)
                self.orchestrator.update_job_status(
                    job_id,
                    JobStatus.UPLOADED,
                    details={
                        "youtube_video_id": upload_result.video_id,
                        "youtube_upload_url": upload_result.upload_url,
                        "youtube_dry_run": upload_result.dry_run,
                    },
                )

            upload_details = {}
            if upload_result:
                upload_details = {
                    "youtube_video_id": upload_result.video_id,
                    "youtube_upload_url": upload_result.upload_url,
                    "youtube_dry_run": upload_result.dry_run,
                }
            self.orchestrator.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                details=upload_details,
            )
            self.history_manager.history.record(
                job_id=job_id,
                topic=topic,
                status="COMPLETED",
                attempts=0,
            )

            logger.info(f"Full automation completed for job {job_id}")

            return {
                "job_id": job_id,
                "topic": topic,
                "status": "COMPLETED",
                "youtube_video_id": upload_result.video_id if upload_result else None,
                "youtube_upload_url": upload_result.upload_url if upload_result else None,
            }

        except Exception as exc:
            logger.error(f"Full automation failed during {current_stage} for job {job_id}: {exc}")
            self.orchestrator.update_job_status(
                job_id,
                JobStatus.FAILED,
                stage=current_stage,
                error=str(exc),
            )
            return {
                "job_id": job_id,
                "topic": topic,
                "status": "FAILED",
            }
