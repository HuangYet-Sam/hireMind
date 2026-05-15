"""
Offer Service.

Business logic for creating, approving, sending, and managing job offers.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.offer import Offer, OfferApproval
from app.models.position import Position
from app.schemas.offer import OfferCreate, OfferUpdate

_UPDATABLE_FIELDS = frozenset({
    "base_salary",
    "annual_bonus_months",
    "sign_on_bonus",
    "equity",
    "benefits_summary",
    "proposed_start_date",
    "probation_months",
    "work_location",
    "employment_type",
    "notes",
    "expiry_date",
})

_SEND_ALLOWED_STATUSES = frozenset({"approved"})
_DRAFT_STATUSES = frozenset({"draft"})


class OfferService:

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
    ) -> tuple[list[Offer], int]:
        filters = [Offer.tenant_id == tenant_id]
        if candidate_id is not None:
            filters.append(Offer.candidate_id == candidate_id)
        if position_id is not None:
            filters.append(Offer.position_id == position_id)
        if status is not None:
            filters.append(Offer.status == status)

        count_stmt = select(func.count()).select_from(Offer).where(*filters)
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = (
            select(Offer)
            .where(*filters)
            .order_by(Offer.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def get_by_id(self, offer_id: UUID, tenant_id: str) -> Offer | None:
        stmt = select(Offer).where(
            Offer.id == offer_id,
            Offer.tenant_id == tenant_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        data: OfferCreate,
        tenant_id: str,
        user_id: str,
    ) -> Offer:
        cand_stmt = select(Candidate).where(
            Candidate.id == data.candidate_id,
            Candidate.tenant_id == tenant_id,
        )
        candidate = (await self.db.execute(cand_stmt)).scalar_one_or_none()
        if candidate is None:
            raise ValueError("Candidate not found")

        if data.position_id is not None:
            pos_stmt = select(Position).where(
                Position.id == data.position_id,
                Position.tenant_id == tenant_id,
            )
            position = (await self.db.execute(pos_stmt)).scalar_one_or_none()
            if position is None:
                raise ValueError("Position not found")

        offer = Offer(
            candidate_id=data.candidate_id,
            position_id=data.position_id,
            base_salary=data.base_salary,
            annual_bonus_months=data.annual_bonus_months,
            sign_on_bonus=data.sign_on_bonus,
            equity=data.equity,
            benefits_summary=data.benefits_summary,
            proposed_start_date=data.proposed_start_date,
            probation_months=data.probation_months if data.probation_months is not None else 3,
            work_location=data.work_location,
            employment_type=data.employment_type,
            notes=data.notes,
            expiry_date=data.expiry_date,
            status="draft",
            tenant_id=tenant_id,
            created_by=user_id,
        )
        self.db.add(offer)
        await self.db.flush()
        await self.db.refresh(offer)
        return offer

    async def update(
        self,
        offer_id: UUID,
        data: OfferUpdate,
        tenant_id: str,
    ) -> Offer:
        offer = await self.get_by_id(offer_id, tenant_id)
        if offer is None:
            raise ValueError("Offer not found")

        if offer.status not in _DRAFT_STATUSES:
            raise ValueError("Only draft offers can be updated")

        update_data = data.model_dump(exclude_unset=True)
        for field in update_data:
            if field not in _UPDATABLE_FIELDS:
                raise ValueError(f"Field '{field}' is not updatable")

        for key, value in update_data.items():
            setattr(offer, key, value)

        await self.db.flush()
        await self.db.refresh(offer)
        return offer

    async def approve(
        self,
        offer_id: UUID,
        approver_id: str,
        approver_name: str | None,
        comment: str | None,
        tenant_id: str,
    ) -> Offer:
        offer = await self.get_by_id(offer_id, tenant_id)
        if offer is None:
            raise ValueError("Offer not found")

        if offer.status == "draft":
            offer.status = "pending_approval"
            self.db.add(offer)
            await self.db.flush()
            await self.db.refresh(offer)

        if offer.status != "pending_approval":
            raise ValueError("Offer is not pending approval")

        existing_stmt = select(OfferApproval).where(
            OfferApproval.offer_id == offer_id,
            OfferApproval.approver_id == approver_id,
        )
        existing_record = (await self.db.execute(existing_stmt)).scalar_one_or_none()
        if existing_record is not None:
            raise ValueError("Approver has already acted on this offer")

        max_order_stmt = select(func.coalesce(func.max(OfferApproval.approval_order), 0)).where(
            OfferApproval.offer_id == offer_id,
        )
        max_order = (await self.db.execute(max_order_stmt)).scalar_one()

        approval = OfferApproval(
            offer_id=offer_id,
            approver_id=approver_id,
            approver_name=approver_name,
            status="approved",
            comment=comment,
            approved_at=datetime.now(timezone.utc),
            approval_order=max_order + 1,
        )
        self.db.add(approval)
        await self.db.flush()

        # Refresh to pick up relationship changes

        pending_count_stmt = select(func.count()).select_from(OfferApproval).where(
            OfferApproval.offer_id == offer_id,
            OfferApproval.status == "pending",
        )
        pending_count = (await self.db.execute(pending_count_stmt)).scalar_one()

        if pending_count == 0:
            offer.status = "approved"
            await self.db.flush()

        await self.db.refresh(offer)
        return offer

    async def send(self, offer_id: UUID, tenant_id: str) -> Offer:
        offer = await self.get_by_id(offer_id, tenant_id)
        if offer is None:
            raise ValueError("Offer not found")

        if offer.status not in _SEND_ALLOWED_STATUSES:
            raise ValueError("Offer must be approved before sending")

        offer.status = "sent"
        offer.sent_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(offer)
        return offer

    async def withdraw(self, offer_id: UUID, tenant_id: str, reason: str | None = None) -> Offer:
        offer = await self.get_by_id(offer_id, tenant_id)
        if offer is None:
            raise ValueError("Offer not found")

        if offer.status == "withdrawn":
            raise ValueError("Offer is already withdrawn")

        offer.status = "withdrawn"
        if reason is not None:
            offer.response_note = reason
        await self.db.flush()
        await self.db.refresh(offer)
        return offer
