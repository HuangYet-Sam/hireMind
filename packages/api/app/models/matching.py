"""
Matching Models (匹配).

Match records and feedback. Aligned to DDL §7.2.5 and §7.7a.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin


class Match(Base, PrimaryKeyMixin):
    """Position vs Candidate matching record."""

    __tablename__ = "matches"

    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, default="default"
    )
    position_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("positions.id"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True,
        comment="pending/screening/shortlisted/interview_scheduled/interviewed/offered/hired/rejected/withdrawn"
    )

    # Score dimensions
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    skill_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    experience_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    education_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    inference_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_score: Mapped[object | None] = mapped_column(
        Float, nullable=True, comment="Salary match score"
    )

    score_breakdown: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict, comment="Detailed score breakdown"
    )
    match_details: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict,
        comment="Match analysis: strengths/gaps/suggestions"
    )
    candidate_feedback: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict, comment="Candidate feedback"
    )

    initiated_by: Mapped[str] = mapped_column(
        String(20), nullable=False, default="system",
        comment="system/candidate/hr"
    )
    vector_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)

    matched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    position = relationship("Position", lazy="selectin")
    candidate = relationship("Candidate", lazy="selectin")
    feedback_entries = relationship(
        "MatchFeedback", back_populates="match", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("position_id", "candidate_id", name="uq_match"),
    )  # tenant_id scoped via position/candidate FK

    def __repr__(self) -> str:
        return f"<Match {self.position_id} x {self.candidate_id} ({self.status})>"


class MatchFeedback(Base, PrimaryKeyMixin):
    """Feedback on match quality from users."""

    __tablename__ = "match_feedback"

    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    feedback_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="positive/negative/neutral"
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_accuracy_score: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, comment="1-5 accuracy rating"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    match = relationship("Match", back_populates="feedback_entries")
    user = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<MatchFeedback {self.feedback_type}>"
