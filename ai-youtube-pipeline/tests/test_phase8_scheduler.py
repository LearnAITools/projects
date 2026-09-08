from datetime import datetime, timedelta

from app.automation.scheduler import AutomationScheduler, ScheduledJob


def test_scheduler_rejects_invalid_interval():
    scheduler = AutomationScheduler()

    try:
        scheduler.schedule(topic="AI tools", interval_seconds=0)
        assert False, "Expected ValueError for invalid interval"
    except ValueError:
        pass


def test_scheduler_marks_job_due_when_interval_elapsed():
    scheduler = AutomationScheduler()
    scheduled = scheduler.schedule(
        topic="AI tools",
        interval_seconds=60,
        next_run_at=datetime.utcnow() - timedelta(seconds=61),
    )

    due = scheduler.get_due_jobs(now=datetime.utcnow())
    assert scheduled.job_id in [job.job_id for job in due]


def test_scheduler_can_run_immediately():
    scheduler = AutomationScheduler()
    scheduled = scheduler.schedule(topic="AI tools", interval_seconds=60, run_immediately=True)

    assert scheduled.run_immediately is True
    assert scheduled.next_run_at is not None
