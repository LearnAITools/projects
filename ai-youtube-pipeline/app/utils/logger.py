"""Logging configuration and utilities."""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from app.config import Settings


def get_logger(
    name: str,
    settings: Optional[Settings] = None,
) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)
        settings: Settings instance (if None, uses default)

    Returns:
        Configured logger instance
    """
    if settings is None:
        from app.config.settings import get_settings

        settings = get_settings()

    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        level = settings.get_log_level_int()
        logger.setLevel(level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (optional, for production)
        if settings.environment == "production":
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                logs_dir / "app.log",
                maxBytes=10485760,  # 10MB
                backupCount=5,
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger
