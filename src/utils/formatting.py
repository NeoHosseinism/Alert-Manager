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


def format_health_check_result(service_name: str, service_env: str, is_healthy: bool,
                               response_time_ms: int = None, status_code: int = None,
                               error_message: str = None) -> str:
    """
    Format health check result for manual check report

    Args:
        service_name: Service name
        service_env: Service environment
        is_healthy: Health status
        response_time_ms: Response time in milliseconds
        status_code: HTTP status code
        error_message: Error message if unhealthy

    Returns:
        Formatted health check result
    """
    status_icon = "✅" if is_healthy else "❌"
    status_text = "UP" if is_healthy else "DOWN"

    lines = [
        f"{status_icon} {service_name} ({service_env})",
        f"   Status: {status_text}"
    ]

    if response_time_ms is not None:
        if response_time_ms < 0:
            lines.append("   Response Time: Timeout")
        else:
            lines.append(f"   Response Time: {format_response_time(response_time_ms)}")

    if status_code:
        lines.append(f"   HTTP Status: {status_code}")

    if not is_healthy and error_message:
        error_preview = truncate_string(error_message, 100)
        lines.append(f"   Error: {error_preview}")

    return "\n".join(lines)


def format_credit_check_result(service_name: str, service_env: str, credit_data: Dict[str, Any],
                               threshold: float = None) -> str:
    """
    Format API credit check result for manual check report

    Args:
        service_name: Service name
        service_env: Service environment
        credit_data: Dictionary containing credit information
        threshold: Credit threshold for warnings

    Returns:
        Formatted credit check result
    """
    remaining = credit_data.get("remaining_credit")
    total = credit_data.get("total_credit")
    usage = credit_data.get("total_usage")

    lines = [f"💳 {service_name} ({service_env})"]

    # Show credit balance
    if remaining is not None and total is not None:
        percentage = (remaining / total * 100) if total > 0 else 0
        lines.append(f"   Balance: {format_currency(remaining)} / {format_currency(total)} ({percentage:.1f}%)")

        # Check threshold warning
        if threshold and remaining < threshold:
            lines.append(f"   Status: ⚠️ Below threshold ({format_currency(threshold)})")
        else:
            lines.append("   Status: ✅ Healthy")
    elif remaining is not None:
        lines.append(f"   Remaining: {format_currency(remaining)}")

    # Show usage information
    if usage is not None:
        lines.append(f"   Total Usage: {format_currency(usage)}")

    # Show usage periods if available
    daily_usage = credit_data.get("usage_daily")
    if daily_usage is not None:
        lines.append(f"   Daily Usage: {format_currency(daily_usage)}")

    weekly_usage = credit_data.get("usage_weekly")
    if weekly_usage is not None:
        lines.append(f"   Weekly Usage: {format_currency(weekly_usage)}")

    monthly_usage = credit_data.get("usage_monthly")
    if monthly_usage is not None:
        lines.append(f"   Monthly Usage: {format_currency(monthly_usage)}")

    # Show additional info
    key_label = credit_data.get("key_label")
    if key_label:
        lines.append(f"   Key: {key_label}")

    is_free_tier = credit_data.get("is_free_tier")
    if is_free_tier is not None:
        tier = "Free" if is_free_tier else "Paid"
        lines.append(f"   Tier: {tier}")

    limit_reset = credit_data.get("limit_reset")
    if limit_reset:
        lines.append(f"   Reset: {limit_reset}")

    return "\n".join(lines)
