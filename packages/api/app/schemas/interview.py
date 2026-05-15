"""
Interview Pydantic Schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class InterviewCreate(BaseModel):
    """Schema for scheduling a new interview."""

    candidate_id: UUID = Field(...)
    position_id: UUID | None = None
    round_number: int = Field(1, ge=1)
    interview_type: str = Field("technical", description="technical / behavioral / hr / final / phone_screen")
    scheduled_at: datetime | None = Field(None, description="Scheduled start time")
    duration_minutes: int = Field(60, ge=15, le=480)
    location: str | None = Field(None, description="Physical location or meeting link")
    interviewer_ids: list[str] | None = Field(None, description="List of interviewer user IDs")


class InterviewUpdate(BaseModel):
    """Schema for updating interview details."""

    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    location: str | None = None
    interviewer_ids: list[str] | None = None
    status: str | None = None
    round_number: int | None = None
    interview_type: str | None = None


class InterviewFeedbackCreate(BaseModel):
    """Schema for submitting interview feedback."""

    score: float = Field(..., ge=0, le=10, description="Score (0-10)")
    recommendation: str = Field(..., description="strong_yes / yes / no / strong_no")
    strengths: str | None = None
    weaknesses: str | None = None
    comments: str | None = None
    skill_ratings: dict | None = None


class InterviewResponse(BaseModel):
    """Interview response schema."""

    id: UUID
    candidate_id: UUID
    position_id: UUID | None
    round_number: int
    interview_type: str
    status: str
    scheduled_at: datetime | None
    duration_minutes: int
    location: str | None
    interviewer_ids: list | None
    overall_score: float | None
    recommendation: str | None
    summary: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InterviewListResponse(BaseModel):
    """Paginated interview list."""

    items: list[InterviewResponse]
    total: int
    page: int
    page_size: int
    pages: int
