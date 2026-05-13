"""
Dependency injection for FastAPI endpoints.

Provides: async DB session, current user extraction, RBAC helpers.
"""

from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# ── Database Engine & Session Factory ─────────────────────────
_engine: AsyncEngine = create_async_engine(
    settings.async_database_url,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session (auto-commits/rollbacks)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Pagination Helper ─────────────────────────────────────────
class PaginationParams:
    """Common pagination query parameters."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(
            20, ge=1, le=100, description="Items per page"
        ),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size

    @property
    def limit(self) -> int:
        return self.page_size


PaginationDep = Annotated[PaginationParams, Depends()]


# ── Current User (skeleton) ───────────────────────────────────
class CurrentUser:
    """Stub representing the authenticated user."""

    def __init__(self, user_id: str, tenant_id: str, role: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role


async def get_current_user() -> CurrentUser:
    """
    Extract and validate the current user from JWT.

    In production this decodes the Authorization Bearer token,
    validates signature / expiry, and loads the user record.
    """
    # TODO: Implement real JWT decoding
    return CurrentUser(user_id="system", tenant_id="default", role="admin")


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


# ── RBAC Helper ───────────────────────────────────────────────
def require_role(*allowed_roles: str):
    """Return a dependency that verifies the current user's role."""

    async def _check(current_user: CurrentUserDep) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not permitted. "
                f"Required one of: {allowed_roles}",
            )
        return current_user

    return _check


# Type aliases for convenience
DbSession = Annotated[AsyncSession, Depends(get_db)]
