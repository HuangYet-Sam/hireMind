"""
RBAC (Role-Based Access Control) Middleware.

Checks whether the authenticated user has the required role to access
the requested endpoint.  Works in concert with the Auth middleware.
"""

import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("hiremind.rbac")

# Role hierarchy: higher index = more permissions
ROLE_HIERARCHY = ["viewer", "recruiter", "hr_manager", "admin"]

# Endpoint prefix → minimum role required
RBAC_RULES: dict[str, str] = {
    "/api/v1/analytics": "hr_manager",
    "/api/v1/offers": "hr_manager",
}


class RBACMiddleware(BaseHTTPMiddleware):
    """
    Enforce role-based access control.

    - Reads ``request.state.role`` set by ``AuthMiddleware``.
    - Matches the request path against ``RBAC_RULES``.
    - Returns 403 if the user's role is insufficient.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        user_role = getattr(request.state, "role", None)

        if user_role is None:
            # Auth middleware hasn't set a role; allow through (public or skeleton mode)
            return await call_next(request)

        for path_prefix, min_role in RBAC_RULES.items():
            if request.url.path.startswith(path_prefix):
                user_level = ROLE_HIERARCHY.index(user_role) if user_role in ROLE_HIERARCHY else -1
                required_level = ROLE_HIERARCHY.index(min_role) if min_role in ROLE_HIERARCHY else 999
                if user_level < required_level:
                    logger.warning(
                        "RBAC denied: user_role=%s, required=%s, path=%s",
                        user_role,
                        min_role,
                        request.url.path,
                    )
                    return Response(
                        content='{"detail":"Insufficient permissions"}',
                        status_code=403,
                        media_type="application/json",
                    )
                break

        return await call_next(request)
