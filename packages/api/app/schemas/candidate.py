"""
Candidate Pydantic Schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CandidateCreate(BaseModel):
    """Schema for registering a new candidate."""

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr = Field(...)
    phone: str | None = Field(None, max_length=50)
    position_id: UUID | None = Field(None, description="Applied position")
    source: str | None = Field(None, description="referral / job_board / social / campus / other")
    source_detail: str | None = None
    current_company: str | None = None
    current_title: str | None = None
    years_of_experience: int | None = None
    education: str | None = None
    location: str | None = None
    expected_salary: int | None = None
    tags: list[str] | None = None


class CandidateUpdate(BaseModel):
    """Schema for updating candidate info."""

    name: str | None = Field(None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = None
    position_id: UUID | None = None
    stage: str | None = None
    status: str | None = None
    source: str | None = None
    current_company: str | None = None
    current_title: str | None = None
    years_of_experience: int | None = None
    education: str | None = None
    location: str | None = None
    expected_salary: int | None = None
    assigned_recruiter: str | None = None
    tags: list[str] | None = None


class CandidateResponse(BaseModel):
    """Candidate response schema."""

    id: UUID
    name: str
    email: str | None
    phone: str | None
    position_id: UUID | None
    stage: str
    status: str
    source: str | None
    current_company: str | None
    current_title: str | None
    years_of_experience: int | None
    education: str | None
    location: str | None
    expected_salary: int | None
    skills: dict | None
    summary: str | None
    applied_at: datetime | None
    assigned_recruiter: str | None
    tags: list | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CandidateListResponse(BaseModel):
    """Paginated candidate list."""

    items: list[CandidateResponse]
    total: int
    page: int
    page_size: int
    pages: int
