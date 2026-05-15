"""
Position Model (岗位).

Structured capability requirement model with full lifecycle.
Aligned to DDL §7.2.1.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin


DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000000"


class Position(Base, PrimaryKeyMixin, TimestampMixin):
    """Job position model."""

    __tablename__ = "positions"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        index=True,
        comment="draft / open / paused / closed / filled",
    )
    required_skills: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=list
    )
    required_exp_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    required_exp_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_min: Mapped[object | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[object | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="CNY"
    )
    profile_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_keywords: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=list
    )
    jd_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    headcount: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    filled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    priority: Mapped[str] = mapped_column(
        String(10), nullable=False, default="normal"
    )
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        default=DEFAULT_TENANT_ID,
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="Optimistic lock version"
    )

    # Extra fields not in DDL but kept for frontend compatibility
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="full_time"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_skills: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    education_requirement: Mapped[str | None] = mapped_column(String(100), nullable=True)
    experience_years_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    department = relationship("Department", back_populates="positions", lazy="selectin")
    candidates = relationship("Candidate", back_populates="position", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Position {self.title} ({self.status})>"
