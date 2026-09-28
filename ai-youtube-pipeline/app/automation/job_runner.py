"""Job execution layer coordinating scheduler, topic queue, and history."""

from __future__ import annotations

from datetime import datetime, timezone
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
        reference = now or datetime.now(timezone.utc)
        claimed = self.scheduler.claim_due_job(now=reference)
        if claimed is None:
            return None

        job, claim_token = claimed

        try:
            topic = self.queue.next_topic()
        except ValueError:
            self.scheduler.release_claim(job.job_id, claim_token)
            return None

        self.scheduler.mark_run(job.job_id, claim_token=claim_token)

        return {
            "job_id": job.job_id,
            "topic": topic,
            "format": job.format.value,
            "publish_at": job.publish_at.isoformat() if job.publish_at else None,
            "status": "SCHEDULED",
            "timestamp": reference.isoformat(),
        }
