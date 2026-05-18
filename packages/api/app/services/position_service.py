"""
Position Service.

Business logic for creating, querying, and managing job positions.
"""

import json
import logging
import re
from uuid import UUID

from sqlalchemy import func, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.decorators.ai_capability import AiCapability
from app.models.department import Department
from app.models.position import Position
from app.schemas.position import PositionCreate, PositionUpdate
from app.services.ai_client import ai_client
from app.services.pii_masking import PIIMaskingService

logger = logging.getLogger("hiremind.position")

_VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"open"},
    "open": {"paused", "closed"},
    "paused": {"open", "closed"},
    "closed": set(),
    "filled": set(),
}


class PositionService:

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
    ) -> tuple[list[Position], int]:
        filters = [Position.tenant_id == tenant_id]
        if department_id is not None:
            filters.append(Position.department_id == department_id)
        if status is not None:
            filters.append(Position.status == status)
        if keyword is not None:
            escaped = re.sub(r'([\\%_])', r'\\\1', keyword.strip())
            filters.append(Position.title.ilike(f"%{escaped}%"))

        count_stmt = select(func.count()).select_from(Position).where(*filters)
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = (
            select(Position)
            .where(*filters)
            .order_by(Position.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def get_by_id(self, position_id: UUID, tenant_id: str) -> Position | None:
        stmt = select(Position).where(
            Position.id == position_id,
            Position.tenant_id == tenant_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        data: PositionCreate,
        tenant_id: str,
        user_id: str,
    ) -> Position:
        if data.department_id is not None:
            dept_stmt = select(Department).where(
                Department.id == data.department_id,
                Department.tenant_id == tenant_id,
            )
            dept = (await self.db.execute(dept_stmt)).scalar_one_or_none()
            if dept is None:
                raise ValueError("Department not found")

        try:
            created_by = UUID(user_id) if isinstance(user_id, str) else user_id
        except (ValueError, AttributeError):
            created_by = None

        position = Position(
            title=data.title,
            department_id=data.department_id,
            location=data.location,
            employment_type=data.employment_type,
            headcount=data.headcount,
            priority=data.priority,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            description=data.description,
            requirements=data.requirements,
            benefits=data.benefits,
            required_skills=data.required_skills,
            preferred_skills=data.preferred_skills,
            education_requirement=data.education_requirement,
            experience_years_min=data.experience_years_min,
            is_remote=data.is_remote,
            status="draft",
            tenant_id=tenant_id,
            created_by=created_by,
        )
        self.db.add(position)
        await self.db.flush()
        await self.db.refresh(position)
        return position

    async def update(
        self,
        position_id: UUID,
        data: PositionUpdate,
        tenant_id: str,
    ) -> Position:
        position = await self.get_by_id(position_id, tenant_id)
        if position is None:
            raise ValueError("Position not found")

        update_data = data.model_dump(exclude_unset=True)

        new_status = update_data.get("status")
        if new_status is not None and new_status != position.status:
            allowed = _VALID_TRANSITIONS.get(position.status, set())
            if new_status not in allowed:
                raise ValueError(
                    f"Invalid status transition: {position.status} -> {new_status}"
                )

        old_version = position.version
        stmt = (
            sa_update(Position)
            .where(Position.id == position_id, Position.version == old_version)
            .values(**update_data, version=old_version + 1)
            .returning(Position)
        )
        result = await self.db.execute(stmt)
        updated = result.scalar_one_or_none()
        if updated is None:
            raise ValueError("Concurrent update conflict")
        return updated

    async def soft_delete(self, position_id: UUID, tenant_id: str) -> None:
        position = await self.get_by_id(position_id, tenant_id)
        if position is None:
            raise ValueError("Position not found")

        if position.status == "closed":
            return

        stmt = (
            sa_update(Position)
            .where(
                Position.id == position_id,
                Position.tenant_id == tenant_id,
            )
            .values(status="closed")
        )
        await self.db.execute(stmt)
        await self.db.flush()

    # ── AI Capabilities ──────────────────────────────────────────

    @AiCapability(
        capability="ai_interpret_jd",
        name="AI JD Interpretation",
        endpoint="/api/v1/positions/ai-interpret",
        method="POST",
        tool_name="interpret_jd",
        permissions=["position:create"],
        llm_model="gpt-4",
        fallback_model="gpt-3.5-turbo",
        prompt_version="v1",
        allowed_callers=["api", "agent"],
        requires_tenant_isolation=True,
        ai_capability_id="position_ai_interpret_jd",
        description="AI interprets natural language JD into structured position data",
        request_model="AIInterpretRequest",
        response_model="AIInterpretResponse",
        rate_limit="30/minute",
        data_classification="L2",
        audit_level="detailed",
        tags=["ai", "jd", "position"],
        timeout=30.0,
        cache_ttl=300,
    )
    async def ai_interpret_jd(self, text: str) -> dict:
        """
        Use AI to interpret a natural-language job description.

        Flow: mask PII → LLM call → unmask PII → return structured data.
        """
        pii = PIIMaskingService()

        masked_text, mapping = await pii.mask(text)

        raw = await ai_client.interpret_jd(masked_text)
        if raw is None:
            raise ValueError("AI JD interpretation failed: no response from LLM")

        # Unmask any PII that the LLM echoed back
        unmasked_raw = await pii.unmask(json.dumps(raw, ensure_ascii=False), mapping)
        result = json.loads(unmasked_raw)

        logger.info("ai_interpret_jd completed title=%s", result.get("title"))
        return result

    @AiCapability(
        capability="ai_confirm_jd",
        name="AI JD Confirm & Create",
        endpoint="/api/v1/positions/ai-confirm",
        method="POST",
        tool_name="confirm_jd",
        permissions=["position:create"],
        llm_model="gpt-4",
        allowed_callers=["api"],
        requires_tenant_isolation=True,
        ai_capability_id="position_ai_confirm_jd",
        description="Confirm AI-interpreted JD and create position as draft",
        request_model="AIConfirmRequest",
        response_model="PositionResponse",
        rate_limit="30/minute",
        data_classification="L2",
        audit_level="detailed",
        tags=["ai", "jd", "position", "create"],
        timeout=15.0,
    )
    async def ai_confirm_jd(
        self,
        data: dict,
        tenant_id: str,
        user_id: str,
        department_id: UUID | None = None,
    ) -> Position:
        """
        Create a position from AI-interpreted structured data (status=draft).
        """
        create_data = PositionCreate(
            title=data.get("title", "Untitled Position"),
            department_id=department_id,
            location=data.get("location"),
            employment_type=data.get("employment_type", "full_time"),
            headcount=data.get("headcount", 1),
            priority=data.get("priority", "normal"),
            salary_min=data.get("salary_min"),
            salary_max=data.get("salary_max"),
            description=data.get("description"),
            requirements=data.get("requirements"),
            benefits=data.get("benefits"),
            required_skills=[{"name": s} for s in data.get("required_skills") or []],
            preferred_skills=data.get("preferred_skills"),
            education_requirement=data.get("education_requirement"),
            experience_years_min=data.get("experience_years_min"),
            is_remote=data.get("is_remote", False),
        )

        position = await self.create(
            data=create_data,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        logger.info("ai_confirm_jd created position_id=%s title=%s", position.id, position.title)
        return position
