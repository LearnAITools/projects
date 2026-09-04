"""Automation executor that bridges scheduled jobs to full pipeline execution."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.automation.automation_manager import AutomationManager
from app.pipeline.orchestrator import PipelineOrchestrator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AutomationExecutor:
    """Execute a scheduled job by creating a pipeline entry and recording in history."""

    def __init__(
        self,
        orchestrator: Optional[PipelineOrchestrator] = None,
        history_manager: Optional[AutomationManager] = None,
    ) -> None:
        self.orchestrator = orchestrator or PipelineOrchestrator()
        self.history_manager = history_manager or AutomationManager()

    def execute(self, scheduled_job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a pipeline job from a scheduled job and record it in history.
        
        Args:
            scheduled_job: Dict with job_id, topic, status, timestamp from JobRunner
            
        Returns:
            Dict with created job details or None if job is invalid
        """
        if not scheduled_job:
            raise ValueError("scheduled_job cannot be None or empty")
        if not scheduled_job.get("job_id"):
            raise ValueError("scheduled_job must have a job_id")
        if not scheduled_job.get("topic"):
            raise ValueError("scheduled_job must have a topic")

        job_id = scheduled_job["job_id"]
        topic = scheduled_job["topic"]

        pipeline_job = self.orchestrator.create_job(topic=topic, job_id=job_id)
        self.history_manager.history.record(
            job_id=job_id,
            topic=topic,
            status="CREATED",
            attempts=0,
        )

        logger.info(f"Executor created job {job_id} for topic: {topic}")

        return {
            "job_id": pipeline_job.job_id,
            "topic": pipeline_job.topic,
            "status": pipeline_job.status.value,
            "created_at": pipeline_job.created_at,
        }
