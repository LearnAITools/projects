import json

from app.automation.job_monitor import JobMonitor
from app.main import build_parser


def write_state(data_dir, job_id, status, **extra):
    job_dir = data_dir / job_id
    job_dir.mkdir()
    state = {"job_id": job_id, "topic": "AI tools", "status": status, **extra}
    (job_dir / "job_state.json").write_text(json.dumps(state), encoding="utf-8")


def test_monitor_lists_jobs_and_summarizes_statuses(tmp_path):
    write_state(tmp_path, "job_001", "COMPLETED")
    write_state(tmp_path, "job_002", "FAILED", stage="images", error="timeout")

    monitor = JobMonitor(tmp_path)

    assert [job["job_id"] for job in monitor.list_jobs()] == ["job_001", "job_002"]
    assert monitor.summary() == {
        "total": 2,
        "by_status": {"COMPLETED": 1, "FAILED": 1},
    }


def test_monitor_returns_job_details_without_mutating_state(tmp_path):
    write_state(tmp_path, "job_001", "FAILED", stage="audio", error="provider unavailable")
    monitor = JobMonitor(tmp_path)

    job = monitor.get_job("job_001")

    assert job["stage"] == "audio"
    assert monitor.get_job("missing") is None
    assert monitor.get_job("../job_001") is None


def test_cli_parser_accepts_status_commands():
    assert build_parser().parse_args(["--status"]).status == ""
    assert build_parser().parse_args(["--status", "job_001"]).status == "job_001"