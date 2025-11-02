"""
Logging configuration with structlog (ASCII-only for Docker/Ubuntu compatibility)
"""
import logging
import sys
import structlog
from typing import Any


def configure_logging(environment: str, log_level: str) -> None:
    """
    Configure structlog with ASCII-only output for Docker/Ubuntu compatibility

    Args:
        environment: Environment name (dev, stage, prod)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Determine processors based on environment
    if environment == "dev":
        # Development: Colored console output
        processors = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Production/Stage: JSON output
        processors = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Silence noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


def get_logger(name: str = None) -> Any:
    """
    Get a structlog logger instance

    Args:
        name: Logger name (optional)

    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)
