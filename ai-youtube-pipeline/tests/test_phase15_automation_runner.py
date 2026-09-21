import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.automation.automation_manager import AutomationManager
from app.automation.automation_runner import AutomationRunner
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


def test_automation_runner_checks_for_due_jobs(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "pipeline_jobs"))
    job_runner = JobRunner(history_manager=manager)

    scheduler = AutomationScheduler()
    queue = TopicQueue(history_manager=manager)
    job_runner.scheduler = scheduler
    job_runner.queue = queue

    scheduler.schedule(topic="AI tools", interval_seconds=60, run_immediately=True)
    queue.add_topics(["AI tools"])

    from app.automation.full_automation import FullAutomation

    mock_automation = MagicMock(spec=FullAutomation)
    mock_automation.run_job.return_value = {
        "job_id": "test_job",
        "topic": "AI tools",
        "status": "COMPLETED",
    }

    runner = AutomationRunner(job_runner=job_runner, automation=mock_automation)
    results = runner.run_once()

    assert results is not None
    assert len(results) > 0
    assert results[0]["status"] == "COMPLETED"


def test_automation_runner_returns_empty_when_no_jobs_due(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "pipeline_jobs"))
    job_runner = JobRunner(history_manager=manager)

    scheduler = AutomationScheduler()
    queue = TopicQueue(history_manager=manager)
    job_runner.scheduler = scheduler
    job_runner.queue = queue

    scheduler.schedule(
        topic="AI tools",
        interval_seconds=3600,
        next_run_at=datetime.utcnow() + timedelta(hours=1),
    )
    queue.add_topics(["AI tools"])

    from app.automation.full_automation import FullAutomation

    runner = AutomationRunner(job_runner=job_runner, automation=MagicMock(spec=FullAutomation))
    results = runner.run_once()

    assert results == []


def test_automation_runner_tracks_execution_stats(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "pipeline_jobs"))
    job_runner = JobRunner(history_manager=manager)

    scheduler = AutomationScheduler()
    queue = TopicQueue(history_manager=manager)
    job_runner.scheduler = scheduler
    job_runner.queue = queue

    scheduler.schedule(topic="AI tools", interval_seconds=60, run_immediately=True)
    queue.add_topics(["AI tools"])

    from app.automation.full_automation import FullAutomation

    mock_automation = MagicMock(spec=FullAutomation)
    mock_automation.run_job.return_value = {
        "job_id": "test_job",
        "topic": "AI tools",
        "status": "COMPLETED",
    }

    runner = AutomationRunner(job_runner=job_runner, automation=mock_automation)
    runner.run_once()
    stats = runner.get_stats()

    assert stats["total_runs"] == 1
    assert stats["successful_jobs"] == 1
    assert stats["failed_jobs"] == 0
