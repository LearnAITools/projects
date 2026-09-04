"""Background automation runner for continuous job execution."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.automation.full_automation import FullAutomation
from app.automation.job_runner import JobRunner
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AutomationRunner:
    """
    Continuously check for due scheduled jobs and execute them.
    Tracks execution statistics and handles errors gracefully.
    """

    def __init__(
        self,
        job_runner: Optional[JobRunner] = None,
        automation: Optional[FullAutomation] = None,
    ) -> None:
        self.job_runner = job_runner or JobRunner()
        self.automation = automation or FullAutomation()
        self._stats = {
            "total_runs": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
        }

    def run_once(self) -> List[Dict[str, Any]]:
        """
        Execute all currently due scheduled jobs.
        
        Returns:
            List of execution results (empty if no jobs are due)
        """
        self._stats["total_runs"] += 1
        results: List[Dict[str, Any]] = []

        while True:
            scheduled_job = self.job_runner.run_next_job()
            if not scheduled_job:
                break

            logger.info(
                f"Automation runner executing job {scheduled_job['job_id']}: "
                f"{scheduled_job['topic']}"
            )

            try:
                result = self.automation.run_job(scheduled_job)
                if result:
                    results.append(result)
                    if result.get("status") == "COMPLETED":
                        self._stats["successful_jobs"] += 1
                    else:
                        self._stats["failed_jobs"] += 1
            except Exception as exc:
                logger.error(
                    f"Unexpected error executing job {scheduled_job['job_id']}: {exc}"
                )
                self._stats["failed_jobs"] += 1
                results.append({
                    "job_id": scheduled_job["job_id"],
                    "topic": scheduled_job["topic"],
                    "status": "FAILED",
                    "error": str(exc),
                })

        return results

    def get_stats(self) -> Dict[str, int]:
        """Return execution statistics."""
        return dict(self._stats)

    def reset_stats(self) -> None:
        """Reset execution statistics."""
        self._stats = {
            "total_runs": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
        }
