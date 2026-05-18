"""
Offer Service.

Business logic for creating, approving, sending, and managing job offers.
Includes approval workflow, template rendering, counter-offer, and status timeline.
"""

import json
import logging
import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.offer import Offer, OfferApproval
from app.models.offer_template import OfferTemplate
from app.models.position import Position
from app.schemas.offer import OfferCreate, OfferUpdate

logger = logging.getLogger("hiremind.services.offer")

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

    # ------------------------------------------------------------------
    # Approval workflow
    # ------------------------------------------------------------------

    async def submit_for_approval(self, offer_id: UUID, tenant_id: str) -> Offer:
        """Submit a draft offer for approval.

        Reads the approval_chain configuration from the offer (or defaults
        to a simple single-approver chain) and creates pending approval
        records for each approver in the chain.
        """
        offer = await self.get_by_id(offer_id, tenant_id)
        if offer is None:
            raise ValueError("Offer not found")

        if offer.status != "draft":
            raise ValueError("Only draft offers can be submitted for approval")

        # Determine approval chain — for now default to a single-step chain.
        # In production this would come from tenant/position configuration.
        approval_chain = [
            {"approver_id": "default_approver", "approver_name": "HR Manager"},
        ]

        for idx, step in enumerate(approval_chain):
            approval = OfferApproval(
                offer_id=offer_id,
                approver_id=step["approver_id"],
                approver_name=step.get("approver_name"),
                status="pending",
                approval_order=idx + 1,
            )
            self.db.add(approval)

        offer.status = "pending_approval"
        await self.db.flush()
        await self.db.refresh(offer)
        logger.info("Offer %s submitted for approval", offer_id)
        return offer

    async def process_approval(
        self,
        offer_id: UUID,
        approver_id: str,
        action: str,
        comment: str | None,
        tenant_id: str,
    ) -> Offer:
        """Process an approval action (approve / reject / withdraw / counter).

        Supports multi-level approval chains.  When all pending approvals
        are cleared the offer transitions to *approved*.
        """
        offer = await self.get_by_id(offer_id, tenant_id)
        if offer is None:
            raise ValueError("Offer not found")

        if offer.status != "pending_approval":
            raise ValueError("Offer is not pending approval")

        # Find the pending approval record for this approver
        pending_stmt = select(OfferApproval).where(
            OfferApproval.offer_id == offer_id,
            OfferApproval.approver_id == approver_id,
            OfferApproval.status == "pending",
        )
        approval_record = (await self.db.execute(pending_stmt)).scalar_one_or_none()
        if approval_record is None:
            raise ValueError("No pending approval found for this approver")

        now = datetime.now(timezone.utc)

        if action == "approve":
            approval_record.status = "approved"
            approval_record.approved_at = now
            approval_record.comment = comment
        elif action == "reject":
            approval_record.status = "rejected"
            approval_record.approved_at = now
            approval_record.comment = comment
            offer.status = "rejected"
            await self.db.flush()
            await self.db.refresh(offer)
            return offer
        elif action == "withdraw":
            offer.status = "withdrawn"
            if comment:
                offer.response_note = comment
            await self.db.flush()
            await self.db.refresh(offer)
            return offer
        elif action == "counter":
            # Counter-offer keeps the offer in pending_approval
            approval_record.status = "counter"
            approval_record.approved_at = now
            approval_record.comment = comment
        else:
            raise ValueError(f"Unsupported approval action: {action}")

        await self.db.flush()

        # Check if all approvals are resolved
        remaining_stmt = select(func.count()).select_from(OfferApproval).where(
            OfferApproval.offer_id == offer_id,
            OfferApproval.status == "pending",
        )
        remaining = (await self.db.execute(remaining_stmt)).scalar_one()
        if remaining == 0:
            offer.status = "approved"
            logger.info("All approvals completed for offer %s", offer_id)

        await self.db.flush()
        await self.db.refresh(offer)
        return offer

    async def get_approval_history(self, offer_id: UUID) -> list[OfferApproval]:
        """Return all approval records for an offer, ordered by step."""
        stmt = (
            select(OfferApproval)
            .where(OfferApproval.offer_id == offer_id)
            .order_by(OfferApproval.approval_order, OfferApproval.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Counter-offer
    # ------------------------------------------------------------------

    async def counter_offer(
        self,
        offer_id: UUID,
        tenant_id: str,
        data: dict,
    ) -> Offer:
        """Process a counter-offer by updating compensation fields.

        Resets the offer back to *pending_approval* so the new terms go
        through the approval chain again.
        """
        offer = await self.get_by_id(offer_id, tenant_id)
        if offer is None:
            raise ValueError("Offer not found")

        allowed_fields = {
            "base_salary", "annual_bonus_months", "sign_on_bonus",
            "equity", "benefits_summary", "notes",
        }
        for key, value in data.items():
            if key in allowed_fields and value is not None:
                setattr(offer, key, value)

        # Reset status to draft so it can be re-submitted
        offer.status = "draft"
        await self.db.flush()
        await self.db.refresh(offer)
        logger.info("Counter-offer processed for offer %s", offer_id)
        return offer

    # ------------------------------------------------------------------
    # Status timeline
    # ------------------------------------------------------------------

    async def get_status_timeline(self, offer_id: UUID, tenant_id: str) -> list[dict]:
        """Build a status-change timeline from the offer and its approvals."""
        offer = await self.get_by_id(offer_id, tenant_id)
        if offer is None:
            raise ValueError("Offer not found")

        timeline: list[dict] = []

        # Initial creation
        timeline.append({
            "status": "draft",
            "changed_at": offer.created_at.isoformat() if offer.created_at else None,
            "changed_by": offer.created_by,
            "comment": None,
        })

        # Approval history
        approvals = await self.get_approval_history(offer_id)
        for appr in approvals:
            if appr.approved_at:
                timeline.append({
                    "status": appr.status,
                    "changed_at": appr.approved_at.isoformat(),
                    "changed_by": appr.approver_id,
                    "comment": appr.comment,
                })

        # Major status changes
        if offer.sent_at:
            timeline.append({
                "status": "sent",
                "changed_at": offer.sent_at.isoformat(),
                "changed_by": None,
                "comment": None,
            })
        if offer.responded_at:
            timeline.append({
                "status": offer.status,
                "changed_at": offer.responded_at.isoformat(),
                "changed_by": None,
                "comment": offer.response_note,
            })

        # Sort by timestamp
        timeline.sort(key=lambda e: e["changed_at"] or "")
        return timeline

    # ------------------------------------------------------------------
    # Template rendering
    # ------------------------------------------------------------------

    async def render_offer_letter(
        self,
        offer_id: UUID,
        template_id: UUID | None,
        tenant_id: str,
    ) -> str:
        """Render an offer letter by substituting template variables."""
        offer = await self.get_by_id(offer_id, tenant_id)
        if offer is None:
            raise ValueError("Offer not found")

        # Load template
        if template_id is not None:
            tpl_stmt = select(OfferTemplate).where(
                OfferTemplate.id == template_id,
                OfferTemplate.tenant_id == tenant_id,
            )
        else:
            tpl_stmt = (
                select(OfferTemplate)
                .where(
                    OfferTemplate.tenant_id == tenant_id,
                    OfferTemplate.is_default == True,  # noqa: E712
                )
                .limit(1)
            )
        template = (await self.db.execute(tpl_stmt)).scalar_one_or_none()
        if template is None:
            raise ValueError("Offer template not found")

        # Gather candidate info
        cand_stmt = select(Candidate).where(Candidate.id == offer.candidate_id)
        candidate = (await self.db.execute(cand_stmt)).scalar_one_or_none()

        # Gather position info
        position_title = ""
        if offer.position_id:
            pos_stmt = select(Position).where(Position.id == offer.position_id)
            position = (await self.db.execute(pos_stmt)).scalar_one_or_none()
            if position:
                position_title = position.title

        # Build variable map
        variables = {
            "candidate_name": candidate.name if candidate else "候选人",
            "position_title": position_title,
            "base_salary": str(offer.base_salary or ""),
            "annual_bonus_months": str(offer.annual_bonus_months or ""),
            "sign_on_bonus": str(offer.sign_on_bonus or ""),
            "equity": offer.equity or "",
            "benefits_summary": offer.benefits_summary or "",
            "proposed_start_date": str(offer.proposed_start_date or ""),
            "probation_months": str(offer.probation_months or "3"),
            "work_location": offer.work_location or "",
            "employment_type": offer.employment_type or "",
            "company_name": "公司",
            "offer_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }

        # Substitute {{variable}} placeholders
        content = template.content
        for var_name, var_value in variables.items():
            content = content.replace("{{" + var_name + "}}", var_value)

        # Clean up any unreplaced placeholders
        content = re.sub(r"\{\{(\w+)\}\}", r"[待填: \1]", content)

        logger.info("Rendered offer letter for offer %s using template %s", offer_id, template_id)
        return content

    # ------------------------------------------------------------------
    # Template listing
    # ------------------------------------------------------------------

    async def list_templates(
        self,
        tenant_id: str,
        template_type: str | None = None,
    ) -> list[OfferTemplate]:
        """List available offer templates for a tenant."""
        filters = [OfferTemplate.tenant_id == tenant_id]
        if template_type:
            filters.append(OfferTemplate.template_type == template_type)

        stmt = (
            select(OfferTemplate)
            .where(*filters)
            .order_by(OfferTemplate.is_default.desc(), OfferTemplate.name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_template(
        self,
        name: str,
        template_type: str,
        content: str,
        variables: list[str],
        is_default: bool,
        tenant_id: str,
    ) -> OfferTemplate:
        """Create a new offer template."""
        # If this is set as default, unset other defaults of same type
        if is_default:
            existing_stmt = select(OfferTemplate).where(
                OfferTemplate.tenant_id == tenant_id,
                OfferTemplate.template_type == template_type,
                OfferTemplate.is_default == True,  # noqa: E712
            )
            existing = (await self.db.execute(existing_stmt)).scalars().all()
            for tpl in existing:
                tpl.is_default = False

        template = OfferTemplate(
            name=name,
            template_type=template_type,
            content=content,
            variables=variables,
            is_default=is_default,
            tenant_id=tenant_id,
        )
        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)
        return template
