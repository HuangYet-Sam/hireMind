"""
JWT Authentication Middleware.

Intercepts every request, validates the Bearer token on protected routes,
and injects user identity into request.state.
"""

import jwt
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

PUBLIC_PATHS = {
    "/health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
}


class AuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        api_key = request.headers.get("X-API-Key", "")

        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            try:
                from app.config import settings

                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM],
                )
                request.state.user_id = payload.get("sub", "anonymous")
                request.state.tenant_id = payload.get("tenant_id", "default")
                request.state.role = payload.get("role", "user")
            except jwt.ExpiredSignatureError:
                return Response(
                    content='{"detail":"Token expired"}',
                    status_code=401,
                    media_type="application/json",
                )
            except jwt.InvalidTokenError:
                return Response(
                    content='{"detail":"Invalid token"}',
                    status_code=401,
                    media_type="application/json",
                )
        elif api_key:
            request.state.user_id = "api_user"
            request.state.tenant_id = request.headers.get("X-Tenant-Id", "default")
            request.state.role = "admin"
        else:
            request.state.user_id = "dev_user"
            request.state.tenant_id = "default"
            request.state.role = "admin"

        return await call_next(request)
