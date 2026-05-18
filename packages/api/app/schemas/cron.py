"""
Cron Pydantic Schemas — request/response models for cron job management.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CronJobCreate(BaseModel):
    """Schema for creating a new cron job."""

    name: str = Field(..., min_length=1, max_length=200, description="Job name")
    description: str | None = Field(None, description="Job description")
    task_type: str = Field(
        ...,
        description="daily_report / weekly_report / insight_scan / data_snapshot / custom",
    )
    schedule_config: dict = Field(
        ...,
        description="Schedule config: {cron_expr, interval_minutes, specific_time, timezone}",
    )
    is_active: bool = Field(True, description="Whether the job is active on creation")
    max_retries: int = Field(3, ge=0, le=10, description="Max retry attempts")
    timeout_seconds: int = Field(300, ge=10, le=3600, description="Timeout in seconds")


class CronJobUpdate(BaseModel):
    """Schema for updating a cron job."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    task_type: str | None = None
    schedule_config: dict | None = None
    max_retries: int | None = Field(None, ge=0, le=10)
    timeout_seconds: int | None = Field(None, ge=10, le=3600)


class CronJobResponse(BaseModel):
    """Cron job response schema."""

    id: UUID
    tenant_id: str
    name: str
    description: str | None
    task_type: str
    schedule_config: dict
    is_active: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    failure_count: int
    max_retries: int
    timeout_seconds: int
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CronJobListResponse(BaseModel):
    """Paginated cron job list."""

    items: list[CronJobResponse]
    total: int
    page: int
    page_size: int
    pages: int


class CronLogResponse(BaseModel):
    """Cron execution log response schema."""

    id: UUID
    tenant_id: str
    cron_job_id: UUID
    status: str
    started_at: datetime
    finished_at: datetime | None
    duration_seconds: float | None
    result: dict | None
    error_message: str | None
    retry_attempt: int

    model_config = {"from_attributes": True}


class CronLogListResponse(BaseModel):
    """Paginated cron log list."""

    items: list[CronLogResponse]
    total: int
