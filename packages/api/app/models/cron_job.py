"""
CronJob Model — scheduled task management.

Represents a recurring or one-shot scheduled task such as daily reports,
weekly summaries, insight scans, and data snapshots.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TenantMixin, TimestampMixin


class CronJob(Base, PrimaryKeyMixin, TimestampMixin, TenantMixin):
    """Scheduled cron task for automated recruitment operations."""

    __tablename__ = "cron_jobs"

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Human-readable job name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Job description",
    )
    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="daily_report / weekly_report / insight_scan / data_snapshot / custom",
    )
    schedule_config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Schedule config: {cron_expr, interval_minutes, specific_time, timezone}",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether the job is currently active",
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful execution time",
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Calculated next execution time",
    )
    failure_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Consecutive failure count (resets on success)",
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        comment="Maximum retry attempts before disabling",
    )
    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=300,
        comment="Execution timeout in seconds",
    )
    created_by: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="User ID who created the job",
    )

    # Relationships
    logs = relationship(
        "CronLog", back_populates="job", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CronJob {self.name} type={self.task_type} active={self.is_active}>"
