"""
AiTask Pydantic Schemas.

Request / response models for AI Task CRUD endpoints.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.ai_task import TaskStatus, TaskType


class AiTaskCreate(BaseModel):
    """Schema for creating an AI task."""

    task_type: TaskType
    input_data: str | None = Field(None, description="JSON-encoded input payload")


class AiTaskResponse(BaseModel):
    """AI Task response schema."""

    id: UUID
    tenant_id: str
    task_type: TaskType
    status: TaskStatus
    input_data: str | None
    output_data: str | None
    error_message: str | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedAiTaskResponse(BaseModel):
    """Paginated list of AI tasks."""

    items: list[AiTaskResponse]
    total: int
    page: int
    page_size: int
    pages: int
