"""
Validation utilities
"""
import re
from typing import Optional
from monitoring_system.core.exceptions import ValidationException


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format (E.164)

    Args:
        phone: Phone number string

    Returns:
        True if valid, False otherwise

    Example:
        +989123456789 (valid)
        +12025551234 (valid)
        9123456789 (invalid - missing +)
    """
    # E.164 format: +[country code][number]
    # Length: 8-15 digits (excluding +)
    pattern = r'^\+[1-9]\d{7,14}$'
    return bool(re.match(pattern, phone))


def validate_url(url: str) -> bool:
    """
    Validate URL format

    Args:
        url: URL string

    Returns:
        True if valid, False otherwise
    """
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def validate_api_key(api_key: str) -> bool:
    """
    Validate API key format (basic check)

    Args:
        api_key: API key string

    Returns:
        True if valid, False otherwise
    """
    if not api_key or len(api_key) < 10:
        return False

    # Check for obvious test/placeholder keys
    invalid_patterns = [
        'test',
        'example',
        'placeholder',
        'your-api-key',
        'xxx',
    ]

    api_key_lower = api_key.lower()
    for pattern in invalid_patterns:
        if pattern in api_key_lower:
            return False

    return True


def validate_service_name(name: str) -> None:
    """
    Validate service name

    Args:
        name: Service name

    Raises:
        ValidationException: If name is invalid
    """
    if not name or not name.strip():
        raise ValidationException("Service name cannot be empty")

    if len(name) > 255:
        raise ValidationException("Service name cannot exceed 255 characters")

    # Allow alphanumeric, hyphens, underscores, spaces
    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
        raise ValidationException(
            "Service name can only contain letters, numbers, spaces, hyphens, and underscores"
        )


def validate_interval(seconds: int, min_value: int = 30, max_value: int = 86400) -> None:
    """
    Validate check interval

    Args:
        seconds: Interval in seconds
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Raises:
        ValidationException: If interval is invalid
    """
    if seconds < min_value:
        raise ValidationException(f"Interval must be at least {min_value} seconds")

    if seconds > max_value:
        raise ValidationException(f"Interval cannot exceed {max_value} seconds (24 hours)")


def validate_timeout(seconds: int, min_value: int = 1, max_value: int = 300) -> None:
    """
    Validate timeout value

    Args:
        seconds: Timeout in seconds
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Raises:
        ValidationException: If timeout is invalid
    """
    if seconds < min_value:
        raise ValidationException(f"Timeout must be at least {min_value} second")

    if seconds > max_value:
        raise ValidationException(f"Timeout cannot exceed {max_value} seconds")


def sanitize_message(message: str, max_length: int = 4000) -> str:
    """
    Sanitize message for Telegram (remove control characters, limit length)

    Args:
        message: Message string
        max_length: Maximum message length

    Returns:
        Sanitized message
    """
    if not message:
        return ""

    # Remove control characters except newlines and tabs
    sanitized = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', message)

    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[: max_length - 3] + "..."

    return sanitized
