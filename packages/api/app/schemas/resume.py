"""
Resume Pydantic Schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ResumeResponse(BaseModel):
    """Resume response schema."""

    id: UUID
    candidate_id: UUID | None
    original_filename: str
    file_size: int
    content_type: str
    parse_status: str
    parsed_data: dict | None
    language: str | None
    page_count: int | None
    uploaded_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeParseResult(BaseModel):
    """AI parse result schema."""

    resume_id: UUID
    parse_status: str
    parsed_data: dict | None = Field(None, description="Structured resume data")
    skills: list[str] | None = None
    education: list[dict] | None = None
    work_experience: list[dict] | None = None
    error: str | None = None


class ResumeListResponse(BaseModel):
    """Paginated resume list."""

    items: list[ResumeResponse]
    total: int
    page: int
    page_size: int
