"""Job execution layer coordinating scheduler, topic queue, and history."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.automation.automation_manager import AutomationManager
from app.automation.scheduler import AutomationScheduler
from app.automation.topic_queue import TopicQueue


class JobRunner:
    """Execute scheduled jobs by coordinating scheduler, queue, and automation state."""

    def __init__(
        self,
        history_manager: Optional[AutomationManager] = None,
        scheduler: Optional[AutomationScheduler] = None,
        queue: Optional[TopicQueue] = None,
    ) -> None:
        self.history_manager = history_manager or AutomationManager()
        self.scheduler = scheduler or AutomationScheduler()
        self.queue = queue or TopicQueue(history_manager=self.history_manager)

    def run_next_job(
        self, now: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute the next due scheduled job if one exists, otherwise return None."""
        reference = now or datetime.utcnow()
        due_jobs = self.scheduler.get_due_jobs(now=reference)

        if not due_jobs:
            return None

        job = due_jobs[0]

        try:
            topic = self.queue.next_topic()
        except ValueError:
            return None

        self.scheduler.mark_run(job.job_id)

        return {
            "job_id": job.job_id,
            "topic": topic,
            "status": "SCHEDULED",
            "timestamp": reference.isoformat(),
        }
