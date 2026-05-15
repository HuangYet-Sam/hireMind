"""
Candidate Service.

Business logic for managing candidates throughout the hiring pipeline.
"""

import hashlib
import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.schemas.candidate import CandidateCreate, CandidateUpdate

VALID_STAGES = ["applied", "screened", "interviewed", "offered", "hired", "rejected"]

STAGE_TRANSITIONS = {
    "applied": ["screened", "rejected"],
    "screened": ["interviewed", "rejected"],
    "interviewed": ["offered", "rejected"],
    "offered": ["hired", "rejected"],
    "hired": [],
    "rejected": [],
}


class CandidateService:

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.strip().encode()).hexdigest()

    async def list_candidates(
        self,
        *,
        tenant_id: str,
        position_id: UUID | None = None,
        status: str | None = None,
        stage: str | None = None,
        keyword: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Candidate], int]:
        base = select(Candidate).where(Candidate.tenant_id == tenant_id)
        count_base = select(func.count()).select_from(Candidate).where(
            Candidate.tenant_id == tenant_id
        )

        if position_id is not None:
            base = base.where(Candidate.position_id == position_id)
            count_base = count_base.where(Candidate.position_id == position_id)

        if status is not None:
            base = base.where(Candidate.status == status)
            count_base = count_base.where(Candidate.status == status)

        if stage is not None:
            base = base.where(Candidate.stage == stage)
            count_base = count_base.where(Candidate.stage == stage)

        if keyword is not None and keyword.strip():
            escaped = re.sub(r'([\\%_])', r'\\\1', keyword.strip())
            pattern = f"%{escaped}%"
            base = base.where(Candidate.summary.ilike(pattern))
            count_base = count_base.where(Candidate.summary.ilike(pattern))

        total = (await self.db.execute(count_base)).scalar_one()

        stmt = base.order_by(Candidate.created_at.desc()).offset(offset).limit(limit)
        rows = (await self.db.execute(stmt)).scalars().all()

        return list(rows), total

    async def get_by_id(self, candidate_id: UUID, tenant_id: str) -> Candidate | None:
        stmt = select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create(
        self, data: CandidateCreate, tenant_id: str, user_id: str
    ) -> Candidate:
        email_hash = self._hash(data.email.lower().strip())

        if data.phone:
            phone_hash = self._hash(data.phone)
        else:
            phone_hash = self._hash("no_phone:" + data.email.lower().strip())

        dup_stmt = select(Candidate).where(
            Candidate.email_hash == email_hash,
            Candidate.phone_hash == phone_hash,
            Candidate.tenant_id == tenant_id,
        )
        existing = (await self.db.execute(dup_stmt)).scalar_one_or_none()
        if existing is not None:
            raise ValueError("Candidate with this email and phone already exists")

        name_hash = self._hash(data.name)

        profile = {
            "basic_info": {
                "name": data.name,
                "email": data.email,
                "phone": data.phone,
                "location": data.location,
            },
            "skills": data.tags or [],
            "preferences": {"expected_salary": data.expected_salary},
        }

        candidate = Candidate(
            email=data.email,
            phone=data.phone,
            name_encrypted=data.name,
            email_hash=email_hash,
            phone_hash=phone_hash,
            name_hash=name_hash,
            position_id=data.position_id,
            source=data.source,
            source_detail=data.source_detail,
            stage="applied",
            status="active",
            credibility_score=0,
            credibility_grade="D",
            tags=data.tags or [],
            applied_at=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            assigned_recruiter=user_id,
            profile=profile,
            summary=None,
        )

        self.db.add(candidate)
        await self.db.flush()
        await self.db.refresh(candidate)
        return candidate

    async def update(
        self, candidate_id: UUID, data: CandidateUpdate, tenant_id: str
    ) -> Candidate:
        candidate = await self.get_by_id(candidate_id, tenant_id)
        if candidate is None:
            return None

        update_data = data.model_dump(exclude_unset=True)

        if "email" in update_data and update_data["email"] is not None:
            candidate.email = update_data["email"]
            candidate.email_hash = self._hash(update_data["email"].lower().strip())

        if "phone" in update_data:
            candidate.phone = update_data["phone"]
            if update_data["phone"] is not None:
                candidate.phone_hash = self._hash(update_data["phone"])
            else:
                candidate.phone_hash = self._hash(
                    "no_phone:" + (candidate.email or "").lower().strip()
                )

        if "name" in update_data and update_data["name"] is not None:
            candidate.name_encrypted = update_data["name"]
            candidate.name_hash = self._hash(update_data["name"])

        simple_fields = [
            "position_id",
            "stage",
            "status",
            "source",
            "assigned_recruiter",
            "tags",
        ]
        for field in simple_fields:
            if field in update_data:
                setattr(candidate, field, update_data[field])

        candidate.version += 1
        await self.db.flush()
        await self.db.refresh(candidate)
        return candidate

    async def soft_delete(self, candidate_id: UUID, tenant_id: str) -> None:
        candidate = await self.get_by_id(candidate_id, tenant_id)
        if candidate is None:
            raise ValueError("Candidate not found")
        candidate.status = "inactive"
        await self.db.flush()

    async def advance_stage(
        self, candidate_id: UUID, new_stage: str, tenant_id: str
    ) -> Candidate:
        if new_stage not in VALID_STAGES:
            raise ValueError(f"Invalid stage: {new_stage}")

        candidate = await self.get_by_id(candidate_id, tenant_id)
        if candidate is None:
            return None

        current_stage = candidate.stage
        allowed = STAGE_TRANSITIONS.get(current_stage, [])
        if new_stage not in allowed:
            raise ValueError(
                f"Cannot transition from '{current_stage}' to '{new_stage}'"
            )

        candidate.stage = new_stage
        candidate.version += 1
        await self.db.flush()
        await self.db.refresh(candidate)
        return candidate
