"""
@AiCapability Decorator.

Marks an endpoint or service method as requiring AI capabilities from
Hermes Agent. Can be used for capability discovery, rate limiting,
and fallback handling.
"""

import functools
import logging
from typing import Any, Callable

logger = logging.getLogger("hiremind.ai")


def AiCapability(
    capability: str,
    *,
    fallback: Callable | None = None,
    timeout: float = 30.0,
    cache_ttl: int | None = None,
):
    """
    Decorator that marks a function as requiring an AI capability.

    Args:
        capability: Name of the AI capability (e.g. "resume_parse", "candidate_match").
        fallback: Optional fallback function if AI is unavailable.
        timeout: Maximum seconds to wait for AI response.
        cache_ttl: Cache result for this many seconds (None = no cache).

    Usage::

        @AiCapability("resume_parse", fallback=rule_based_parse, timeout=15)
        async def parse_resume(text: str) -> dict:
            # Call Hermes Agent
            ...

    The decorator currently only logs capability usage. In production it should:
    1. Check if the Hermes Agent is available.
    2. Enforce rate limits per capability / tenant.
    3. Apply caching if ``cache_ttl`` is set.
    4. Fall back to ``fallback`` if the agent is down.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.info(
                "AiCapability invoked: capability=%s, func=%s, timeout=%.1fs",
                capability,
                func.__qualname__,
                timeout,
            )

            try:
                # TODO: check capability availability, rate limits, caching
                result = await func(*args, **kwargs)
                return result
            except Exception as exc:
                logger.warning(
                    "AiCapability failed: capability=%s, error=%s",
                    capability,
                    exc,
                )
                if fallback is not None:
                    logger.info("Using fallback for capability=%s", capability)
                    return await fallback(*args, **kwargs)
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.info(
                "AiCapability invoked (sync): capability=%s, func=%s",
                capability,
                func.__qualname__,
            )
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                if fallback is not None:
                    return fallback(*args, **kwargs)
                raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
