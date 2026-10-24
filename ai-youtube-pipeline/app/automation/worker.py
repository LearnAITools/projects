"""Worker process controls for running due automation jobs safely."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.automation.automation_runner import AutomationRunner
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AutomationWorker:
    """Run automation polling cycles with bounded concurrency and clean shutdown."""

    def __init__(
        self,
        runner: Optional[AutomationRunner] = None,
        poll_interval_seconds: float = 5,
        max_workers: int = 1,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be greater than zero")
        if max_workers <= 0:
            raise ValueError("max_workers must be greater than zero")
        self.runner = runner or AutomationRunner()
        self.poll_interval_seconds = poll_interval_seconds
        self.max_workers = max_workers
        self._stop_event = threading.Event()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._results: List[Dict[str, Any]] = []

    def stop(self) -> None:
        """Request a graceful shutdown after active jobs finish."""
        self._stop_event.set()

    @property
    def stopped(self) -> bool:
        """Return whether shutdown has been requested."""
        return self._stop_event.is_set()

    def run_once(self) -> List[Dict[str, Any]]:
        """Run one polling cycle and return completed job results."""
        scheduler = self.runner.job_runner.scheduler
        results: List[Dict[str, Any]] = []
        futures = []
        for _ in range(self.max_workers):
            scheduled_job = self.runner.job_runner.run_next_job(
                now=datetime.now(timezone.utc)
            )
            if not scheduled_job:
                break
            futures.append(self._executor.submit(self.runner.automation.run_job, scheduled_job))
        for future in futures:
            result = future.result()
            if result:
                results.append(result)
                retry_at = result.get("next_retry_at")
                if result.get("status") == "FAILED" and retry_at:
                    scheduler.reschedule_retry(result["job_id"], datetime.fromisoformat(retry_at))
                elif result.get("status") == "FAILED":
                    scheduler.cancel(result["job_id"])
        self._results.extend(results)
        return results

    def run_forever(self, max_cycles: Optional[int] = None) -> List[Dict[str, Any]]:
        """Poll until stopped, optionally limiting the number of cycles for tests."""
        cycles = 0
        try:
            while not self.stopped and (max_cycles is None or cycles < max_cycles):
                self.run_once()
                cycles += 1
                if not self.stopped and (max_cycles is None or cycles < max_cycles):
                    self._stop_event.wait(self.poll_interval_seconds)
        finally:
            self._executor.shutdown(wait=True)
        return list(self._results)

    def queue_status(self) -> Dict[str, Any]:
        """Return queue visibility and worker lifecycle information."""
        scheduler = self.runner.job_runner.scheduler
        due = scheduler.get_due_jobs()
        return {
            "due_jobs": len(due),
            "due_job_ids": [job.job_id for job in due],
            "stopped": self.stopped,
            "max_workers": self.max_workers,
            "completed_results": len(self._results),
        }