"""
Interview Model (面试).

Represents a scheduled or completed interview session.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TenantMixin, TimestampMixin


class Interview(Base, PrimaryKeyMixin, TimestampMixin, TenantMixin):
    """Interview session model."""

    __tablename__ = "interviews"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        comment="Interviewed candidate",
    )
    position_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Position being interviewed for",
    )

    round_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="Interview round (1, 2, 3...)"
    )
    interview_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="technical",
        comment="technical / behavioral / hr / final / phone_screen",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="scheduled",
        index=True,
        comment="scheduled / in_progress / completed / cancelled / no_show",
    )

    # Scheduling
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Scheduled start time"
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60, comment="Planned duration"
    )
    location: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="Physical location or meeting link")

    # Participants
    interviewer_ids: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=list, comment="List of interviewer user IDs"
    )

    # Result
    overall_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Overall interview score (0-10)"
    )
    recommendation: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="strong_yes / yes / no / strong_no"
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Interview summary")

    # AI-generated
    ai_questions: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=list, comment="AI-suggested interview questions"
    )

    # M5: Multi-round interview configuration (JSONB)
    interview_config: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Interview round configuration: [{round_number, interview_type, interviewer_role, duration_minutes, required}]",
    )

    # Metadata
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Actual completion time"
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Cancellation timestamp"
    )
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    candidate = relationship("Candidate", back_populates="interviews", lazy="selectin")
    position = relationship("Position", lazy="selectin")
    feedbacks = relationship(
        "InterviewFeedback", back_populates="interview", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Interview round={self.round_number} status={self.status}>"


class InterviewFeedback(Base, PrimaryKeyMixin, TimestampMixin):
    """Individual interviewer feedback for an interview."""

    __tablename__ = "interview_feedbacks"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    interviewer_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="Interviewer user ID")

    score: Mapped[float] = mapped_column(Float, nullable=False, comment="Score given (0-10)")
    recommendation: Mapped[str] = mapped_column(String(50), nullable=False, comment="strong_yes / yes / no / strong_no")
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Candidate strengths observed")
    weaknesses: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Areas of concern")
    comments: Mapped[str | None] = mapped_column(Text, nullable=True, comment="General comments")
    skill_ratings: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict, comment="Per-skill ratings"
    )

    # Relationships
    interview = relationship("Interview", back_populates="feedbacks")

    def __repr__(self) -> str:
        return f"<InterviewFeedback interviewer={self.interviewer_id} score={self.score}>"


class InterviewPanel(Base, PrimaryKeyMixin, TimestampMixin, TenantMixin):
    """Interview panel — groups multiple interviewers for a single interview session.

    Enables multi-interviewer coordination with role-based responsibilities.
    """

    __tablename__ = "interview_panels"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        comment="Associated interview session",
    )
    interviewer_id: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="Interviewer user ID"
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="panelist",
        comment="Role in panel: lead / panelist / observer",
    )
    focus_area: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="Focus area for this interviewer"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="invited",
        comment="invited / accepted / declined / completed",
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When interviewer responded to invitation"
    )

    # Relationships
    interview = relationship("Interview", lazy="selectin")

    def __repr__(self) -> str:
        return f"<InterviewPanel interview={self.interview_id} interviewer={self.interviewer_id} role={self.role}>"
