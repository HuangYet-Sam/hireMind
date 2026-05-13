"""
Offer Service.

Business logic for creating, approving, sending, and tracking job offers.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.offer import OfferCreate, OfferUpdate


class OfferService:
    """Handles offer lifecycle: creation, approval workflow, and tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_offers(
        self,
        *,
        tenant_id: str,
        candidate_id: UUID | None = None,
        position_id: UUID | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list, int]:
        """Return paginated offers with optional filters."""
        return [], 0

    async def get_by_id(self, offer_id: UUID, tenant_id: str) -> dict | None:
        """Fetch a single offer."""
        return None

    async def create(self, data: OfferCreate, tenant_id: str, user_id: str) -> dict:
        """
        Create a new offer for a candidate.

        Sets initial status to 'draft'. Triggers approval workflow.
        """
        raise NotImplementedError

    async def update(self, offer_id: UUID, data: OfferUpdate, tenant_id: str) -> dict:
        """Update offer details (only in 'draft' status)."""
        raise NotImplementedError

    async def approve(
        self,
        offer_id: UUID,
        approver_id: str,
        comment: str | None,
        tenant_id: str,
    ) -> dict:
        """
        Approve an offer (multi-level approval).

        Advances the offer through the approval chain.
        If all approvals are collected, status becomes 'approved'.
        """
        raise NotImplementedError

    async def send(self, offer_id: UUID, tenant_id: str) -> dict:
        """Send the approved offer to the candidate. Changes status to 'sent'."""
        raise NotImplementedError

    async def withdraw(self, offer_id: UUID, tenant_id: str) -> None:
        """Withdraw (cancel) an offer."""
        raise NotImplementedError
