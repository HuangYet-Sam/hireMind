"""
Position Service.

Business logic for creating, querying, and managing job positions.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.position import PositionCreate, PositionUpdate


class PositionService:
    """Handles all position-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_positions(
        self,
        *,
        tenant_id: str,
        department_id: UUID | None = None,
        status: str | None = None,
        keyword: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list, int]:
        """
        Return a paginated list of positions for the given tenant.

        Returns:
            (items, total_count)
        """
        # TODO: implement with SQLAlchemy select + where + count
        return [], 0

    async def get_by_id(self, position_id: UUID, tenant_id: str) -> dict | None:
        """Fetch a single position by ID. Returns None if not found."""
        # TODO: implement
        return None

    async def create(self, data: PositionCreate, tenant_id: str, user_id: str) -> dict:
        """
        Create a new position record.

        Args:
            data: Validated creation payload.
            tenant_id: Tenant owning this position.
            user_id: Creator's user ID.

        Returns:
            The created position as a dict.
        """
        # TODO: implement
        raise NotImplementedError

    async def update(self, position_id: UUID, data: PositionUpdate, tenant_id: str) -> dict:
        """Update position fields. Raises if not found."""
        # TODO: implement
        raise NotImplementedError

    async def soft_delete(self, position_id: UUID, tenant_id: str) -> None:
        """Mark position as 'closed' (soft delete). Raises if not found."""
        # TODO: implement
        raise NotImplementedError
