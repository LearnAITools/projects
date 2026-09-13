from app.automation.automation_executor import AutomationExecutor
from app.automation.automation_manager import AutomationManager
from app.automation.job_runner import JobRunner
from app.automation.scheduler import AutomationScheduler
from app.automation.topic_queue import TopicQueue
from app.pipeline.orchestrator import PipelineOrchestrator


def test_automation_executor_creates_pipeline_job(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "pipeline_jobs"))
    runner = JobRunner(history_manager=manager)
    executor = AutomationExecutor(
        orchestrator=orchestrator, history_manager=manager
    )

    scheduler = AutomationScheduler()
    queue = TopicQueue(history_manager=manager)
    runner.scheduler = scheduler
    runner.queue = queue

    scheduler.schedule(topic="AI tools", interval_seconds=60, run_immediately=True)
    queue.add_topics(["AI tools"])

    scheduled_job = runner.run_next_job()
    result = executor.execute(scheduled_job)

    assert result is not None
    assert result["topic"] == "AI tools"
    assert result["status"] == "CREATED"


def test_automation_executor_records_job_in_history(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "pipeline_jobs"))
    executor = AutomationExecutor(
        orchestrator=orchestrator, history_manager=manager
    )

    scheduled_job = {
        "job_id": "test_job_001",
        "topic": "AI tools",
        "status": "SCHEDULED",
        "timestamp": "2026-09-02T10:00:00",
    }
    executor.execute(scheduled_job)

    history = manager.history.list_jobs()
    assert len(history) == 1
    assert history[0]["job_id"] == "test_job_001"
    assert history[0]["topic"] == "AI tools"


def test_automation_executor_raises_on_invalid_scheduled_job(tmp_path):
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "pipeline_jobs"))
    executor = AutomationExecutor(orchestrator=orchestrator)

    try:
        executor.execute(None)
        assert False, "Expected ValueError for None job"
    except (ValueError, TypeError):
        pass
