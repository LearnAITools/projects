"""Full automation pipeline integrating executor and content generation."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.automation.automation_executor import AutomationExecutor
from app.automation.automation_manager import AutomationManager
from app.content.content_generator import ContentGenerator, ContentValidationError
from app.pipeline.orchestrator import PipelineOrchestrator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AutomationPipeline:
    """Execute a full automation workflow: scheduled job → pipeline creation → content generation."""

    def __init__(
        self,
        orchestrator: Optional[PipelineOrchestrator] = None,
        generator: Optional[ContentGenerator] = None,
        history_manager: Optional[AutomationManager] = None,
    ) -> None:
        self.orchestrator = orchestrator or PipelineOrchestrator()
        self.generator = generator or ContentGenerator()
        self.history_manager = history_manager or AutomationManager()
        self.executor = AutomationExecutor(
            orchestrator=self.orchestrator,
            history_manager=self.history_manager,
        )

    def run(self, scheduled_job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute a scheduled job through content generation.
        
        Args:
            scheduled_job: Dict with job_id, topic, status, timestamp from JobRunner
            
        Returns:
            Dict with execution results including content_generated flag
        """
        if not scheduled_job:
            logger.error("Cannot run automation pipeline with None job")
            return None

        job_id = scheduled_job.get("job_id")
        topic = scheduled_job.get("topic")

        logger.info(f"Automation pipeline starting for job {job_id}: {topic}")

        try:
            pipeline_job = self.executor.execute(scheduled_job)
            if not pipeline_job:
                logger.error(f"Executor failed to create job for {job_id}")
                return None

            content = self.generator.generate(topic)
            self.orchestrator.save_content(job_id, content)
            self.orchestrator.update_job_status(
                job_id, self.orchestrator.load_job(job_id).status.__class__.CONTENT_GENERATED
            )

            logger.info(f"Automation pipeline completed content for job {job_id}")

            return {
                "job_id": job_id,
                "topic": topic,
                "content_generated": True,
                "status": "CONTENT_GENERATED",
            }

        except ContentValidationError as exc:
            logger.error(f"Content generation failed for job {job_id}: {exc}")
            self.orchestrator.update_job_status(
                job_id, self.orchestrator.load_job(job_id).status.__class__.FAILED
            )
            return {
                "job_id": job_id,
                "topic": topic,
                "content_generated": False,
                "status": "FAILED",
            }
        except Exception as exc:
            logger.error(f"Unexpected error in automation pipeline for {job_id}: {exc}")
            return {
                "job_id": job_id,
                "topic": topic,
                "content_generated": False,
                "status": "FAILED",
            }
