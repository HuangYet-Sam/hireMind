"""Matching Pydantic Schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MatchResultItem(BaseModel):
    """Single match result in a matching response."""

    candidate_id: UUID
    candidate_name: str | None = None
    overall_score: float
    skill_score: float | None = None
    experience_score: float | None = None
    education_score: float | None = None
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    explanation: str | None = None


class PositionMatchResult(BaseModel):
    """Response for position->candidates matching."""

    position_id: UUID
    position_title: str | None = None
    total_candidates: int
    matches: list[MatchResultItem]


class CandidateMatchResultItem(BaseModel):
    """Single position match for a candidate."""

    position_id: UUID
    position_title: str | None = None
    overall_score: float
    skill_score: float | None = None
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    explanation: str | None = None


class CandidateMatchResult(BaseModel):
    """Response for candidate->positions matching."""

    candidate_id: UUID
    total_positions: int
    matches: list[CandidateMatchResultItem]


class MatchDetailResponse(BaseModel):
    """Full match record response."""

    id: UUID
    position_id: UUID
    candidate_id: UUID
    status: str
    overall_score: float | None
    skill_score: float | None
    experience_score: float | None
    education_score: float | None
    score_breakdown: dict | None
    match_details: dict | None
    matched_at: datetime | None

    model_config = {"from_attributes": True}


class MatchListResponse(BaseModel):
    """Paginated match list."""

    items: list[MatchDetailResponse]
    total: int
    pages: int
