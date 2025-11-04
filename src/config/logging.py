"""
Logging configuration with dual UTC/IR timestamps and ANSI colors

Format: [UTC][IR][level] message [logger] key=value...
- UTC: YYYY-MM-DD HH:MM:SS.μs UTC (cyan in TTY)
- IR: JYYYY-JMM-JDD HH:MM:SS.μs IR (blue in TTY)
- Levels: debug (gray), info (green), warn (yellow), error (red)
"""
import logging
import sys
import structlog
from datetime import datetime, timezone, timedelta
from typing import Any, Dict
from persiantools.jdatetime import JalaliDateTime


# ANSI 16-color codes (max compatibility)
class Colors:
    """ANSI 16-color codes for terminal output"""
    RESET = "\033[0m"
    GRAY = "\033[90m"      # debug
    GREEN = "\033[92m"     # info
    YELLOW = "\033[93m"    # warn
    RED = "\033[91m"       # error
    CYAN = "\033[96m"      # UTC timestamp
    BLUE = "\033[94m"      # IR timestamp


def is_tty() -> bool:
    """Check if stdout is a TTY (terminal)"""
    return sys.stdout.isatty()


class DualTimestampRenderer:
    """Custom renderer with UTC and Jalali (IR) timestamps"""

    def __init__(self, use_colors: bool = None):
        """
        Initialize renderer

        Args:
            use_colors: Enable colors. If None, auto-detect TTY
        """
        self.use_colors = use_colors if use_colors is not None else is_tty()

    def __call__(self, logger: Any, name: str, event_dict: Dict) -> str:
        """
        Render log entry with dual timestamps

        Args:
            logger: Logger instance
            name: Log method name
            event_dict: Event dictionary

        Returns:
            Formatted log string
        """
        # Get timestamp
        timestamp = event_dict.pop("timestamp", None)
        if isinstance(timestamp, str):
            # Parse ISO timestamp
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = datetime.now(timezone.utc)

        # Format UTC timestamp
        utc_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        utc_micros = dt.microsecond
        utc_timestamp = f"{utc_str}.{utc_micros:06d} UTC"

        # Format IR (Jalali) timestamp with IRST (UTC+3:30)
        ir_dt = dt + timedelta(hours=3, minutes=30)
        jalali_dt = JalaliDateTime.to_jalali(ir_dt)
        ir_str = f"{jalali_dt.year:04d}-{jalali_dt.month:02d}-{jalali_dt.day:02d} {jalali_dt.hour:02d}:{jalali_dt.minute:02d}:{jalali_dt.second:02d}"
        ir_micros = ir_dt.microsecond
        ir_timestamp = f"J{ir_str}.{ir_micros:06d} IR"

        # Get level
        level = event_dict.pop("level", "info")

        # Get logger name
        logger_name = event_dict.pop("logger", None)

        # Get message
        event = event_dict.pop("event", "")

        # Build log line
        if self.use_colors:
            # Colored output
            utc_colored = f"{Colors.CYAN}[{utc_timestamp}]{Colors.RESET}"
            ir_colored = f"{Colors.BLUE}[{ir_timestamp}]{Colors.RESET}"

            # Level colors
            level_colors = {
                "debug": Colors.GRAY,
                "info": Colors.GREEN,
                "warning": Colors.YELLOW,
                "error": Colors.RED,
            }
            level_color = level_colors.get(level, Colors.RESET)
            level_colored = f"{level_color}[{level}]{Colors.RESET}"

            parts = [utc_colored, ir_colored, level_colored, event]

            if logger_name:
                parts.append(f"[{logger_name}]")

        else:
            # Plain output (for logs/containers)
            parts = [
                f"[{utc_timestamp}]",
                f"[{ir_timestamp}]",
                f"[{level}]",
                event
            ]

            if logger_name:
                parts.append(f"[{logger_name}]")

        # Add key-value pairs
        if event_dict:
            kv_pairs = " ".join(f"{k}={v}" for k, v in sorted(event_dict.items()))
            parts.append(kv_pairs)

        return " ".join(parts)


def configure_logging(environment: str, log_level: str) -> None:
    """
    Configure structlog with dual UTC/IR timestamps

    Args:
        environment: Environment name (dev, stage, prod)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Determine if we should use colors (TTY detection)
    use_colors = is_tty() and environment == "dev"

    # Common processors
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        DualTimestampRenderer(use_colors=use_colors),
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
