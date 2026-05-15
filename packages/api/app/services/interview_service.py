from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.interview import Interview, InterviewFeedback
from app.schemas.interview import InterviewCreate, InterviewFeedbackCreate, InterviewUpdate

VALID_TRANSITIONS = {
    "scheduled": {"in_progress", "cancelled", "no_show"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
    "no_show": set(),
}


class InterviewService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_interviews(
        self,
        *,
        tenant_id: str,
        candidate_id: UUID | None = None,
        position_id: UUID | None = None,
        interviewer_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Interview], int]:
        filters = [Interview.tenant_id == tenant_id]
        if candidate_id is not None:
            filters.append(Interview.candidate_id == candidate_id)
        if position_id is not None:
            filters.append(Interview.position_id == position_id)
        if date_from is not None:
            filters.append(Interview.scheduled_at >= date_from)
        if date_to is not None:
            filters.append(Interview.scheduled_at <= date_to)
        if interviewer_id is not None:
            filters.append(Interview.interviewer_ids.contains([str(interviewer_id)]))

        count_stmt = select(func.count()).select_from(Interview).where(*filters)
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = (
            select(Interview)
            .where(*filters)
            .order_by(Interview.scheduled_at.desc().nulls_last(), Interview.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def get_by_id(self, interview_id: UUID, tenant_id: str) -> Interview | None:
        stmt = select(Interview).where(
            Interview.id == interview_id,
            Interview.tenant_id == tenant_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        data: InterviewCreate,
        tenant_id: str,
        user_id: str,
    ) -> Interview:
        candidate_stmt = select(Candidate).where(
            Candidate.id == data.candidate_id,
            Candidate.tenant_id == tenant_id,
        )
        candidate = (await self.db.execute(candidate_stmt)).scalar_one_or_none()
        if candidate is None:
            raise ValueError("Candidate not found")

        interview = Interview(
            candidate_id=data.candidate_id,
            position_id=data.position_id,
            round_number=data.round_number,
            interview_type=data.interview_type,
            status="scheduled",
            scheduled_at=data.scheduled_at,
            duration_minutes=data.duration_minutes,
            location=data.location,
            interviewer_ids=data.interviewer_ids or [],
            tenant_id=tenant_id,
            created_by=user_id,
        )
        self.db.add(interview)
        await self.db.flush()
        await self.db.refresh(interview)
        return interview

    async def update(
        self,
        interview_id: UUID,
        data: InterviewUpdate,
        tenant_id: str,
    ) -> Interview:
        interview = await self.get_by_id(interview_id, tenant_id)
        if interview is None:
            raise ValueError("Interview not found")

        update_data = data.model_dump(exclude_unset=True)

        if "status" in update_data:
            new_status = update_data["status"]
            allowed = VALID_TRANSITIONS.get(interview.status, set())
            if new_status not in allowed:
                raise ValueError(
                    f"Cannot transition from '{interview.status}' to '{new_status}'"
                )

        allowed_fields = {
            "scheduled_at", "duration_minutes", "location",
            "interviewer_ids", "status", "round_number", "interview_type",
        }
        for key, value in update_data.items():
            if key in allowed_fields:
                setattr(interview, key, value)

        if update_data.get("status") == "completed":
            interview.completed_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(interview)
        return interview

    async def cancel(
        self,
        interview_id: UUID,
        tenant_id: str,
        reason: str | None = None,
    ) -> Interview:
        interview = await self.get_by_id(interview_id, tenant_id)
        if interview is None:
            raise ValueError("Interview not found")

        allowed = VALID_TRANSITIONS.get(interview.status, set())
        if "cancelled" not in allowed:
            raise ValueError(
                f"Cannot cancel interview in '{interview.status}' status"
            )

        interview.status = "cancelled"
        interview.cancelled_at = datetime.now(timezone.utc)
        interview.cancel_reason = reason
        await self.db.flush()
        await self.db.refresh(interview)
        return interview

    async def submit_feedback(
        self,
        interview_id: UUID,
        interviewer_id: str,
        data: InterviewFeedbackCreate,
        tenant_id: str,
    ) -> Interview:
        interview = await self.get_by_id(interview_id, tenant_id)
        if interview is None:
            raise ValueError("Interview not found")

        if interview.status not in ("in_progress", "completed"):
            raise ValueError(
                f"Cannot submit feedback for interview in '{interview.status}' status"
            )

        feedback = InterviewFeedback(
            interview_id=interview_id,
            interviewer_id=interviewer_id,
            score=data.score,
            recommendation=data.recommendation,
            strengths=data.strengths,
            weaknesses=data.weaknesses,
            comments=data.comments,
            skill_ratings=data.skill_ratings,
        )
        self.db.add(feedback)
        await self.db.flush()

        avg_stmt = select(func.avg(InterviewFeedback.score)).where(
            InterviewFeedback.interview_id == interview_id,
        )
        avg_score = (await self.db.execute(avg_stmt)).scalar_one_or_none()
        interview.overall_score = round(avg_score, 2) if avg_score is not None else None

        if interview.status == "in_progress":
            interview.status = "completed"
            interview.completed_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(interview)
        return interview
