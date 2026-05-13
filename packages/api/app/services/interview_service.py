"""
Interview Service.

Business logic for scheduling, managing, and recording interview feedback.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.interview import InterviewCreate, InterviewUpdate


class InterviewService:
    """Handles interview lifecycle management."""

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
    ) -> tuple[list, int]:
        """Return paginated interviews with optional filters."""
        # TODO: implement
        return [], 0

    async def get_by_id(self, interview_id: UUID, tenant_id: str) -> dict | None:
        """Fetch a single interview."""
        return None

    async def create(self, data: InterviewCreate, tenant_id: str, user_id: str) -> dict:
        """
        Schedule a new interview.

        - Validates time slot availability.
        - Sends calendar invitations (TODO).
        - Creates DB record.
        """
        raise NotImplementedError

    async def update(self, interview_id: UUID, data: InterviewUpdate, tenant_id: str) -> dict:
        """Update interview details (reschedule, change interviewer, etc.)."""
        raise NotImplementedError

    async def cancel(self, interview_id: UUID, tenant_id: str) -> None:
        """Cancel an interview and notify participants."""
        raise NotImplementedError

    async def submit_feedback(
        self,
        interview_id: UUID,
        feedback: str,
        score: float,
        recommendation: str,
        tenant_id: str,
        user_id: str,
    ) -> dict:
        """
        Record interviewer feedback after an interview.

        Args:
            feedback: Free-text feedback.
            score: Numeric score (0-10).
            recommendation: One of 'strong_yes', 'yes', 'no', 'strong_no'.
            tenant_id: Tenant context.
            user_id: Interviewer submitting feedback.
        """
        raise NotImplementedError
