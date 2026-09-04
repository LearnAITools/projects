"""Automation package for future pipeline features."""

from app.automation.automation_executor import AutomationExecutor
from app.automation.automation_manager import AutomationManager
from app.automation.automation_pipeline import AutomationPipeline
from app.automation.automation_runner import AutomationRunner
from app.automation.full_automation import FullAutomation
from app.automation.job_history import JobHistory
from app.automation.job_runner import JobRunner
from app.automation.scheduler import AutomationScheduler, ScheduledJob
from app.automation.topic_queue import TopicQueue
from app.automation.topic_selector import TopicSelector

__all__ = [
    "AutomationManager",
    "JobHistory",
    "AutomationScheduler",
    "ScheduledJob",
    "TopicSelector",
    "TopicQueue",
    "JobRunner",
    "AutomationExecutor",
    "AutomationPipeline",
    "FullAutomation",
    "AutomationRunner",
]
