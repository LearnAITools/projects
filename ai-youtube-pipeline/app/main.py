"""Command-line entry point for the AI YouTube Pipeline."""

from __future__ import annotations

import argparse
import sys

from app.automation.automation_manager import AutomationManager
from app.automation.job_monitor import JobMonitor
from app.automation.automation_runner import AutomationRunner
from app.automation.scheduler import AutomationScheduler
from app.automation.topic_queue import TopicQueue

from app.config.settings import get_settings
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for operational pipeline commands."""
    parser = argparse.ArgumentParser(description="Run the AI YouTube automation pipeline")
    command_group = parser.add_mutually_exclusive_group()
    command_group.add_argument(
        "--run-once",
        action="store_true",
        help="Execute all currently due scheduled jobs and exit",
    )
    command_group.add_argument(
        "--status",
        nargs="?",
        const="",
        help="Show aggregate job status, or details for JOB_ID",
    )
    parser.add_argument(
        "--topic",
        help="Add a topic as an immediate job before running once",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    Main application entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        args = build_parser().parse_args(argv)

        if args.topic and not args.run_once:
            logger.error("--topic requires --run-once")
            return 2

        logger.info("=" * 60)
        logger.info("AI YouTube Pipeline - Production Automation")
        logger.info("=" * 60)

        # Load settings
        settings = get_settings()
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Log Level: {settings.log_level}")
        logger.info(f"Dry Run: {settings.dry_run}")
        logger.info(f"Data Directory: {settings.data_dir}")

        # Verify data directory
        data_dir = settings.get_data_dir()
        logger.info(f"Data directory ready: {data_dir}")

        if args.status is not None:
            monitor = JobMonitor(data_dir)
            if args.status:
                job = monitor.get_job(args.status)
                if job is None:
                    logger.error("Job not found: %s", args.status)
                    return 1
                logger.info("Job status: %s", job)
            else:
                logger.info("Job summary: %s", monitor.summary())
            return 0

        if args.run_once:
            history_manager = AutomationManager()
            scheduler = AutomationScheduler()
            queue = TopicQueue(history_manager=history_manager)

            if args.topic:
                scheduler.schedule(
                    topic=args.topic,
                    interval_seconds=86400,
                    run_immediately=True,
                )
                queue.add_topics([args.topic])

            runner = AutomationRunner(
                job_runner=None,
                automation=None,
            )
            runner.job_runner.history_manager = history_manager
            runner.job_runner.scheduler = scheduler
            runner.job_runner.queue = queue
            results = runner.run_once()
            logger.info("Automation run completed: %s", results)
            return 0 if all(item.get("status") == "COMPLETED" for item in results) else 1

        logger.info("=" * 60)
        logger.info("Production automation foundation initialized successfully!")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"Application failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
