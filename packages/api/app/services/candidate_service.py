"""
Candidate Service.

Business logic for managing candidates throughout the hiring pipeline.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.candidate import CandidateCreate, CandidateUpdate


class CandidateService:
    """Handles all candidate-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_candidates(
        self,
        *,
        tenant_id: str,
        position_id: UUID | None = None,
        status: str | None = None,
        keyword: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list, int]:
        """
        Return a paginated list of candidates.

        Supports filtering by position, status, and keyword search.
        """
        # TODO: implement
        return [], 0

    async def get_by_id(self, candidate_id: UUID, tenant_id: str) -> dict | None:
        """Fetch a single candidate by ID."""
        return None

    async def create(self, data: CandidateCreate, tenant_id: str, user_id: str) -> dict:
        """Register a new candidate."""
        raise NotImplementedError

    async def update(self, candidate_id: UUID, data: CandidateUpdate, tenant_id: str) -> dict:
        """Update candidate information."""
        raise NotImplementedError

    async def soft_delete(self, candidate_id: UUID, tenant_id: str) -> None:
        """Soft-delete a candidate record."""
        raise NotImplementedError

    async def advance_stage(self, candidate_id: UUID, new_stage: str, tenant_id: str) -> dict:
        """Move a candidate to the next stage in the hiring pipeline."""
        raise NotImplementedError
