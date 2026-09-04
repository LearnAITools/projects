"""Automation helper for duplicate-topic detection and retry decisions."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.automation.job_history import JobHistory


class AutomationManager:
    """Small automation layer for future scheduling, deduplication, and retries."""

    def __init__(self, history_path: Optional[Path | str] = None) -> None:
        self.history = JobHistory(history_path=history_path)

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
