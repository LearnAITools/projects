from datetime import datetime

from app.automation.automation_manager import AutomationManager
from app.automation.job_runner import JobRunner
from app.automation.scheduler import AutomationScheduler
from app.automation.topic_queue import TopicQueue


def test_job_runner_executes_scheduled_job(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    scheduler = AutomationScheduler()
    queue = TopicQueue(history_manager=manager)
    runner = JobRunner(
        history_manager=manager, scheduler=scheduler, queue=queue
    )

    scheduler.schedule(
        topic="AI tools", interval_seconds=60, run_immediately=True
    )
    queue.add_topics(["AI tools", "Prompt engineering"])

    result = runner.run_next_job()

    assert result is not None
    assert result["topic"] == "AI tools"
    assert result["status"] == "SCHEDULED"


def test_job_runner_returns_none_when_no_jobs_due(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    scheduler = AutomationScheduler()
    queue = TopicQueue(history_manager=manager)
    runner = JobRunner(
        history_manager=manager, scheduler=scheduler, queue=queue
    )

    scheduler.schedule(
        topic="AI tools",
        interval_seconds=60,
        next_run_at=datetime.utcnow(),
        run_immediately=False,
    )

    result = runner.run_next_job(now=datetime.utcnow())

    assert result is None


def test_job_runner_advances_scheduler_after_job(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    scheduler = AutomationScheduler()
    queue = TopicQueue(history_manager=manager)
    runner = JobRunner(
        history_manager=manager, scheduler=scheduler, queue=queue
    )

    scheduled = scheduler.schedule(
        topic="AI tools", interval_seconds=60, run_immediately=True
    )
    queue.add_topics(["AI tools"])

    runner.run_next_job()

    due = scheduler.get_due_jobs(now=datetime.utcnow())
    assert scheduled not in due
