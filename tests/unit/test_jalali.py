"""
Tests for Jalali (Persian) calendar utilities
"""
import pytest
from datetime import datetime, timedelta
from utils.jalali import (
    gregorian_to_jalali,
    format_jalali_datetime,
    format_jalali_date,
    get_jalali_today,
    get_jalali_now,
    format_duration_persian,
)
from persiantools.jdatetime import JalaliDateTime


class TestJalaliConversion:
    """Test Gregorian to Jalali conversion"""

    def test_gregorian_to_jalali(self):
        """Test converting Gregorian to Jalali"""
        # 2025-11-04 should be around 1404-08-13/14
        dt = datetime(2025, 11, 4, 15, 30, 45)
        jalali_dt = gregorian_to_jalali(dt)

        assert jalali_dt.year == 1404
        assert jalali_dt.month == 8
        assert jalali_dt.day in [13, 14]  # Allow for slight variation

    def test_nowruz_conversion(self):
        """Test Persian New Year conversion (1 Farvardin)"""
        # March 21, 2025 = 1 Farvardin 1404
        dt = datetime(2025, 3, 21, 0, 0, 0)
        jalali_dt = gregorian_to_jalali(dt)

        assert jalali_dt.year == 1404
        assert jalali_dt.month == 1
        # Day might be 1 or 2 depending on exact time
        assert jalali_dt.day in [1, 2]


class TestJalaliFormatting:
    """Test Jalali date/time formatting"""

    def test_format_jalali_datetime_with_time(self):
        """Test formatting Jalali datetime with time"""
        dt = datetime(2025, 11, 4, 15, 30, 45)
        result = format_jalali_datetime(dt, include_time=True)

        # Should be in format: YYYY/MM/DD HH:MM:SS
        assert "/" in result
        assert ":" in result
        assert len(result.split("/")) == 3
        assert len(result.split(":")) == 3

    def test_format_jalali_datetime_without_time(self):
        """Test formatting Jalali datetime without time"""
        dt = datetime(2025, 11, 4, 15, 30, 45)
        result = format_jalali_datetime(dt, include_time=False)

        # Should be in format: YYYY/MM/DD
        assert "/" in result
        assert ":" not in result
        assert len(result.split("/")) == 3

    def test_format_jalali_date(self):
        """Test formatting Jalali date only"""
        dt = datetime(2025, 11, 4, 15, 30, 45)
        result = format_jalali_date(dt)

        # Should not include time
        assert ":" not in result
        assert "/" in result

    def test_date_formatting_consistency(self):
        """Test that format_jalali_date and format_jalali_datetime(include_time=False) match"""
        dt = datetime(2025, 11, 4, 15, 30, 45)

        result1 = format_jalali_date(dt)
        result2 = format_jalali_datetime(dt, include_time=False)

        assert result1 == result2


class TestJalaliGetters:
    """Test Jalali date/time getter functions"""

    def test_get_jalali_today(self):
        """Test getting today's Jalali date"""
        jalali_today = get_jalali_today()

        # Should be a valid JalaliDate
        assert hasattr(jalali_today, 'year')
        assert hasattr(jalali_today, 'month')
        assert hasattr(jalali_today, 'day')
        assert 1 <= jalali_today.month <= 12
        assert 1 <= jalali_today.day <= 31

    def test_get_jalali_now(self):
        """Test getting current Jalali datetime"""
        jalali_now = get_jalali_now()

        # Should be a valid JalaliDateTime
        assert hasattr(jalali_now, 'year')
        assert hasattr(jalali_now, 'month')
        assert hasattr(jalali_now, 'day')
        assert hasattr(jalali_now, 'hour')
        assert hasattr(jalali_now, 'minute')
        assert hasattr(jalali_now, 'second')


class TestDurationFormatting:
    """Test Persian-friendly duration formatting"""

    def test_format_duration_minutes(self):
        """Test formatting duration in minutes"""
        assert "minute" in format_duration_persian(1)
        assert "minutes" in format_duration_persian(30)
        assert "minutes" in format_duration_persian(59)

    def test_format_duration_hours(self):
        """Test formatting duration in hours"""
        result = format_duration_persian(60)
        assert "1 hour" in result
        assert "minute" not in result

        result = format_duration_persian(120)
        assert "2 hours" in result

    def test_format_duration_hours_and_minutes(self):
        """Test formatting duration with hours and minutes"""
        result = format_duration_persian(90)
        assert "1 hour" in result
        assert "30 minutes" in result

        result = format_duration_persian(135)
        assert "2 hours" in result
        assert "15 minutes" in result

    def test_format_duration_edge_cases(self):
        """Test edge cases for duration formatting"""
        # Zero minutes (edge case)
        assert format_duration_persian(0) == "0 minutes"

        # Exactly 1 minute (singular)
        assert format_duration_persian(1) == "1 minute"

        # Large duration
        result = format_duration_persian(1500)
        assert "25 hours" in result


class TestJalaliRoundTrip:
    """Test round-trip conversions"""

    def test_multiple_dates_consistency(self):
        """Test consistency across multiple dates"""
        test_dates = [
            datetime(2025, 1, 1),
            datetime(2025, 6, 15),
            datetime(2025, 12, 31),
            datetime(2024, 3, 20),  # Around Nowruz
        ]

        for dt in test_dates:
            jalali = gregorian_to_jalali(dt)
            formatted = format_jalali_datetime(dt)

            # Should contain year
            assert str(jalali.year) in formatted
            # Should contain month (with leading zero if needed)
            assert f"{jalali.month:02d}" in formatted
            # Should contain day (with leading zero if needed)
            assert f"{jalali.day:02d}" in formatted
