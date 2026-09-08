from app.automation.automation_manager import AutomationManager
from app.automation.job_history import JobHistory


def test_job_history_tracks_completed_jobs(tmp_path):
    history = JobHistory(history_path=tmp_path / "history.json")

    history.record(job_id="job_001", topic="AI tools", status="COMPLETED")
    items = history.list_jobs()

    assert len(items) == 1
    assert items[0]["topic"] == "AI tools"
    assert items[0]["status"] == "COMPLETED"


def test_automation_manager_detects_duplicate_topics(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    manager.history.record(job_id="job_001", topic="AI tools", status="COMPLETED")

    assert manager.is_duplicate_topic("AI tools") is True
    assert manager.is_duplicate_topic("ai tools") is True


def test_automation_manager_retry_policy_uses_attempts(tmp_path):
    manager = AutomationManager(history_path=tmp_path / "history.json")
    manager.history.record(job_id="job_retry", topic="AI tools", status="FAILED", attempts=1)

    assert manager.should_retry("job_retry", max_retries=3) is True
    assert manager.should_retry("job_retry", max_retries=1) is False
