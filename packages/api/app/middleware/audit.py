"""
Audit Log Middleware.

Automatically records every API request into the audit trail
for compliance and debugging purposes. Persists records to the
audit_logs table asynchronously so the response is never blocked.
"""

import asyncio
import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("hiremind.audit")

# Paths that should be excluded from audit persistence (health checks, docs).
PUBLIC_PATHS = ("/health", "/api/docs", "/api/redoc", "/openapi.json")


async def _persist_audit_record(
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    user_id: str | None,
    tenant_id: str | None,
    duration_ms: float,
    client_ip: str | None,
    user_agent: str | None,
) -> None:
    """
    Fire-and-forget coroutine that writes an AuditLog row.

    Creates its own database session so it does not depend on the
    request-lifetime session.  Any database error is logged but never
    propagates to the caller.
    """
    # Import here to avoid circular imports at module level.
    from app.dependencies import AsyncSessionLocal
    from app.models.audit_log import AuditLog

    try:
        async with AsyncSessionLocal() as session:
            record = AuditLog(
                request_id=request_id,
                method=method,
                path=path,
                status_code=status_code,
                user_id=user_id,
                tenant_id=tenant_id,
                duration_ms=duration_ms,
                client_ip=client_ip,
                user_agent=user_agent,
            )
            session.add(record)
            await session.commit()
    except Exception:
        logger.exception(
            "audit_persist_failed request_id=%s path=%s",
            request_id,
            path,
        )


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Log every API call with timing, user, and status information.

    - Generates a unique ``request_id`` (UUID4).
    - Attaches it to ``request.state.request_id`` and the ``X-Request-ID`` response header.
    - Emits a structured log line after the response is ready.
    - Persists the audit record to the ``audit_logs`` table via an async
      background task so the response is never delayed.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        user_id = getattr(request.state, "user_id", None) or "anonymous"
        tenant_id = getattr(request.state, "tenant_id", None)
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Structured log — always emitted regardless of DB persistence.
        logger.info(
            "audit request_id=%s method=%s path=%s status=%d user=%s tenant=%s duration=%.2fms",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            user_id,
            tenant_id,
            elapsed_ms,
        )

        # Skip persistence for health-check and documentation paths.
        if not request.url.path.startswith(PUBLIC_PATHS):
            asyncio.create_task(
                _persist_audit_record(
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    user_id=user_id if user_id != "anonymous" else None,
                    tenant_id=tenant_id,
                    duration_ms=elapsed_ms,
                    client_ip=client_ip,
                    user_agent=user_agent,
                )
            )

        return response
