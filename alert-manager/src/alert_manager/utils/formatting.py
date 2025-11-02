"""
Formatting utilities for messages and display
"""
from typing import List, Dict, Any


def format_bytes(bytes_count: int) -> str:
    """
    Format bytes into human-readable format

    Args:
        bytes_count: Number of bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format percentage with specified decimal places

    Args:
        value: Percentage value (0-100)
        decimals: Number of decimal places

    Returns:
        Formatted string (e.g., "95.5%")
    """
    return f"{value:.{decimals}f}%"


def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format currency amount

    Args:
        amount: Amount
        currency: Currency code

    Returns:
        Formatted string (e.g., "$10.50")
    """
    symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "IRR": "﷼",
    }

    symbol = symbols.get(currency, currency)
    return f"{symbol}{amount:.2f}"


def format_list_items(items: List[str], max_items: int = 10) -> str:
    """
    Format list of items with bullet points

    Args:
        items: List of item strings
        max_items: Maximum items to show

    Returns:
        Formatted string with bullet points
    """
    if not items:
        return "None"

    display_items = items[:max_items]
    lines = [f"• {item}" for item in display_items]

    if len(items) > max_items:
        lines.append(f"... and {len(items) - max_items} more")

    return "\n".join(lines)


def format_key_value(data: Dict[str, Any], indent: int = 2) -> str:
    """
    Format dictionary as key-value pairs

    Args:
        data: Dictionary of data
        indent: Indentation spaces

    Returns:
        Formatted string
    """
    if not data:
        return "No data"

    lines = []
    indent_str = " " * indent

    for key, value in data.items():
        # Format key: replace underscores with spaces, capitalize
        formatted_key = key.replace("_", " ").title()
        lines.append(f"{indent_str}{formatted_key}: {value}")

    return "\n".join(lines)


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to maximum length

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def format_response_time(ms: int) -> str:
    """
    Format response time in human-readable format

    Args:
        ms: Response time in milliseconds

    Returns:
        Formatted string
    """
    if ms < 1000:
        return f"{ms}ms"
    else:
        seconds = ms / 1000
        return f"{seconds:.2f}s"


def format_alert_severity(severity: str) -> str:
    """
    Format alert severity with appropriate symbol

    Args:
        severity: Severity level (info, warning, critical)

    Returns:
        Formatted string with symbol
    """
    symbols = {
        "info": "[INFO]",
        "warning": "[WARNING]",
        "critical": "[CRITICAL]",
    }

    return symbols.get(severity.lower(), f"[{severity.upper()}]")
