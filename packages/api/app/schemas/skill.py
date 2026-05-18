"""
Skill Pydantic Schemas — request/response models for skill management.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    """Schema for registering a new skill."""

    name: str = Field(..., min_length=1, max_length=200, description="Skill name")
    skill_type: str = Field(..., description="tool / prompt / workflow")
    description: str | None = Field(None, description="Skill description")
    prompt_template: str | None = Field(None, description="Prompt template with {{variable}} placeholders")
    input_schema: dict | None = Field(None, description="JSON Schema for input validation")
    output_schema: dict | None = Field(None, description="JSON Schema for output validation")
    is_active: bool = Field(True, description="Whether the skill is active on registration")
    tags: list[str] | None = Field(None, description="Tags for categorization")


class SkillUpdate(BaseModel):
    """Schema for updating a skill."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    prompt_template: str | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None
    is_active: bool | None = None
    tags: list[str] | None = None


class SkillResponse(BaseModel):
    """Skill response schema."""

    id: UUID
    tenant_id: str
    name: str
    skill_type: str
    description: str | None
    prompt_template: str | None
    input_schema: dict | None
    output_schema: dict | None
    is_active: bool
    call_count: int
    avg_latency_ms: float | None
    last_called_at: datetime | None
    tags: list | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SkillListResponse(BaseModel):
    """Paginated skill list."""

    items: list[SkillResponse]
    total: int
    page: int
    page_size: int
    pages: int


class SkillCallRequest(BaseModel):
    """Schema for invoking a skill."""

    input_data: dict = Field(..., description="Input data for the skill invocation")
    timeout_seconds: int | None = Field(None, ge=5, le=600, description="Optional timeout override")


class SkillCallResponse(BaseModel):
    """Skill invocation result."""

    skill_id: UUID
    skill_name: str
    skill_type: str
    status: str
    output: dict | None
    latency_ms: float
    error: str | None = None


class SkillStatsResponse(BaseModel):
    """Skill usage statistics."""

    skill_id: UUID
    skill_name: str
    skill_type: str
    call_count: int
    avg_latency_ms: float | None
    last_called_at: datetime | None
    created_at: datetime
