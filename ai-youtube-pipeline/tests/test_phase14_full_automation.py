from unittest.mock import MagicMock, patch

from app.automation.automation_manager import AutomationManager
from app.automation.full_automation import FullAutomation
from app.automation.job_runner import JobRunner
from app.automation.scheduler import AutomationScheduler
from app.automation.topic_queue import TopicQueue
from app.content.models import GeneratedContent, Scene, YouTubeMetadata
from app.pipeline.orchestrator import PipelineOrchestrator


VALID_CONTENT = GeneratedContent(
    topic="AI tools",
    title="5 AI Tools Every Developer Should Know",
    hook="AI is changing how developers ship faster.",
    script="This video covers five practical AI tools.",
    scenes=[
        Scene(
            scene_number=1,
            narration="First, let's talk about AI coding assistants.",
            visual_description="Developer using AI coding assistant on laptop.",
            duration_seconds=8,
        ),
    ],
    youtube=YouTubeMetadata(
        title="5 AI Tools Every Developer Should Know",
        description="A practical overview of AI tools.",
        tags=["ai", "developer tools"],
    ),
)


def test_full_automation_executes_all_pipeline_stages(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "pipeline_jobs"))
    runner = JobRunner(history_manager=manager)

    mock_content_gen = MagicMock()
    mock_content_gen.generate.return_value = VALID_CONTENT
    mock_image_gen = MagicMock()
    mock_image_gen.generate.return_value = None
    mock_narration_gen = MagicMock()
    mock_narration_gen.generate.return_value = None
    mock_video_builder = MagicMock()
    mock_video_builder.build.return_value = None

    automation = FullAutomation(
        orchestrator=orchestrator,
        history_manager=manager,
        content_gen=mock_content_gen,
        image_gen=mock_image_gen,
        narration_gen=mock_narration_gen,
        video_builder=mock_video_builder,
    )

    scheduler = AutomationScheduler()
    queue = TopicQueue(history_manager=manager)
    runner.scheduler = scheduler
    runner.queue = queue

    scheduler.schedule(topic="AI tools", interval_seconds=60, run_immediately=True)
    queue.add_topics(["AI tools"])

    scheduled_job = runner.run_next_job()
    result = automation.run_job(scheduled_job)

    assert result is not None
    assert result["job_id"] == scheduled_job["job_id"]
    assert result["status"] == "COMPLETED"


def test_full_automation_marks_job_completed_in_history(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "pipeline_jobs"))

    mock_content_gen = MagicMock()
    mock_content_gen.generate.return_value = VALID_CONTENT
    mock_image_gen = MagicMock()
    mock_image_gen.generate.return_value = None
    mock_narration_gen = MagicMock()
    mock_narration_gen.generate.return_value = None
    mock_video_builder = MagicMock()
    mock_video_builder.build.return_value = None

    automation = FullAutomation(
        orchestrator=orchestrator,
        history_manager=manager,
        content_gen=mock_content_gen,
        image_gen=mock_image_gen,
        narration_gen=mock_narration_gen,
        video_builder=mock_video_builder,
    )

    scheduled_job = {
        "job_id": "full_test_001",
        "topic": "Python tips",
        "status": "SCHEDULED",
        "timestamp": "2026-09-02T10:00:00",
    }

    result = automation.run_job(scheduled_job)

    job = orchestrator.load_job(scheduled_job["job_id"])
    assert job.status.value == "COMPLETED"


def test_full_automation_returns_none_on_invalid_job(tmp_path):
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "pipeline_jobs"))
    automation = FullAutomation(orchestrator=orchestrator)

    result = automation.run_job(None)
    assert result is None
