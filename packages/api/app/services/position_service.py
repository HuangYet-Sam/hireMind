"""
Position Service.

Business logic for creating, querying, and managing job positions.
"""

import re
from uuid import UUID

from sqlalchemy import func, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.models.position import Position
from app.schemas.position import PositionCreate, PositionUpdate

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
