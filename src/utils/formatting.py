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
    lines = [f"💳 {service_name} ({service_env})"]
    lines.append("")  # Empty line for spacing

    # ===== SUMMARY SECTION =====
    # Show quick overview (from /api/v1/credits endpoint style)
    total = credit_data.get("total_credit")
    usage = credit_data.get("total_usage")

    if total is not None and usage is not None:
        lines.append("   📊 Summary:")
        lines.append(f"      Total Credits: {format_currency(total)}")
        lines.append(f"      Total Usage: {format_currency(usage)}")
        if total > 0:
            used_percentage = (usage / total * 100) if usage else 0
            lines.append(f"      Used: {used_percentage:.1f}%")
        lines.append("")  # Empty line for spacing

    # ===== DETAILED SECTION =====
    # Show detailed breakdown (from /api/v1/key endpoint)
    lines.append("   📝 Detailed Breakdown:")

    # Key label
    key_label = credit_data.get("key_label")
    if key_label:
        lines.append(f"      Label: {key_label}")

    # Limit information
    limit = credit_data.get("total_credit")
    if limit is not None:
        if limit == 0:
            lines.append("      Limit: Unlimited")
        else:
            lines.append(f"      Limit: {format_currency(limit)}")

    # Remaining balance
    remaining = credit_data.get("remaining_credit")
    if remaining is not None:
        if limit is not None and limit > 0:
            percentage = (remaining / limit * 100) if limit > 0 else 0
            lines.append(f"      Remaining: {format_currency(remaining)} ({percentage:.1f}%)")

            # Check threshold warning
            if threshold and remaining < threshold:
                lines.append(f"      Status: ⚠️ Below threshold ({format_currency(threshold)})")
            else:
                lines.append("      Status: ✅ Healthy")
        else:
            lines.append(f"      Remaining: {format_currency(remaining)}")

    # Limit reset
    limit_reset = credit_data.get("limit_reset")
    if limit_reset:
        lines.append(f"      Limit Reset: {limit_reset}")

    # Usage breakdown by period
    daily_usage = credit_data.get("usage_daily")
    weekly_usage = credit_data.get("usage_weekly")
    monthly_usage = credit_data.get("usage_monthly")

    if daily_usage is not None or weekly_usage is not None or monthly_usage is not None:
        lines.append("")
        lines.append("      Usage Breakdown:")
        if daily_usage is not None:
            lines.append(f"         Daily: {format_currency(daily_usage)}")
        if weekly_usage is not None:
            lines.append(f"         Weekly: {format_currency(weekly_usage)}")
        if monthly_usage is not None:
            lines.append(f"         Monthly: {format_currency(monthly_usage)}")

    # BYOK usage if available
    byok_usage = credit_data.get("byok_usage")
    byok_daily = credit_data.get("byok_usage_daily")
    byok_weekly = credit_data.get("byok_usage_weekly")
    byok_monthly = credit_data.get("byok_usage_monthly")

    if any(x is not None for x in [byok_usage, byok_daily, byok_weekly, byok_monthly]):
        lines.append("")
        lines.append("      BYOK Usage:")
        if byok_usage is not None:
            lines.append(f"         Total: {format_currency(byok_usage)}")
        if byok_daily is not None:
            lines.append(f"         Daily: {format_currency(byok_daily)}")
        if byok_weekly is not None:
            lines.append(f"         Weekly: {format_currency(byok_weekly)}")
        if byok_monthly is not None:
            lines.append(f"         Monthly: {format_currency(byok_monthly)}")

    # Additional metadata
    is_free_tier = credit_data.get("is_free_tier")
    include_byok = credit_data.get("include_byok_in_limit")

    if is_free_tier is not None or include_byok is not None:
        lines.append("")
        lines.append("      Metadata:")
        if is_free_tier is not None:
            tier = "Free Tier" if is_free_tier else "Paid Tier"
            lines.append(f"         Account Type: {tier}")
        if include_byok is not None:
            byok_text = "Yes" if include_byok else "No"
            lines.append(f"         BYOK in Limit: {byok_text}")

    return "\n".join(lines)
