"""Main entry point for AI YouTube Pipeline."""

import sys
from pathlib import Path

from app.config.settings import get_settings
from app.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


def main() -> int:
    """
    Main application entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        logger.info("=" * 60)
        logger.info("AI YouTube Pipeline - Foundation Phase")
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

        logger.info("=" * 60)
        logger.info("Foundation phase initialized successfully!")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"Application failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
