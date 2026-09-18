from unittest.mock import patch

from app.automation.automation_manager import AutomationManager
from app.automation.automation_pipeline import AutomationPipeline
from app.automation.job_runner import JobRunner
from app.automation.scheduler import AutomationScheduler
from app.automation.topic_queue import TopicQueue
from app.content.content_generator import ContentGenerator
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


def test_automation_pipeline_runs_job_through_content_generation(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "pipeline_jobs"))
    generator = ContentGenerator()
    runner = JobRunner(history_manager=manager)
    pipeline = AutomationPipeline(
        orchestrator=orchestrator,
        generator=generator,
        history_manager=manager,
    )

    scheduler = AutomationScheduler()
    queue = TopicQueue(history_manager=manager)
    runner.scheduler = scheduler
    runner.queue = queue

    scheduler.schedule(topic="AI tools", interval_seconds=60, run_immediately=True)
    queue.add_topics(["AI tools"])

    scheduled_job = runner.run_next_job()
    
    with patch.object(generator, "generate", return_value=VALID_CONTENT):
        result = pipeline.run(scheduled_job)

    assert result is not None
    assert result["job_id"] == scheduled_job["job_id"]
    assert result["topic"] == "AI tools"
    assert result["content_generated"] is True


def test_automation_pipeline_updates_pipeline_job_status(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "pipeline_jobs"))
    generator = ContentGenerator()
    pipeline = AutomationPipeline(
        orchestrator=orchestrator,
        generator=generator,
        history_manager=manager,
    )

    scheduled_job = {
        "job_id": "test_job_002",
        "topic": "Prompt engineering",
        "status": "SCHEDULED",
        "timestamp": "2026-09-02T10:00:00",
    }
    
    with patch.object(generator, "generate", return_value=VALID_CONTENT):
        result = pipeline.run(scheduled_job)

    job = orchestrator.load_job(scheduled_job["job_id"])
    assert job.status.value == "CONTENT_GENERATED"


def test_automation_pipeline_records_completion_in_history(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "pipeline_jobs"))
    generator = ContentGenerator()
    pipeline = AutomationPipeline(
        orchestrator=orchestrator,
        generator=generator,
        history_manager=manager,
    )

    scheduled_job = {
        "job_id": "test_job_003",
        "topic": "LLM workflows",
        "status": "SCHEDULED",
        "timestamp": "2026-09-02T10:00:00",
    }
    
    with patch.object(generator, "generate", return_value=VALID_CONTENT):
        pipeline.run(scheduled_job)

    history = manager.history.list_jobs()
    topic_records = manager.history.find_by_topic("LLM workflows")
    assert len(topic_records) >= 1
    assert topic_records[0]["topic"] == "LLM workflows"

