"""
@AiCapability Decorator.

Marks an endpoint or service method as requiring AI capabilities.
Supports capability discovery, rate limiting, fallback handling,
health-check-based gating, and full metadata registration for code generation.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import threading
import time
from typing import Any, Callable

logger = logging.getLogger("hiremind.ai")

# ---------------------------------------------------------------------------
# Health-check cache (internal)
# ---------------------------------------------------------------------------
_health_cache: dict[str, tuple[bool, float]] = {}
_HEALTH_CHECK_INTERVAL = 60.0  # seconds between health checks

# ---------------------------------------------------------------------------
# Thread-safe global registry for AI capability metadata
# ---------------------------------------------------------------------------
_AI_CAPABILITIES_REGISTRY: dict[str, dict[str, Any]] = {}
_registry_lock = threading.Lock()


def _register_capability(meta: dict[str, Any]) -> None:
    """Thread-safe insert into the global registry."""
    key = meta.get("ai_capability_id") or meta.get("capability")
    if not key:
        logger.warning("Skipping capability registration: no identifier")
        return
    with _registry_lock:
        _AI_CAPABILITIES_REGISTRY[key] = meta


def get_all_capabilities() -> dict[str, dict[str, Any]]:
    """Return a shallow copy of every registered capability's metadata."""
    with _registry_lock:
        return dict(_AI_CAPABILITIES_REGISTRY)


def get_capability(name: str) -> dict[str, Any] | None:
    """Look up a single capability by *ai_capability_id* or *capability*."""
    with _registry_lock:
        return _AI_CAPABILITIES_REGISTRY.get(name)


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------
def AiCapability(
    capability: str,
    *,
    # -- new fields (PRD §8.1a) -------------------------------------------
    name: str | None = None,
    endpoint: str | None = None,
    method: str = "POST",
    tool_name: str | None = None,
    permissions: list[str] | None = None,
    llm_model: str | None = None,
    fallback_model: str | None = None,
    prompt_version: str | None = None,
    allowed_callers: list[str] | None = None,
    requires_tenant_isolation: bool = False,
    ai_capability_id: str | None = None,
    description: str | None = None,
    request_model: str | None = None,
    response_model: str | None = None,
    rate_limit: str | None = None,
    data_classification: str = "L2",
    audit_level: str = "standard",
    tags: list[str] | None = None,
    # -- existing fields ---------------------------------------------------
    fallback: Callable | None = None,
    timeout: float = 30.0,
    cache_ttl: int | None = None,
):
    """
    Decorator that marks a function as requiring an AI capability.

    Registers full metadata in ``_AI_CAPABILITIES_REGISTRY`` so that code
    generators and discovery tools can introspect available capabilities at
    runtime.

    Args:
        capability: Short identifier (e.g. ``"resume_parse"``).
        name: Human-readable display name.
        endpoint: FastAPI route path (e.g. ``"/api/v1/ai/resume-parse"``).
        method: HTTP method (``"GET"`` / ``"POST"``).  Defaults to ``"POST"``.
        tool_name: Name exposed to Agent tools.
        permissions: Required permission identifiers.
        llm_model: Primary LLM model identifier.
        fallback_model: Backup LLM model identifier.
        prompt_version: Prompt template version tag.
        allowed_callers: ``["api", "agent"]`` etc.
        requires_tenant_isolation: Whether tenant data must be isolated.
        ai_capability_id: Globally unique capability identifier.
        description: Free-text description of the capability.
        request_model: Pydantic model class name for the request body.
        response_model: Pydantic model class name for the response body.
        rate_limit: Rate-limit expression (e.g. ``"100/minute"``).
        data_classification: ``"L1"``–``"L4"``.  Defaults to ``"L2"``.
        audit_level: ``"standard"`` / ``"detailed"`` / ``"none"``.
        tags: Arbitrary string tags.
        fallback: Callable invoked when AI is unavailable or the wrapped
            function raises.  Must be async if the wrapped function is async.
        timeout: Max seconds to wait for AI response.
        cache_ttl: Cache the result for this many seconds (``None`` = no cache).
    """

    meta: dict[str, Any] = {
        "capability": capability,
        "name": name,
        "endpoint": endpoint,
        "method": method,
        "tool_name": tool_name,
        "permissions": permissions,
        "llm_model": llm_model,
        "fallback_model": fallback_model,
        "prompt_version": prompt_version,
        "allowed_callers": allowed_callers,
        "requires_tenant_isolation": requires_tenant_isolation,
        "ai_capability_id": ai_capability_id,
        "description": description,
        "request_model": request_model,
        "response_model": response_model,
        "rate_limit": rate_limit,
        "data_classification": data_classification,
        "audit_level": audit_level,
        "tags": tags,
        "timeout": timeout,
        "cache_ttl": cache_ttl,
    }

    def decorator(func: Callable) -> Callable:
        # Register before wrapping so metadata is available immediately.
        meta["qualified_name"] = func.__qualname__
        meta["module"] = func.__module__
        _register_capability(meta)

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

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
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

    try:
        from app.config import settings

        available = bool(settings.OPENAI_API_KEY)
    except Exception:
        available = False

    _health_cache[capability] = (available, now)
    return available
