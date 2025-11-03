"""
Jalali (Persian) calendar utilities
"""
from datetime import datetime, timedelta
from typing import Optional

from persiantools.jdatetime import JalaliDate, JalaliDateTime

from monitoring_system.config.logging import get_logger

log = get_logger(__name__)


def gregorian_to_jalali(dt: datetime) -> JalaliDateTime:
    """
    Convert Gregorian datetime to Jalali datetime

    Args:
        dt: Gregorian datetime

    Returns:
        Jalali datetime
    """
    return JalaliDateTime.to_jalali(dt)


def jalali_to_gregorian(jdt: JalaliDate, hour: int = 0, minute: int = 0, second: int = 0) -> datetime:
    """
    Convert Jalali date to Gregorian datetime

    Args:
        jdt: Jalali date
        hour: Hour (0-23)
        minute: Minute (0-59)
        second: Second (0-59)

    Returns:
        Gregorian datetime
    """
    return datetime(jdt.year, jdt.month, jdt.day, hour, minute, second)


def format_jalali_datetime(dt: datetime, include_time: bool = True) -> str:
    """
    Format datetime as Jalali string

    Args:
        dt: Gregorian datetime
        include_time: Whether to include time

    Returns:
        Formatted string (e.g., "1403/08/11 14:23:45" or "1403/08/11")
    """
    jdt = gregorian_to_jalali(dt)

    if include_time:
        return f"{jdt.year}/{jdt.month:02d}/{jdt.day:02d} {jdt.hour:02d}:{jdt.minute:02d}:{jdt.second:02d}"
    else:
        return f"{jdt.year}/{jdt.month:02d}/{jdt.day:02d}"


def format_jalali_date(dt: datetime) -> str:
    """
    Format date as Jalali string (date only)

    Args:
        dt: Gregorian datetime

    Returns:
        Formatted string (e.g., "1403/08/11")
    """
    return format_jalali_datetime(dt, include_time=False)


def get_jalali_today() -> JalaliDate:
    """
    Get today's Jalali date

    Returns:
        Jalali date
    """
    return JalaliDate.today()


def get_jalali_now() -> JalaliDateTime:
    """
    Get current Jalali datetime

    Returns:
        Jalali datetime
    """
    return JalaliDateTime.now()


def calculate_next_jalali_date(
    frequency: str,
    day_of_week: Optional[int] = None,
    day_of_month: Optional[int] = None,
    month: Optional[int] = None,
) -> datetime:
    """
    Calculate next occurrence based on Jalali calendar

    Args:
        frequency: Report frequency (daily, weekly, monthly, quarterly, yearly)
        day_of_week: Day of week (0=Shanbeh/Saturday, 6=Jomeh/Friday)
        day_of_month: Day of month (1-31)
        month: Month (1-12)

    Returns:
        Gregorian datetime of next occurrence
    """
    now_jalali = get_jalali_today()

    if frequency == "daily":
        # Next day at specified hour
        next_jalali = now_jalali + timedelta(days=1)
        return jalali_to_gregorian(next_jalali, hour=9, minute=0)

    elif frequency == "weekly":
        # Next Shanbeh (Saturday - first day of Persian week)
        days_until_shanbeh = (7 - now_jalali.weekday()) % 7 or 7
        next_jalali = now_jalali + timedelta(days=days_until_shanbeh)
        return jalali_to_gregorian(next_jalali, hour=9, minute=0)

    elif frequency == "monthly":
        # First day of next month
        if now_jalali.day == 1:
            # Already day 1, go to next month
            next_month = now_jalali.month + 1 if now_jalali.month < 12 else 1
            next_year = now_jalali.year if now_jalali.month < 12 else now_jalali.year + 1
            next_jalali = JalaliDate(next_year, next_month, 1)
        else:
            # Go to day 1 of next month
            next_month = now_jalali.month + 1 if now_jalali.month < 12 else 1
            next_year = now_jalali.year if now_jalali.month < 12 else now_jalali.year + 1
            next_jalali = JalaliDate(next_year, next_month, 1)
        return jalali_to_gregorian(next_jalali, hour=9, minute=0)

    elif frequency == "quarterly":
        # First day of next quarter (months 1, 4, 7, 10)
        quarter_months = [1, 4, 7, 10]
        current_month = now_jalali.month

        next_quarter_month = next((m for m in quarter_months if m > current_month), None)
        if next_quarter_month:
            next_jalali = JalaliDate(now_jalali.year, next_quarter_month, 1)
        else:
            # Next quarter is next year's Farvardin
            next_jalali = JalaliDate(now_jalali.year + 1, 1, 1)

        return jalali_to_gregorian(next_jalali, hour=9, minute=0)

    elif frequency == "yearly":
        # First day of next year (1 Farvardin - Persian New Year)
        next_year = now_jalali.year + 1 if now_jalali.month > 1 or now_jalali.day > 1 else now_jalali.year
        next_jalali = JalaliDate(next_year, 1, 1)
        return jalali_to_gregorian(next_jalali, hour=9, minute=0)

    else:
        raise ValueError(f"Invalid frequency: {frequency}")


def is_jalali_schedule_due(
    frequency: str,
    last_run: Optional[datetime] = None,
    day_of_week: Optional[int] = None,
    day_of_month: Optional[int] = None,
    month: Optional[int] = None,
) -> bool:
    """
    Check if a Jalali schedule is due to run

    Args:
        frequency: Report frequency
        last_run: Last run datetime
        day_of_week: Target day of week
        day_of_month: Target day of month
        month: Target month

    Returns:
        True if schedule is due
    """
    now_jalali = get_jalali_today()

    # Check if already ran today
    if last_run:
        last_run_jalali = gregorian_to_jalali(last_run)
        if last_run_jalali.date() == now_jalali:
            return False

    if frequency == "daily":
        return True

    elif frequency == "weekly":
        # Check if today is Shanbeh (day 0)
        return now_jalali.weekday() == 0

    elif frequency == "monthly":
        # Check if today is day 1
        return now_jalali.day == 1

    elif frequency == "quarterly":
        # Check if today is first day of quarter
        return now_jalali.day == 1 and now_jalali.month in [1, 4, 7, 10]

    elif frequency == "yearly":
        # Check if today is 1 Farvardin
        return now_jalali.month == 1 and now_jalali.day == 1

    return False


def format_duration_persian(minutes: int) -> str:
    """
    Format duration in Persian-friendly format

    Args:
        minutes: Duration in minutes

    Returns:
        Formatted string (e.g., "2 hours 15 minutes")
    """
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if remaining_minutes == 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"

    return f"{hours} hour{'s' if hours != 1 else ''} {remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}"
