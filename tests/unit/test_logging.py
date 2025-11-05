"""
Tests for dual timestamp logging system
"""
import pytest
from datetime import datetime, timezone
from config.logging import DualTimestampRenderer, Colors, is_tty
import structlog


class TestDualTimestampRenderer:
    """Test dual timestamp logging renderer"""

    def test_renderer_without_colors(self):
        """Test log rendering without colors"""
        renderer = DualTimestampRenderer(use_colors=False)

        event_dict = {
            "timestamp": "2025-11-04T15:50:43.576659Z",
            "level": "info",
            "logger": "test_logger",
            "event": "test_message",
            "key1": "value1",
            "key2": "value2",
        }

        result = renderer(None, "info", event_dict.copy())

        # Verify format components
        assert "[2025-11-04" in result  # UTC timestamp
        assert "UTC]" in result
        assert "[J" in result  # Jalali timestamp
        assert "IR]" in result
        assert "[info]" in result
        assert "test_message" in result
        assert "[test_logger]" in result
        assert "key1=value1" in result
        assert "key2=value2" in result

    def test_renderer_with_colors(self):
        """Test log rendering with colors"""
        renderer = DualTimestampRenderer(use_colors=True)

        event_dict = {
            "timestamp": "2025-11-04T15:50:43.576659Z",
            "level": "info",
            "logger": "test_logger",
            "event": "test_message",
        }

        result = renderer(None, "info", event_dict.copy())

        # Verify ANSI color codes are present
        assert Colors.CYAN in result  # UTC color
        assert Colors.BLUE in result  # IR color
        assert Colors.GREEN in result  # info level color
        assert Colors.RESET in result

    def test_level_colors(self):
        """Test different log level colors"""
        renderer = DualTimestampRenderer(use_colors=True)

        levels_colors = {
            "debug": Colors.GRAY,
            "info": Colors.GREEN,
            "warning": Colors.YELLOW,
            "error": Colors.RED,
        }

        for level, color in levels_colors.items():
            event_dict = {
                "timestamp": "2025-11-04T15:50:43.576659Z",
                "level": level,
                "event": "test",
            }
            result = renderer(None, level, event_dict.copy())
            assert color in result

    def test_jalali_timestamp_format(self):
        """Test Jalali timestamp format"""
        renderer = DualTimestampRenderer(use_colors=False)

        event_dict = {
            "timestamp": "2025-11-04T15:50:43.576659Z",
            "level": "info",
            "event": "test",
        }

        result = renderer(None, "info", event_dict.copy())

        # Jalali format should be J1404-08-14 (roughly for Nov 2025)
        assert "J1404" in result or "J1403" in result
        assert ".576659 IR]" in result  # microseconds preserved

    def test_no_logger_name(self):
        """Test log without logger name"""
        renderer = DualTimestampRenderer(use_colors=False)

        event_dict = {
            "timestamp": "2025-11-04T15:50:43.576659Z",
            "level": "info",
            "event": "test_message",
        }

        result = renderer(None, "info", event_dict.copy())

        assert "test_message" in result
        # Should not have empty logger brackets
        assert result.count("[") == 3  # [UTC], [IR], [level]

    def test_microsecond_precision(self):
        """Test microsecond precision in timestamps"""
        renderer = DualTimestampRenderer(use_colors=False)

        event_dict = {
            "timestamp": "2025-11-04T15:50:43.123456Z",
            "level": "info",
            "event": "test",
        }

        result = renderer(None, "info", event_dict.copy())

        assert ".123456 UTC]" in result

    def test_key_value_sorting(self):
        """Test key-value pairs are sorted alphabetically"""
        renderer = DualTimestampRenderer(use_colors=False)

        event_dict = {
            "timestamp": "2025-11-04T15:50:43.576659Z",
            "level": "info",
            "event": "test",
            "zebra": "last",
            "alpha": "first",
            "middle": "second",
        }

        result = renderer(None, "info", event_dict.copy())

        # Find position of each key
        alpha_pos = result.find("alpha=first")
        middle_pos = result.find("middle=second")
        zebra_pos = result.find("zebra=last")

        assert alpha_pos < middle_pos < zebra_pos


class TestColorCodes:
    """Test ANSI color code definitions"""

    def test_color_codes_are_valid(self):
        """Ensure all color codes are valid ANSI sequences"""
        assert Colors.RESET.startswith("\033[")
        assert Colors.GRAY.startswith("\033[")
        assert Colors.GREEN.startswith("\033[")
        assert Colors.YELLOW.startswith("\033[")
        assert Colors.RED.startswith("\033[")
        assert Colors.CYAN.startswith("\033[")
        assert Colors.BLUE.startswith("\033[")
