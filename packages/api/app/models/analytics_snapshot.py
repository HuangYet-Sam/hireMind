"""
AnalyticsSnapshot Model — stores daily/weekly data snapshots for trend analysis.

Each snapshot captures a JSON blob of all core metrics at a point in time,
enabling historical comparison and retroactive reporting.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AnalyticsSnapshot(Base):
    """Persists periodic metric snapshots for analytics."""

    __tablename__ = "analytics_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
    )
    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
    )
    snapshot_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="daily",
        comment="daily or weekly",
    )
    metrics: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
        comment="JSON snapshot of all core metrics",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
