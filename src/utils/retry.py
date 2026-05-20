"""
Retry and error handling utilities.

Provides retry logic with exponential backoff for API calls,
graceful degradation strategies, and error classification.
"""

from __future__ import annotations
import time
import functools
import logging
from typing import Callable, Any

logger = logging.getLogger("shopease.retry")


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""
    pass


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
):
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Multiplier for exponential backoff
        retryable_exceptions: Tuple of exception types to retry on

    Usage:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def call_openai(prompt):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        break

                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {func.__name__}: "
                        f"{type(e).__name__}: {e}. Waiting {delay:.1f}s"
                    )
                    time.sleep(delay)

            raise RetryExhaustedError(
                f"{func.__name__} failed after {max_retries} retries. "
                f"Last error: {last_exception}"
            )
        return wrapper
    return decorator


def graceful_fallback(fallback_value: Any = None, log_error: bool = True):
    """
    Decorator that catches exceptions and returns a fallback value.

    Use for non-critical operations where a failure shouldn't crash the pipeline.

    Args:
        fallback_value: Value to return on failure
        log_error: Whether to log the error

    Usage:
        @graceful_fallback(fallback_value={})
        def fetch_optional_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(f"{func.__name__} failed gracefully: {e}")
                return fallback_value
        return wrapper
    return decorator


def classify_error(exception: Exception) -> str:
    """
    Classify an exception into a category for metrics and routing.

    Returns one of: "api_error", "validation_error", "timeout_error",
    "auth_error", "data_error", "unknown_error"
    """
    error_type = type(exception).__name__.lower()

    if "timeout" in error_type or "timeout" in str(exception).lower():
        return "timeout_error"
    if "auth" in error_type or "401" in str(exception) or "403" in str(exception):
        return "auth_error"
    if "validation" in error_type or "value" in error_type:
        return "validation_error"
    if "api" in error_type or "request" in error_type or "http" in error_type:
        return "api_error"
    if "key" in error_type or "index" in error_type or "type" in error_type:
        return "data_error"
    return "unknown_error"
