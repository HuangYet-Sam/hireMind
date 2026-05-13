"""
Position Model (岗位).

Represents an open or closed job position in the recruitment pipeline.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TenantMixin, TimestampMixin


class Position(Base, PrimaryKeyMixin, TimestampMixin, TenantMixin):
    """Job position model."""

    __tablename__ = "positions"

    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="Position title")
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        comment="Owning department",
    )
    location: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Work location")
    employment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="full_time",
        comment="full_time / part_time / contract / internship",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
        index=True,
        comment="draft / open / closed / archived",
    )
    headcount: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="Number of openings")
    priority: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="normal",
        comment="low / normal / high / urgent",
    )
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Minimum salary (monthly)")
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Maximum salary (monthly)")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Job description")
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Job requirements")
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Benefits description")

    # Structured fields (JSON)
    required_skills: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict, comment="Required skills list"
    )
    preferred_skills: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict, comment="Preferred skills list"
    )
    education_requirement: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Minimum education level"
    )
    experience_years_min: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Minimum years of experience"
    )

    # Metadata
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When position was published"
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When position was closed"
    )
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="Creator user ID")
    is_remote: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="Remote-friendly")

    # Relationships
    department = relationship("Department", back_populates="positions", lazy="selectin")
    candidates = relationship("Candidate", back_populates="position", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Position {self.title} ({self.status})>"
