"""Command-line entry point for the AI YouTube Pipeline."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from app.automation.automation_manager import AutomationManager
from app.automation.job_monitor import JobMonitor
from app.automation.automation_runner import AutomationRunner
from app.automation.scheduler import AutomationScheduler
from app.automation.topic_queue import TopicQueue
from app.automation.job_runner import JobRunner
from app.automation.full_automation import FullAutomation
from app.content.models import VideoFormat

from app.config.settings import get_settings
from app.utils.logger import get_logger
from app.utils.health import startup_checks
from app.utils.database import SQLiteStore
from app.utils.costs import CostController
from app.automation.worker import AutomationWorker

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
    command_group.add_argument(
        "--schedule-topic",
        help="Create a persisted recurring schedule for TOPIC",
    )
    command_group.add_argument(
        "--list-schedules",
        action="store_true",
        help="List persisted schedules",
    )
    command_group.add_argument(
        "--cancel-schedule",
        metavar="JOB_ID",
        help="Cancel a persisted schedule by job ID",
    )
    command_group.add_argument(
        "--health",
        action="store_true",
        help="Run startup readiness checks and exit",
    )
    command_group.add_argument(
        "--alerts",
        action="store_true",
        help="Show operational alerts for persisted jobs",
    )
    command_group.add_argument(
        "--usage",
        action="store_true",
        help="Show provider usage, estimated cost, budget, and quota status",
    )
    command_group.add_argument("--queue", action="store_true", help="Show queued and paused schedules")
    command_group.add_argument("--pause", metavar="JOB_ID", help="Pause a scheduled job")
    command_group.add_argument("--resume", metavar="JOB_ID", help="Resume a paused scheduled job")
    command_group.add_argument("--retry", metavar="JOB_ID", help="Retry a scheduled job immediately")
    command_group.add_argument("--worker", action="store_true", help="Run the worker until interrupted")
    parser.add_argument(
        "--topic",
        help="Add a topic as an immediate job before running once",
    )
    parser.add_argument(
        "--format",
        choices=("long-form", "short"),
        default="long-form",
        help="Video format for an immediate topic job",
    )
    parser.add_argument(
        "--publish-at",
        help="UTC or timezone-aware ISO-8601 publish time for a scheduled topic",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=86400,
        help="Interval for a persisted schedule (default: 86400)",
    )
    parser.add_argument("--poll-interval", type=float, default=5, help="Worker polling interval in seconds")
    parser.add_argument("--max-workers", type=int, default=1, help="Maximum concurrent worker jobs")
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
        if args.publish_at and not args.schedule_topic:
            logger.error("--publish-at requires --schedule-topic")
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
        schedule_file = data_dir / "schedules.json"
        database_path = data_dir / "pipeline.sqlite3"
        use_sqlite = getattr(settings, "storage_backend", None) == "sqlite"
        if use_sqlite:
            SQLiteStore(database_path).migrate_json(
                history_path=data_dir / "job_history.json",
                schedule_path=schedule_file,
            )
        health_failures = startup_checks(settings, data_dir)
        if args.health:
            if health_failures:
                for failure in health_failures:
                    logger.error("Health check failed: %s", failure)
                return 1
            logger.info("Health checks passed")
            return 0
        for failure in health_failures:
            logger.warning("Startup check: %s", failure)

        cost_controller = CostController(
            data_dir,
            monthly_budget_usd=getattr(settings, "monthly_budget_usd", 0),
            image_cost_per_unit_usd=getattr(settings, "image_cost_per_unit_usd", 0),
            voice_cost_per_unit_usd=getattr(settings, "voice_cost_per_unit_usd", 0),
            image_quota_units=getattr(settings, "image_quota_units", 0),
            voice_quota_units=getattr(settings, "voice_quota_units", 0),
        )
        if args.usage:
            usage_report = cost_controller.report()
            logger.info("Provider usage: %s", usage_report)
            return 1 if usage_report["budget_exceeded"] or usage_report["quota_exceeded"] else 0
        if args.run_once or args.worker:
            cost_controller.assert_within_limits()

        if args.schedule_topic:
            publish_at = None
            if args.publish_at:
                publish_at = datetime.fromisoformat(args.publish_at.replace("Z", "+00:00"))
            scheduler = AutomationScheduler(
                schedule_file=None if use_sqlite else schedule_file,
                database_path=database_path if use_sqlite else None,
            )
            job = scheduler.schedule(
                topic=args.schedule_topic,
                interval_seconds=args.interval_seconds,
                run_immediately=publish_at is not None,
                format=VideoFormat.SHORT if args.format == "short" else VideoFormat.LONG_FORM,
                publish_at=publish_at,
            )
            logger.info("Schedule created: %s", job.to_dict())
            return 0

        if args.list_schedules:
            scheduler = AutomationScheduler(
                schedule_file=None if use_sqlite else schedule_file,
                database_path=database_path if use_sqlite else None,
            )
            logger.info("Schedules: %s", [job.to_dict() for job in scheduler.list_jobs()])
            return 0

        if args.cancel_schedule:
            scheduler = AutomationScheduler(
                schedule_file=None if use_sqlite else schedule_file,
                database_path=database_path if use_sqlite else None,
            )
            if not scheduler.cancel(args.cancel_schedule):
                logger.error("Schedule not found: %s", args.cancel_schedule)
                return 1
            logger.info("Schedule canceled: %s", args.cancel_schedule)
            return 0

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

        if args.alerts:
            monitor = JobMonitor(data_dir)
            logger.info("Alerts: %s", monitor.alerts())
            return 0

        if args.queue or args.pause or args.resume or args.retry or args.worker:
            scheduler = AutomationScheduler(
                schedule_file=None if use_sqlite else schedule_file,
                database_path=database_path if use_sqlite else None,
            )
            if args.pause:
                if not scheduler.pause(args.pause):
                    logger.error("Schedule not found: %s", args.pause)
                    return 1
                logger.info("Schedule paused: %s", args.pause)
                return 0
            if args.resume:
                if not scheduler.resume(args.resume):
                    logger.error("Schedule not found: %s", args.resume)
                    return 1
                logger.info("Schedule resumed: %s", args.resume)
                return 0
            if args.retry:
                if not scheduler.retry(args.retry):
                    logger.error("Schedule not found: %s", args.retry)
                    return 1
                logger.info("Schedule queued for retry: %s", args.retry)
                return 0
            if args.queue:
                jobs = scheduler.list_jobs()
                logger.info("Queue: %s", {
                    "queued": [job.job_id for job in jobs if not job.paused],
                    "paused": [job.job_id for job in jobs if job.paused],
                })
                return 0
            history_manager = AutomationManager(
                history_path=None if use_sqlite else data_dir / "job_history.json",
                database_path=database_path if use_sqlite else None,
            )
            queue = TopicQueue(history_manager=history_manager)
            worker = AutomationWorker(
                runner=AutomationRunner(
                    job_runner=JobRunner(
                        history_manager=history_manager,
                        scheduler=scheduler,
                        queue=queue,
                    ),
                    automation=FullAutomation(history_manager=history_manager),
                ),
                poll_interval_seconds=args.poll_interval,
                max_workers=args.max_workers,
            )
            try:
                worker.run_forever()
            except KeyboardInterrupt:
                worker.stop()
            return 0

        if args.run_once:
            history_manager = AutomationManager(
                history_path=None if use_sqlite else data_dir / "job_history.json",
                database_path=database_path if use_sqlite else None,
            )
            scheduler = AutomationScheduler(
                schedule_file=None if use_sqlite else schedule_file,
                database_path=database_path if use_sqlite else None,
            )
            queue = TopicQueue(history_manager=history_manager)
            if args.topic:
                scheduler.schedule(
                    topic=args.topic,
                    interval_seconds=86400,
                    run_immediately=True,
                    format=VideoFormat.SHORT if args.format == "short" else VideoFormat.LONG_FORM,
                )
                queue.add_topics([args.topic])

            runner = AutomationRunner(
                job_runner=JobRunner(
                    history_manager=history_manager,
                    scheduler=scheduler,
                    queue=queue,
                ),
                automation=FullAutomation(history_manager=history_manager),
            )
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
