"""
CronLog Model — execution history for CronJob tasks.

Each record tracks one execution attempt including timing, status,
result summary, and error information.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TenantMixin


class CronLog(Base, PrimaryKeyMixin, TenantMixin):
    """Execution log for a scheduled cron task."""

    __tablename__ = "cron_logs"

    cron_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cron_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated cron job",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="running",
        index=True,
        comment="running / success / failed / timeout",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Execution start time",
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Execution finish time",
    )
    duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Execution duration in seconds",
    )
    result: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Execution result summary",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if execution failed",
    )
    retry_attempt: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Retry attempt number (0 = first attempt)",
    )

    # Relationships
    job = relationship("CronJob", back_populates="logs")

    def __repr__(self) -> str:
        return f"<CronLog job={self.cron_job_id} status={self.status}>"
