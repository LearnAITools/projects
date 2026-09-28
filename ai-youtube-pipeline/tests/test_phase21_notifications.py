import json
from pathlib import Path
from unittest.mock import MagicMock

from app.automation.automation_manager import AutomationManager
from app.automation.full_automation import FullAutomation
from app.automation.scheduler import AutomationScheduler
from app.content.models import GeneratedContent, Scene, YouTubeMetadata
from app.pipeline.orchestrator import PipelineOrchestrator


VALID_CONTENT = GeneratedContent(
    topic="AI tools",
    title="AI Tools for Developers",
    hook="A practical guide to AI tools.",
    script="This video covers useful AI tools.",
    scenes=[
        Scene(
            scene_number=1,
            narration="Use an AI assistant for repetitive coding tasks.",
            visual_description="A developer reviewing code with an AI assistant.",
            duration_seconds=5,
        )
    ],
    youtube=YouTubeMetadata(
        title="AI Tools for Developers",
        description="Useful AI tools for developers.",
        tags=["ai", "development"],
    ),
)


def test_scheduler_persists_jobs_to_disk(tmp_path):
    schedule_path = tmp_path / "scheduler.json"
    scheduler = AutomationScheduler(schedule_file=schedule_path)
    job = scheduler.schedule(topic="AI tools", interval_seconds=60, run_immediately=True)

    reloaded = AutomationScheduler(schedule_file=schedule_path)

    assert len(reloaded.jobs) == 1
    assert reloaded.jobs[0].job_id == job.job_id
    assert reloaded.jobs[0].topic == "AI tools"


def test_full_automation_notifies_on_completion(tmp_path):
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "jobs"))
    manager = AutomationManager(history_path=tmp_path / "history.json")
    notifier = MagicMock()
    video_path = tmp_path / "video.mp4"
    video_path.write_bytes(b"video")

    mock_content_gen = MagicMock()
    mock_content_gen.generate.return_value = VALID_CONTENT
    mock_image_gen = MagicMock()
    mock_image_gen.generate.return_value = [tmp_path / "scene_001.png"]
    mock_narration_gen = MagicMock()
    mock_narration_gen.generate.return_value = [tmp_path / "scene_001.wav"]
    mock_video_builder = MagicMock()
    mock_video_builder.build.return_value = video_path
    mock_you_tube = MagicMock()
    mock_you_tube.settings.youtube_category_id = "22"
    mock_you_tube.settings.youtube_privacy_status = "private"
    mock_you_tube.upload_video.return_value = type(
        "UploadResult",
        (),
        {"success": True, "video_id": "video_123", "upload_url": "https://youtu.be/video_123", "dry_run": True, "message": "ok"},
    )()

    automation = FullAutomation(
        orchestrator=orchestrator,
        history_manager=manager,
        content_gen=mock_content_gen,
        image_gen=mock_image_gen,
        narration_gen=mock_narration_gen,
        video_builder=mock_video_builder,
        youtube_client=mock_you_tube,
        notifier=notifier,
    )
    automation.automation_pipeline.generator.generate.return_value = VALID_CONTENT

    result = automation.run_job({"job_id": "notify_001", "topic": "AI tools"})

    assert result["status"] == "COMPLETED"
    notifier.notify.assert_called_with(
        job_id="notify_001",
        topic="AI tools",
        status="COMPLETED",
        message="Job completed successfully.",
        payload={"video_id": "video_123", "watch_url": "https://youtu.be/video_123"},
    )
