"""Automation helper for duplicate-topic detection and retry decisions."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.automation.job_history import JobHistory
from app.content.content_generator import ContentValidationError


class AutomationManager:
    """Small automation layer for future scheduling, deduplication, and retries."""

    def __init__(self, history_path: Optional[Path | str] = None, database_path: Optional[Path | str] = None) -> None:
        self.history = JobHistory(history_path=history_path, database_path=database_path)

    def is_duplicate_topic(self, topic: str) -> bool:
        """Return True if the exact topic has previously been recorded."""
        normalized = topic.strip().lower()
        for record in self.history.list_jobs():
            if str(record.get("topic", "")).strip().lower() == normalized:
                return True
        return False

    def should_retry(self, job_id: str, max_retries: int = 3) -> bool:
        """Return True when a failed job can be retried within the configured limit."""
        for record in self.history.list_jobs():
            if record.get("job_id") == job_id:
                attempts = int(record.get("attempts", 0))
                return attempts < max_retries
        return False

    def get_attempts(self, job_id: str) -> int:
        """Return the highest persisted attempt count for a job."""
        return max(
            (
                int(record.get("attempts", 0))
                for record in self.history.list_jobs()
                if record.get("job_id") == job_id
            ),
            default=0,
        )

    def record_attempt(self, job_id: str, attempts: int, status: str = "FAILED") -> None:
        """Update the persisted history record with the latest attempt count."""
        records = self.history.list_jobs()
        for record in reversed(records):
            if record.get("job_id") == job_id:
                record["attempts"] = attempts
                record["status"] = status
                self.history.replace(records)
                return

    @staticmethod
    def is_transient_error(error: BaseException) -> bool:
        """Classify errors that are generally safe to retry."""
        if isinstance(error, (ValueError, FileNotFoundError, ContentValidationError)):
            return False
        return isinstance(error, (TimeoutError, ConnectionError, RuntimeError))

    @staticmethod
    def retry_delay_seconds(attempts: int, base_delay_seconds: int = 2) -> int:
        """Return exponential backoff for a 1-based attempt number."""
        return base_delay_seconds * (2 ** max(attempts - 1, 0))
