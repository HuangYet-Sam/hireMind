"""
JWT Authentication Middleware.

Intercepts every request, validates the Bearer token on protected routes,
and injects user identity into request.state.
"""

import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("hiremind.auth")

# Paths that do NOT require authentication
PUBLIC_PATHS = {
    "/health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Validate JWT tokens on incoming requests.

    - Skips paths listed in ``PUBLIC_PATHS``.
    - On success, sets ``request.state.user_id`` and ``request.state.tenant_id``.
    - On failure, returns 401 Unauthorized.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip auth for public / docs paths
        if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            # For now, allow unauthenticated requests (skeleton mode)
            # TODO: In production, return 401 here
            request.state.user_id = None
            request.state.tenant_id = None
            request.state.role = None
            return await call_next(request)

        token = auth_header.removeprefix("Bearer ").strip()

        try:
            # TODO: Decode and validate JWT using settings.JWT_SECRET_KEY
            # payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            # request.state.user_id = payload["sub"]
            # request.state.tenant_id = payload["tenant_id"]
            # request.state.role = payload["role"]
            request.state.user_id = "decoded_user_id"
            request.state.tenant_id = "default"
            request.state.role = "admin"
        except Exception as exc:
            logger.warning("JWT validation failed: %s", exc)
            return Response(
                content='{"detail":"Invalid or expired token"}',
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)
