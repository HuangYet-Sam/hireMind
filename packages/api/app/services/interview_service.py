from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.models.interview import Interview, InterviewFeedback, InterviewPanel
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

    # ------------------------------------------------------------------
    # M5: Extended methods — workload, batch, calendar, round advance
    # ------------------------------------------------------------------

    async def get_workload_stats(
        self,
        *,
        tenant_id: str,
    ) -> list[dict]:
        """Calculate per-interviewer workload statistics.

        Aggregates total interviews, pending/completed feedback counts,
        average score, and upcoming interview count for each interviewer
        within the tenant.

        Args:
            tenant_id: Tenant scope identifier.

        Returns:
            List of dicts with keys: interviewer_id, interviewer_name,
            total_interviews, pending_feedback, completed_feedback,
            average_score, upcoming_interviews.
        """
        # Gather all interviews with their feedbacks for this tenant
        stmt = (
            select(Interview)
            .where(Interview.tenant_id == tenant_id)
            .options(selectinload(Interview.feedbacks))
        )
        result = await self.db.execute(stmt)
        interviews = list(result.scalars().all())

        # Build per-interviewer stats
        from collections import defaultdict

        stats: dict[str, dict] = defaultdict(lambda: {
            "interviewer_id": "",
            "interviewer_name": "",
            "total_interviews": 0,
            "pending_feedback": 0,
            "completed_feedback": 0,
            "scores": [],
            "upcoming_interviews": 0,
        })

        now = datetime.now(timezone.utc)

        for iv in interviews:
            interviewer_ids = iv.interviewer_ids or []
            feedback_interviewer_ids = {f.interviewer_id for f in iv.feedbacks}

            for iid in interviewer_ids:
                entry = stats[iid]
                entry["interviewer_id"] = iid
                entry["interviewer_name"] = iid  # Placeholder; real name from user service
                entry["total_interviews"] += 1

                if iid in feedback_interviewer_ids:
                    entry["completed_feedback"] += 1
                    fb = next(f for f in iv.feedbacks if f.interviewer_id == iid)
                    entry["scores"].append(fb.score)
                else:
                    entry["pending_feedback"] += 1

                if iv.scheduled_at and iv.scheduled_at > now and iv.status in ("scheduled", "in_progress"):
                    entry["upcoming_interviews"] += 1

        # Compute average scores
        result_list = []
        for entry in stats.values():
            scores = entry.pop("scores")
            entry["average_score"] = round(sum(scores) / len(scores), 2) if scores else None
            result_list.append(entry)

        return result_list

    async def batch_create(
        self,
        *,
        items: list[InterviewCreate],
        tenant_id: str,
        user_id: str,
    ) -> list[Interview]:
        """Create multiple interviews in a single transaction.

        Validates all candidates exist before creating any interview.
        If any candidate is missing, the entire batch is rejected.

        Args:
            items: List of InterviewCreate schemas.
            tenant_id: Tenant scope identifier.
            user_id: User creating the interviews.

        Returns:
            List of created Interview objects.

        Raises:
            ValueError: If any candidate_id is not found.
        """
        # Pre-validate all candidates
        candidate_ids = {item.candidate_id for item in items}
        for cid in candidate_ids:
            stmt = select(Candidate).where(
                Candidate.id == cid,
                Candidate.tenant_id == tenant_id,
            )
            candidate = (await self.db.execute(stmt)).scalar_one_or_none()
            if candidate is None:
                raise ValueError(f"Candidate {cid} not found")

        created: list[Interview] = []
        for item in items:
            interview = Interview(
                candidate_id=item.candidate_id,
                position_id=item.position_id,
                round_number=item.round_number,
                interview_type=item.interview_type,
                status="scheduled",
                scheduled_at=item.scheduled_at,
                duration_minutes=item.duration_minutes,
                location=item.location,
                interviewer_ids=item.interviewer_ids or [],
                tenant_id=tenant_id,
                created_by=user_id,
            )
            self.db.add(interview)
            created.append(interview)

        await self.db.flush()
        for iv in created:
            await self.db.refresh(iv)

        return created

    async def get_calendar_events(
        self,
        *,
        tenant_id: str,
        date_from: datetime,
        date_to: datetime,
    ) -> list[Interview]:
        """Query interviews within a date range for calendar display.

        Args:
            tenant_id: Tenant scope identifier.
            date_from: Start of date range (inclusive).
            date_to: End of date range (inclusive).

        Returns:
            List of Interview objects whose scheduled_at falls within the range.
        """
        stmt = (
            select(Interview)
            .where(
                Interview.tenant_id == tenant_id,
                Interview.scheduled_at >= date_from,
                Interview.scheduled_at <= date_to,
            )
            .options(selectinload(Interview.candidate))
            .options(selectinload(Interview.position))
            .order_by(Interview.scheduled_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def advance_round(
        self,
        *,
        interview_id: UUID,
        tenant_id: str,
        user_id: str,
        next_interview_type: str | None = None,
        next_scheduled_at: datetime | None = None,
        next_interviewer_ids: list[str] | None = None,
    ) -> Interview:
        """Advance a completed interview to the next round.

        Marks the current interview as completed (if not already),
        then creates a new interview for the next round with round_number + 1.
        The interview_config from the current interview is consulted to
        determine the next round's type and duration.

        Args:
            interview_id: Current interview UUID.
            tenant_id: Tenant scope identifier.
            user_id: User advancing the round.
            next_interview_type: Override for next round type (optional).
            next_scheduled_at: Scheduled time for next round (optional).
            next_interviewer_ids: Interviewers for next round (optional).

        Returns:
            The newly created next-round Interview.

        Raises:
            ValueError: If current interview not found or not in a completable state.
        """
        current = await self.get_by_id(interview_id, tenant_id)
        if current is None:
            raise ValueError("Interview not found")

        # Complete current interview if still in_progress
        if current.status == "in_progress":
            current.status = "completed"
            current.completed_at = datetime.now(timezone.utc)
        elif current.status != "completed":
            raise ValueError(
                f"Cannot advance round from '{current.status}' status. "
                "Interview must be completed or in_progress."
            )

        # Determine next round config
        config = current.interview_config or []
        next_round = current.round_number + 1

        # Find config for next round
        round_config = None
        for rc in config:
            if rc.get("round_number") == next_round:
                round_config = rc
                break

        interview_type = next_interview_type or (
            round_config.get("interview_type", "technical") if round_config else "technical"
        )
        duration = (
            round_config.get("duration_minutes", 60) if round_config else 60
        )

        # Create next round interview
        next_interview = Interview(
            candidate_id=current.candidate_id,
            position_id=current.position_id,
            round_number=next_round,
            interview_type=interview_type,
            status="scheduled",
            scheduled_at=next_scheduled_at,
            duration_minutes=duration,
            location=None,
            interviewer_ids=next_interviewer_ids or [],
            tenant_id=tenant_id,
            created_by=user_id,
            interview_config=config,  # Carry forward the config
        )
        self.db.add(next_interview)
        await self.db.flush()
        await self.db.refresh(next_interview)

        return next_interview
