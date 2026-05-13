"""
Candidate Model (候选人).

Represents a person applying for a position in the recruitment system.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TenantMixin, TimestampMixin


class Candidate(Base, PrimaryKeyMixin, TimestampMixin, TenantMixin):
    """Candidate model."""

    __tablename__ = "candidates"

    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Full name")
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True, comment="Email address")
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Phone number")
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="Profile photo URL")

    position_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Applied position",
    )

    stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="applied",
        index=True,
        comment="Current pipeline stage: applied/screened/interviewed/offered/hired/rejected",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
        comment="active / inactive / blacklisted",
    )
    source: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="referral / job_board / social / campus / other"
    )
    source_detail: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Detailed source info")

    # Personal info (from resume parsing)
    current_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    years_of_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    education: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Highest education")
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expected_salary: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # AI-extracted data
    skills: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict, comment="Extracted skills")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="AI-generated candidate summary")

    # Metadata
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Application date"
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last activity timestamp"
    )
    assigned_recruiter: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="Assigned recruiter user ID"
    )
    tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list, comment="Free-form tags")

    # Relationships
    position = relationship("Position", back_populates="candidates", lazy="selectin")
    resumes = relationship("Resume", back_populates="candidate", lazy="selectin")
    interviews = relationship("Interview", back_populates="candidate", lazy="selectin")
    offers = relationship("Offer", back_populates="candidate", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Candidate {self.name} ({self.stage})>"
