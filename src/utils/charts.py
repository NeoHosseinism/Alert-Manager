"""
ASCII chart utilities for text-based visualizations in Telegram reports
"""
from typing import List, Tuple, Optional


def create_horizontal_bar_chart(
    data: List[Tuple[str, float]],
    max_width: int = 30,
    show_values: bool = True,
    bar_char: str = "█"
) -> str:
    """
    Create a horizontal bar chart using ASCII characters

    Args:
        data: List of (label, value) tuples
        max_width: Maximum width of bars in characters
        show_values: Whether to show numeric values
        bar_char: Character to use for bars

    Returns:
        Formatted ASCII bar chart

    Example:
        >>> data = [("Service A", 95.5), ("Service B", 78.2), ("Service C", 100.0)]
        >>> print(create_horizontal_bar_chart(data))
        Service A  ████████████████████████████▌  95.5%
        Service B  ███████████████████████▌       78.2%
        Service C  ██████████████████████████████ 100.0%
    """
    if not data:
        return "No data available"

    # Find max value for scaling
    max_value = max(val for _, val in data)
    if max_value == 0:
        max_value = 1

    lines = []
    max_label_len = max(len(label) for label, _ in data)

    for label, value in data:
        # Calculate bar length
        bar_length = int((value / max_value) * max_width)

        # Create bar with partial character support
        full_bars = int(bar_length)
        partial = bar_length - full_bars

        bar = bar_char * full_bars
        if partial >= 0.5 and full_bars < max_width:
            bar += "▌"  # Half block

        # Pad label
        padded_label = label.ljust(max_label_len)

        # Format line
        if show_values:
            line = f"{padded_label}  {bar.ljust(max_width + 1)} {value:.1f}%"
        else:
            line = f"{padded_label}  {bar}"

        lines.append(line)

    return "\n".join(lines)


def create_sparkline(values: List[float], width: int = 20) -> str:
    """
    Create a sparkline (mini line chart) using Unicode characters

    Args:
        values: List of numeric values
        width: Width in characters (values will be sampled/interpolated)

    Returns:
        Sparkline string

    Example:
        >>> values = [1, 3, 2, 5, 4, 7, 6, 8]
        >>> print(create_sparkline(values))
        ▁▃▂▅▄▇▆█
    """
    if not values:
        return "─" * width

    # Sparkline characters from low to high
    chars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

    # Sample values to fit width
    if len(values) > width:
        # Sample evenly
        step = len(values) / width
        sampled = [values[int(i * step)] for i in range(width)]
    elif len(values) < width:
        # Repeat values to fill width
        sampled = values * (width // len(values) + 1)
        sampled = sampled[:width]
    else:
        sampled = values

    # Normalize to 0-7 range
    min_val = min(sampled)
    max_val = max(sampled)

    if max_val == min_val:
        return chars[4] * len(sampled)  # Middle character

    normalized = [
        int((val - min_val) / (max_val - min_val) * 7)
        for val in sampled
    ]

    return "".join(chars[n] for n in normalized)


def create_trend_indicator(
    current: float,
    previous: float,
    show_percentage: bool = True
) -> str:
    """
    Create a trend indicator showing increase/decrease

    Args:
        current: Current value
        previous: Previous value
        show_percentage: Whether to show percentage change

    Returns:
        Formatted trend indicator

    Example:
        >>> create_trend_indicator(150, 100)
        '↑ +50.0%'
        >>> create_trend_indicator(80, 100)
        '↓ -20.0%'
    """
    if previous == 0:
        return "─ N/A"

    change = current - previous
    percent_change = (change / previous) * 100

    if change > 0:
        arrow = "↑"
        sign = "+"
    elif change < 0:
        arrow = "↓"
        sign = ""
    else:
        return "─ No change"

    if show_percentage:
        return f"{arrow} {sign}{percent_change:.1f}%"
    else:
        return f"{arrow} {sign}{change:.1f}"


def create_uptime_indicator(uptime_percent: float) -> str:
    """
    Create a visual uptime indicator

    Args:
        uptime_percent: Uptime percentage (0-100)

    Returns:
        Formatted uptime indicator with emoji

    Example:
        >>> create_uptime_indicator(99.9)
        '🟢 99.9% (Excellent)'
        >>> create_uptime_indicator(95.0)
        '🟡 95.0% (Good)'
    """
    if uptime_percent >= 99.9:
        emoji = "🟢"
        status = "Excellent"
    elif uptime_percent >= 99.0:
        emoji = "🟢"
        status = "Very Good"
    elif uptime_percent >= 95.0:
        emoji = "🟡"
        status = "Good"
    elif uptime_percent >= 90.0:
        emoji = "🟠"
        status = "Fair"
    else:
        emoji = "🔴"
        status = "Poor"

    return f"{emoji} {uptime_percent:.2f}% ({status})"


def create_credit_gauge(remaining: float, total: float, width: int = 20) -> str:
    """
    Create a visual gauge showing remaining credits

    Args:
        remaining: Remaining credits
        total: Total credits
        width: Width of gauge in characters

    Returns:
        Formatted gauge

    Example:
        >>> create_credit_gauge(75, 100)
        '[███████████████░░░░░] 75.0%'
    """
    if total == 0:
        return f"[{'─' * width}] N/A"

    percent = (remaining / total) * 100
    filled = int((remaining / total) * width)
    empty = width - filled

    # Choose fill character based on level
    if percent >= 50:
        fill_char = "█"
    elif percent >= 25:
        fill_char = "▓"
    else:
        fill_char = "▒"

    gauge = fill_char * filled + "░" * empty

    return f"[{gauge}] {percent:.1f}%"


def create_timeline(
    events: List[Tuple[str, str]],
    max_items: int = 10
) -> str:
    """
    Create a simple timeline of events

    Args:
        events: List of (timestamp, event_description) tuples
        max_items: Maximum number of events to show

    Returns:
        Formatted timeline

    Example:
        >>> events = [("14:30", "Service UP"), ("14:35", "Alert triggered")]
        >>> print(create_timeline(events))
        ├─ 14:30  Service UP
        └─ 14:35  Alert triggered
    """
    if not events:
        return "No events"

    lines = []
    display_events = events[:max_items]

    for i, (timestamp, description) in enumerate(display_events):
        if i == len(display_events) - 1:
            prefix = "└─"
        else:
            prefix = "├─"

        lines.append(f"{prefix} {timestamp}  {description}")

    if len(events) > max_items:
        lines.append(f"   ... and {len(events) - max_items} more events")

    return "\n".join(lines)


def create_comparison_table(
    headers: List[str],
    rows: List[List[str]],
    max_width: Optional[int] = None
) -> str:
    """
    Create a simple ASCII table

    Args:
        headers: Column headers
        rows: Data rows
        max_width: Maximum width per column

    Returns:
        Formatted table

    Example:
        >>> headers = ["Service", "Status", "Uptime"]
        >>> rows = [["API", "UP", "99.9%"], ["DB", "UP", "100%"]]
        >>> print(create_comparison_table(headers, rows))
        Service  Status  Uptime
        ───────  ──────  ──────
        API      UP      99.9%
        DB       UP      100%
    """
    if not rows:
        return "No data"

    # Calculate column widths
    col_widths = []
    for i, header in enumerate(headers):
        max_len = len(header)
        for row in rows:
            if i < len(row):
                max_len = max(max_len, len(str(row[i])))

        if max_width:
            max_len = min(max_len, max_width)

        col_widths.append(max_len)

    # Format header
    header_line = "  ".join(
        headers[i].ljust(col_widths[i]) for i in range(len(headers))
    )

    separator = "  ".join("─" * col_widths[i] for i in range(len(headers)))

    # Format rows
    row_lines = []
    for row in rows:
        row_line = "  ".join(
            str(row[i] if i < len(row) else "").ljust(col_widths[i])
            for i in range(len(headers))
        )
        row_lines.append(row_line)

    return "\n".join([header_line, separator] + row_lines)
