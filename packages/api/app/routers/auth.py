"""
Auth Router — Login endpoint to issue JWT tokens.

POST /api/v1/auth/login  (public, no auth required)
"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.schemas.auth import LoginRequest, LoginResponse, UserInfo

router = APIRouter()

# M1: Hardcoded admin user.  Password from settings.ADMIN_PASSWORD (env ADMIN_PASSWORD, default: Admin@123)
ADMIN_USERNAME = "admin"
ADMIN_USER_ID = "admin"
ADMIN_TENANT_ID = "default"
ADMIN_ROLE = "hr_admin"
ADMIN_EMAIL = "admin@hiremind.local"
ADMIN_NAME = "Admin"


def _create_access_token(
    user_id: str, tenant_id: str, role: str, expires_delta: timedelta | None = None
) -> str:
    """Sign a JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(body: LoginRequest) -> LoginResponse:
    """
    Authenticate user and return a JWT access token.

    M1 milestone: only the hardcoded admin user is supported.
    """
    if body.username != ADMIN_USERNAME or body.password != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = _create_access_token(
        user_id=ADMIN_USER_ID,
        tenant_id=ADMIN_TENANT_ID,
        role=ADMIN_ROLE,
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserInfo(
            user_id=ADMIN_USER_ID,
            tenant_id=ADMIN_TENANT_ID,
            role=ADMIN_ROLE,
            email=ADMIN_EMAIL,
            name=ADMIN_NAME,
        ),
    )
