"""Retry utilities with exponential backoff for AWS Bedrock throttling"""

import asyncio
import logging
from typing import TypeVar, Callable, Any, Optional
from functools import wraps
import time

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def exponential_backoff_retry(
    func: Callable[..., T],
    max_retries: int = 6,  # Increased from 5 for low quotas
    initial_delay: float = 3.0,  # Increased from 1.0 - start with 3s
    max_delay: float = 120.0,  # Increased from 60.0 - max 2 minutes
    exponential_base: float = 2.5,  # Increased from 2.0 - grow faster
    jitter: bool = True,
    retry_exceptions: tuple = (Exception,),
) -> T:
    """
    Retry a function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delay
        retry_exceptions: Tuple of exceptions to retry on

    Returns:
        Result of the function call

    Raises:
        Last exception if all retries failed
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except retry_exceptions as e:
            last_exception = e

            # Check if it's a throttling error
            error_msg = str(e)
            is_throttling = any(
                keyword in error_msg.lower()
                for keyword in ["throttl", "rate limit", "too many requests", "slowdown"]
            )

            if attempt >= max_retries:
                logger.error(f"Max retries ({max_retries}) exceeded: {e}")
                raise

            # Calculate delay with exponential backoff
            delay = min(initial_delay * (exponential_base**attempt), max_delay)

            # Add jitter to prevent thundering herd
            if jitter:
                import random

                delay = delay * (0.5 + random.random())

            if is_throttling:
                logger.warning(
                    f"⚠️  Rate limited, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})..."
                )
            else:
                logger.warning(f"Retry attempt {attempt + 1}/{max_retries} after {delay:.1f}s: {e}")

            await asyncio.sleep(delay)

    # Should never reach here, but just in case
    raise last_exception


def with_retry(
    max_retries: int = 5,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
):
    """
    Decorator to add exponential backoff retry logic to async functions.

    Usage:
        @with_retry(max_retries=3, initial_delay=2.0)
        async def my_bedrock_call():
            return await llm.ainvoke(...)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            async def _call():
                return await func(*args, **kwargs)

            return await exponential_backoff_retry(
                _call,
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
            )

        return wrapper

    return decorator

