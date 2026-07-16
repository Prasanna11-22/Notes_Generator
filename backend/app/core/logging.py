"""
Loguru logging configuration.

Sets up:
- Console handler (colourised, human-readable)
- Rotating file handler for general logs
- Rotating file handler for error-only logs

Call ``setup_logging()`` once at application startup.
"""

import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure Loguru with console and file sinks.

    Should be called once before any other application code runs.
    """
    # Remove the default Loguru handler
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "{message}"
    )

    # ── Console sink ────────────────────────────────────────────────────────
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.log_level,
        colorize=True,
        backtrace=settings.debug,
        diagnose=settings.debug,
    )

    # ── File sinks ──────────────────────────────────────────────────────────
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # General application log (rotated daily, kept 14 days)
    logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        format=log_format,
        level=settings.log_level,
        rotation="00:00",  # rotate at midnight
        retention="14 days",
        compression="zip",
        backtrace=settings.debug,
        diagnose=settings.debug,
        enqueue=True,  # thread-safe async writes
    )

    # Error-only log (rotated at 10 MB, kept 30 days)
    logger.add(
        log_dir / "error.log",
        format=log_format,
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )

    logger.info(
        "Logging initialised | level={} | env={}",
        settings.log_level,
        settings.environment,
    )
