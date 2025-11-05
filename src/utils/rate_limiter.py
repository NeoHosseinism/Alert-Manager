"""
Rate limiting utility for manual check commands
Prevents users from spamming manual checks
"""
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional


class RateLimiter:
    """
    Simple in-memory rate limiter for manual checks

    Stores last check time per user-service combination
    """

    def __init__(self, cooldown_seconds: int = 60):
        """
        Initialize rate limiter

        Args:
            cooldown_seconds: Minimum seconds between checks (default: 60)
        """
        self.cooldown_seconds = cooldown_seconds
        self._last_checks: Dict[str, datetime] = {}

    def _get_key(self, user_id: int, service_id: Optional[int] = None, check_type: Optional[str] = None) -> str:
        """
        Generate unique key for user-service-type combination

        Args:
            user_id: User ID
            service_id: Service ID (optional, for single service checks)
            check_type: Check type (health/credit, optional for specific checks)

        Returns:
            Unique key string
        """
        parts = [str(user_id)]
        if service_id:
            parts.append(str(service_id))
        if check_type:
            parts.append(check_type)
        return ":".join(parts)

    def check_rate_limit(
        self,
        user_id: int,
        service_id: Optional[int] = None,
        check_type: Optional[str] = None
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if user can perform a manual check

        Args:
            user_id: User ID
            service_id: Service ID (optional)
            check_type: Check type (optional)

        Returns:
            Tuple of (allowed: bool, remaining_seconds: Optional[int])
            - If allowed=True, remaining_seconds=None
            - If allowed=False, remaining_seconds=seconds to wait
        """
        key = self._get_key(user_id, service_id, check_type)

        now = datetime.utcnow()

        if key in self._last_checks:
            last_check = self._last_checks[key]
            time_passed = (now - last_check).total_seconds()

            if time_passed < self.cooldown_seconds:
                remaining = int(self.cooldown_seconds - time_passed)
                return False, remaining

        # Update last check time
        self._last_checks[key] = now

        # Clean up old entries (older than 2x cooldown period)
        self._cleanup_old_entries()

        return True, None

    def _cleanup_old_entries(self):
        """Remove entries older than 2x cooldown period to prevent memory leak"""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.cooldown_seconds * 2)

        keys_to_remove = [
            key for key, timestamp in self._last_checks.items()
            if timestamp < cutoff
        ]

        for key in keys_to_remove:
            del self._last_checks[key]

    def reset(self, user_id: int, service_id: Optional[int] = None, check_type: Optional[str] = None):
        """
        Reset rate limit for a specific user-service-type combination
        Useful for testing or admin overrides

        Args:
            user_id: User ID
            service_id: Service ID (optional)
            check_type: Check type (optional)
        """
        key = self._get_key(user_id, service_id, check_type)
        if key in self._last_checks:
            del self._last_checks[key]


# Global rate limiter instance
_rate_limiter = RateLimiter(cooldown_seconds=60)


def check_rate_limit(
    user_id: int,
    service_id: Optional[int] = None,
    check_type: Optional[str] = None
) -> Tuple[bool, Optional[int]]:
    """
    Convenience function to check rate limit

    Args:
        user_id: User ID
        service_id: Service ID (optional)
        check_type: Check type (optional)

    Returns:
        Tuple of (allowed: bool, remaining_seconds: Optional[int])
    """
    return _rate_limiter.check_rate_limit(user_id, service_id, check_type)
