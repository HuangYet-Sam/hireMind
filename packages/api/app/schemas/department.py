"""
Department Pydantic Schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    """Schema for creating a department."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str | None = Field(None, max_length=50, description="Department code (e.g. ENG, HR)")
    parent_id: UUID | None = Field(None, description="Parent department ID")
    description: str | None = None
    head_user_id: str | None = Field(None, description="Department head user ID")
    headcount_limit: int | None = None
    sort_order: int = 0


class DepartmentUpdate(BaseModel):
    """Schema for updating a department."""

    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = None
    parent_id: UUID | None = None
    description: str | None = None
    head_user_id: str | None = None
    headcount_limit: int | None = None
    status: str | None = None
    sort_order: int | None = None


class DepartmentResponse(BaseModel):
    """Department response schema."""

    id: UUID
    name: str
    code: str | None
    parent_id: UUID | None
    description: str | None
    head_user_id: str | None
    headcount_limit: int | None
    current_headcount: int
    status: str
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DepartmentListResponse(BaseModel):
    """Department list response (flat)."""

    items: list[DepartmentResponse]
    total: int
