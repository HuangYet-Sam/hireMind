"""
Position Pydantic Schemas.

Request / response models for the Position endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Create ────────────────────────────────────────────────────
class PositionCreate(BaseModel):
    """Schema for creating a new position."""

    title: str = Field(..., min_length=1, max_length=255, description="Position title")
    department_id: UUID | None = Field(None, description="Department ID")
    location: str | None = Field(None, max_length=255, description="Work location")
    employment_type: str = Field("full_time", description="full_time / part_time / contract / internship")
    headcount: int = Field(1, ge=1, description="Number of openings")
    priority: str = Field("normal", description="low / normal / high / urgent")
    salary_min: float | None = Field(None, description="Minimum monthly salary")
    salary_max: float | None = Field(None, description="Maximum monthly salary")
    description: str | None = Field(None, description="Job description")
    requirements: str | None = Field(None, description="Job requirements")
    benefits: str | None = Field(None, description="Benefits")
    required_skills: list[dict] | None = Field(None, description="Required skills")
    preferred_skills: list[str] | None = Field(None, description="Preferred skills")
    education_requirement: str | None = Field(None, description="Minimum education")
    experience_years_min: int | None = Field(None, description="Min years of experience")
    is_remote: bool = Field(False, description="Remote-friendly")


# ── Update ────────────────────────────────────────────────────
class PositionUpdate(BaseModel):
    """Schema for updating a position. All fields optional."""

    title: str | None = Field(None, min_length=1, max_length=255)
    department_id: UUID | None = None
    location: str | None = None
    employment_type: str | None = None
    headcount: int | None = Field(None, ge=1)
    priority: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    description: str | None = None
    requirements: str | None = None
    benefits: str | None = None
    required_skills: list[dict] | None = None
    preferred_skills: list[str] | None = None
    education_requirement: str | None = None
    experience_years_min: int | None = None
    is_remote: bool | None = None
    status: str | None = Field(None, description="draft / open / closed / archived")


# ── Response ──────────────────────────────────────────────────
class PositionResponse(BaseModel):
    """Position response schema."""

    id: UUID
    title: str
    department_id: UUID | None
    location: str | None
    employment_type: str
    status: str
    headcount: int
    priority: str
    salary_min: float | None
    salary_max: float | None
    description: str | None
    requirements: str | None
    benefits: str | None
    required_skills: list[dict] | None
    preferred_skills: list | None
    education_requirement: str | None
    experience_years_min: int | None
    is_remote: bool
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── List Response ─────────────────────────────────────────────
class PositionListResponse(BaseModel):
    """Paginated list of positions."""

    items: list[PositionResponse]
    total: int
    page: int
    page_size: int
    pages: int
