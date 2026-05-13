"""
Audit Log Middleware.

Automatically records every API request into the audit trail
for compliance and debugging purposes.
"""

import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("hiremind.audit")


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Log every API call with timing, user, and status information.

    - Generates a unique ``request_id`` (UUID4).
    - Attaches it to ``request.state.request_id`` and the ``X-Request-ID`` response header.
    - Emits a structured log line after the response is ready.
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

        logger.info(
            "audit request_id=%s method=%s path=%s status=%d user=%s duration=%.2fms",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            user_id,
            elapsed_ms,
        )

        # TODO: Persist to a dedicated audit_log table / external service

        return response
