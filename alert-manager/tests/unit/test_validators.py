"""
Unit tests for validation utilities
"""
import pytest

from monitoring_system.utils.validators import (
    validate_phone_number,
    validate_url,
    validate_api_key,
    validate_service_name,
    validate_interval,
    sanitize_message,
)
from monitoring_system.core.exceptions import ValidationException


class TestPhoneValidation:
    """Test phone number validation"""

    def test_valid_phone_numbers(self):
        """Test valid phone numbers in E.164 format"""
        assert validate_phone_number("+989123456789") is True
        assert validate_phone_number("+12025551234") is True
        assert validate_phone_number("+442071234567") is True

    def test_invalid_phone_numbers(self):
        """Test invalid phone numbers"""
        assert validate_phone_number("9123456789") is False  # Missing +
        assert validate_phone_number("+98912") is False  # Too short
        assert validate_phone_number("+0123456789") is False  # Invalid country code
        assert validate_phone_number("invalid") is False


class TestURLValidation:
    """Test URL validation"""

    def test_valid_urls(self):
        """Test valid URLs"""
        assert validate_url("https://example.com") is True
        assert validate_url("http://api.example.com/health") is True
        assert validate_url("https://example.com:8080/path") is True

    def test_invalid_urls(self):
        """Test invalid URLs"""
        assert validate_url("not-a-url") is False
        assert validate_url("ftp://example.com") is False
        assert validate_url("") is False


class TestAPIKeyValidation:
    """Test API key validation"""

    def test_valid_api_keys(self):
        """Test valid API keys"""
        assert validate_api_key("sk-1234567890abcdef") is True
        assert validate_api_key("valid_api_key_12345") is True

    def test_invalid_api_keys(self):
        """Test invalid API keys"""
        assert validate_api_key("short") is False
        assert validate_api_key("test-key") is False
        assert validate_api_key("example-key") is False
        assert validate_api_key("") is False


class TestServiceNameValidation:
    """Test service name validation"""

    def test_valid_service_names(self):
        """Test valid service names"""
        validate_service_name("payment-api")  # Should not raise
        validate_service_name("user_service")
        validate_service_name("Service 123")

    def test_invalid_service_names(self):
        """Test invalid service names"""
        with pytest.raises(ValidationException):
            validate_service_name("")

        with pytest.raises(ValidationException):
            validate_service_name("a" * 256)  # Too long

        with pytest.raises(ValidationException):
            validate_service_name("service@name")  # Invalid character


class TestIntervalValidation:
    """Test interval validation"""

    def test_valid_intervals(self):
        """Test valid intervals"""
        validate_interval(30)  # Should not raise
        validate_interval(300)
        validate_interval(3600)

    def test_invalid_intervals(self):
        """Test invalid intervals"""
        with pytest.raises(ValidationException):
            validate_interval(10)  # Too short

        with pytest.raises(ValidationException):
            validate_interval(100000)  # Too long


class TestMessageSanitization:
    """Test message sanitization"""

    def test_sanitize_normal_message(self):
        """Test sanitizing normal message"""
        message = "Service is down"
        result = sanitize_message(message)
        assert result == "Service is down"

    def test_sanitize_long_message(self):
        """Test sanitizing long message"""
        message = "A" * 5000
        result = sanitize_message(message, max_length=100)
        assert len(result) == 100
        assert result.endswith("...")

    def test_sanitize_control_characters(self):
        """Test removing control characters"""
        message = "Service\x00is\x01down"
        result = sanitize_message(message)
        assert "\x00" not in result
        assert "\x01" not in result
