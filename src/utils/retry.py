"""
Retry decorator with exponential backoff
"""
import asyncio
from functools import wraps
from typing import Callable, Tuple, Type, TypeVar

from config.logging import get_logger

log = get_logger(__name__)

T = TypeVar("T")


def async_retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int], None] = None,
):
    """
    Decorator for retrying async functions with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry

    Example:
        @async_retry(max_attempts=3, backoff_factor=2, exceptions=(httpx.TimeoutException,))
        async def fetch_data():
            # This will retry up to 3 times with delays of 2^0, 2^1, 2^2 seconds
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        delay = backoff_factor**attempt
                        log.warning(
                            "retry_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            delay_seconds=delay,
                            error=str(e),
                        )

                        # Call retry callback if provided
                        if on_retry:
                            on_retry(e, attempt + 1)

                        await asyncio.sleep(delay)
                    else:
                        log.error(
                            "retry_exhausted",
                            function=func.__name__,
                            max_attempts=max_attempts,
                            error=str(e),
                        )

            # All retries failed
            raise last_exception

        return wrapper

    return decorator
