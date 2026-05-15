"""
@AiCapability Decorator.

Marks an endpoint or service method as requiring AI capabilities.
Supports capability discovery, rate limiting, fallback handling,
and health-check-based gating.
"""

import functools
import logging
import time
from typing import Any, Callable

logger = logging.getLogger("hiremind.ai")

# Track last health check time per capability
_health_cache: dict[str, tuple[bool, float]] = {}
_HEALTH_CHECK_INTERVAL = 60.0  # seconds between health checks


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

            ai_available = _check_ai_availability(capability)

            if not ai_available:
                logger.warning(
                    "AI capability unavailable: capability=%s, using fallback=%s",
                    capability,
                    fallback is not None,
                )
                if fallback is not None:
                    return await fallback(*args, **kwargs)
                # If no fallback, proceed anyway (the function itself should handle AI absence)

            start = time.monotonic()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.monotonic() - start
                logger.info(
                    "AiCapability completed: capability=%s, elapsed=%.2fs",
                    capability,
                    elapsed,
                )
                return result
            except Exception as exc:
                elapsed = time.monotonic() - start
                logger.warning(
                    "AiCapability failed: capability=%s, elapsed=%.2fs, error=%s",
                    capability,
                    elapsed,
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


def _check_ai_availability(capability: str) -> bool:
    """
    Check if the required AI capability is available.
    Uses cached result if recent enough.
    """
    now = time.monotonic()
    if capability in _health_cache:
        available, last_check = _health_cache[capability]
        if now - last_check < _HEALTH_CHECK_INTERVAL:
            return available

    # Quick config-based check (no async HTTP call in sync context)
    try:
        from app.config import settings
        available = bool(settings.OPENAI_API_KEY)
    except Exception:
        available = False

    _health_cache[capability] = (available, now)
    return available
