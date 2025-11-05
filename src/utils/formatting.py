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

    Supports OpenRouter dual-endpoint structure:
    - Wallet-level data from /api/v1/credits (entire account)
    - API Key-level data from /api/v1/key (specific key only)

    Args:
        service_name: Service name
        service_env: Service environment
        credit_data: Dictionary containing credit information
        threshold: Credit threshold for warnings (applies to key remaining)

    Returns:
        Formatted credit check result
    """
    lines = [f"💳 {service_name} ({service_env})"]
    lines.append("")

    # ===== WALLET OVERVIEW SECTION =====
    # From /api/v1/credits endpoint - shows entire account balance
    wallet_total = credit_data.get("wallet_total_credits")
    wallet_usage = credit_data.get("wallet_total_usage")

    if wallet_total is not None and wallet_usage is not None:
        wallet_remaining = wallet_total - wallet_usage
        wallet_used_pct = (wallet_usage / wallet_total * 100) if wallet_total > 0 else 0

        # Determine wallet status
        wallet_status = "✅ Healthy"
        if threshold and wallet_remaining < threshold:
            wallet_status = f"⚠️ Below threshold ({format_currency(threshold)})"

        lines.append("   🏦 Wallet Overview:")
        lines.append(f"      Total Credits: {format_currency(wallet_total)}")
        lines.append(f"      Total Usage: {format_currency(wallet_usage)}")
        lines.append(f"      Remaining: {format_currency(wallet_remaining)}")
        lines.append(f"      Used: {wallet_used_pct:.1f}%")
        lines.append(f"      Status: {wallet_status}")
        lines.append("")

    # ===== API KEY DETAILS SECTION =====
    # From /api/v1/key endpoint - shows this specific key's allocation
    key_label = credit_data.get("key_label")
    key_limit = credit_data.get("key_limit")
    key_remaining = credit_data.get("key_remaining")
    key_usage = credit_data.get("key_usage")

    if key_label is not None or key_limit is not None:
        lines.append(f"   🔑 API Key: {key_label or 'Unknown'}")
        lines.append("")

        # Key allocation and usage
        if key_limit is not None and key_limit > 0:
            key_used = key_usage if key_usage is not None else (key_limit - key_remaining if key_remaining is not None else 0)
            key_used_pct = (key_used / key_limit * 100) if key_limit > 0 else 0

            lines.append(f"      Allocated Limit: {format_currency(key_limit)}")
            lines.append(f"      Key Usage: {format_currency(key_used)}")

            if key_remaining is not None:
                lines.append(f"      Key Remaining: {format_currency(key_remaining)}")

            lines.append(f"      Used: {key_used_pct:.1f}%")

            # Show allocation percentage relative to wallet
            if wallet_total and wallet_total > 0:
                allocation_pct = (key_limit / wallet_total * 100)
                lines.append(f"      Allocation: {allocation_pct:.1f}% of wallet")

            # Check threshold warning for key
            if threshold and key_remaining is not None:
                if key_remaining < threshold:
                    lines.append(f"      Status: ⚠️ Below threshold ({format_currency(threshold)})")
                else:
                    lines.append("      Status: ✅ Healthy")
            else:
                lines.append("      Status: ✅ Healthy")

        elif key_limit is None or key_limit == 0:
            lines.append("      Allocated Limit: Unlimited")
            if key_usage is not None:
                lines.append(f"      Key Usage: {format_currency(key_usage)}")
            lines.append("      Status: ✅ Healthy")

        # Limit reset
        key_limit_reset = credit_data.get("key_limit_reset")
        if key_limit_reset:
            lines.append("")
            lines.append(f"      Limit Reset: {key_limit_reset}")

        # Usage breakdown by period (for this key only)
        key_daily = credit_data.get("key_usage_daily")
        key_weekly = credit_data.get("key_usage_weekly")
        key_monthly = credit_data.get("key_usage_monthly")

        if any(x is not None for x in [key_daily, key_weekly, key_monthly]):
            lines.append("")
            lines.append("      Usage Breakdown (This Key):")
            if key_daily is not None:
                lines.append(f"         Daily: {format_currency(key_daily)}")
            if key_weekly is not None:
                lines.append(f"         Weekly: {format_currency(key_weekly)}")
            if key_monthly is not None:
                lines.append(f"         Monthly: {format_currency(key_monthly)}")
            lines.append("         ⚠️ Note: Periods calculated in UTC timezone")

        # BYOK usage (for this key only)
        byok_total = credit_data.get("key_byok_usage")
        byok_daily = credit_data.get("key_byok_usage_daily")
        byok_weekly = credit_data.get("key_byok_usage_weekly")
        byok_monthly = credit_data.get("key_byok_usage_monthly")

        if any(x is not None for x in [byok_total, byok_daily, byok_weekly, byok_monthly]):
            lines.append("")
            lines.append("      BYOK Usage (This Key):")
            if byok_total is not None:
                lines.append(f"         Total: {format_currency(byok_total)}")
            if byok_daily is not None:
                lines.append(f"         Daily: {format_currency(byok_daily)}")
            if byok_weekly is not None:
                lines.append(f"         Weekly: {format_currency(byok_weekly)}")
            if byok_monthly is not None:
                lines.append(f"         Monthly: {format_currency(byok_monthly)}")
            if any(x is not None for x in [byok_daily, byok_weekly, byok_monthly]):
                lines.append("         ⚠️ Note: Periods calculated in UTC timezone")

        # Metadata
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
