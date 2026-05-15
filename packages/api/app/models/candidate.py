"""
Candidate Model (候选人).

Multi-dimensional talent profile. Aligned to DDL §7.2.3.
Phase 1: stores plaintext in encrypted fields, uses real SHA256 for hashes.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin


class Candidate(Base, PrimaryKeyMixin, TimestampMixin):
    """Candidate — the organization's cumulative talent model."""

    __tablename__ = "candidates"

    # Phase 1: store plaintext; encrypt in Phase 2
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name_encrypted: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="AES-256 encrypted in Phase 2"
    )

    # Deduplication hashes (real SHA256)
    email_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="SHA256 of email for dedup"
    )
    phone_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="SHA256 of phone for dedup"
    )
    name_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="SHA256 of name for fuzzy match"
    )

    # Core profile (7 categories in JSONB)
    profile: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict,
        comment="7-category profile: basic_info, education, work_experience, skills, certifications, projects, preferences"
    )
    source_refs: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=list, comment="Source traceability index"
    )

    # Credibility scoring
    credibility_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=0,
        comment="0-100 credibility score"
    )
    credibility_grade: Mapped[str | None] = mapped_column(
        String(1), nullable=True,
        comment="A(>=80) / B(>=60) / C(>=40) / D(<40)"
    )

    # AI inference
    inference_data: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict, comment="AI inference results"
    )
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Status and metadata
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active",
        comment="active / inactive / blacklisted / onboarded"
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, default="default"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="Optimistic lock version"
    )

    # Legacy fields kept for backward compatibility
    position_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="SET NULL"),
        nullable=True,
    )
    stage: Mapped[str] = mapped_column(
        String(50), nullable=False, default="applied",
        comment="Pipeline stage: applied/screened/interviewed/offered/hired/rejected"
    )
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_recruiter: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Relationships
    position = relationship("Position", back_populates="candidates", lazy="selectin")
    resumes = relationship("Resume", back_populates="candidate", lazy="selectin")
    interviews = relationship("Interview", back_populates="candidate", lazy="selectin")
    offers = relationship("Offer", back_populates="candidate", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("phone_hash", "email_hash", name="uq_candidate_identity"),
    )

    @property
    def name(self) -> str | None:
        return self.name_encrypted

    @property
    def skills(self) -> dict | None:
        profile = self.profile or {}
        return {"skills": profile.get("skills", [])}

    @property
    def current_company(self) -> str | None:
        return (self.profile or {}).get("basic_info", {}).get("current_company")

    @property
    def current_title(self) -> str | None:
        return (self.profile or {}).get("basic_info", {}).get("current_title")

    @property
    def years_of_experience(self) -> int | None:
        return (self.profile or {}).get("basic_info", {}).get("years_of_experience")

    @property
    def education(self) -> str | None:
        return (self.profile or {}).get("basic_info", {}).get("education")

    @property
    def location(self) -> str | None:
        return (self.profile or {}).get("basic_info", {}).get("location")

    @property
    def expected_salary(self) -> int | None:
        return (self.profile or {}).get("preferences", {}).get("expected_salary")

    def __repr__(self) -> str:
        return f"<Candidate ({self.stage})>"
