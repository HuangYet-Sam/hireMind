"""
Offer Model (Offer).

Represents a job offer extended to a candidate, including approval workflow.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TenantMixin, TimestampMixin


class Offer(Base, PrimaryKeyMixin, TimestampMixin, TenantMixin):
    """Job offer model with approval workflow."""

    __tablename__ = "offers"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        comment="Candidate receiving the offer",
    )
    position_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Position for the offer",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
        index=True,
        comment="draft / pending_approval / approved / sent / accepted / rejected / withdrawn",
    )

    # Compensation
    base_salary: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Base monthly salary")
    annual_bonus_months: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Annual bonus in months"
    )
    sign_on_bonus: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="One-time sign-on bonus")
    equity: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Equity / stock options description")
    benefits_summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Benefits package summary")

    # Employment details
    proposed_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Proposed start date"
    )
    probation_months: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=3, comment="Probation period in months"
    )
    work_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="full_time / contract / etc.")

    # Additional
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Internal notes")
    offer_letter_url: Mapped[str | None] = mapped_column(
        String(1024), nullable=True, comment="Generated offer letter file URL"
    )

    # Response tracking
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Candidate's response note")
    expiry_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Offer expiration date"
    )

    # Metadata
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    candidate = relationship("Candidate", back_populates="offers", lazy="selectin")
    position = relationship("Position", lazy="selectin")
    approvals = relationship(
        "OfferApproval", back_populates="offer", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Offer {self.status} candidate={self.candidate_id}>"


class OfferApproval(Base, PrimaryKeyMixin, TimestampMixin):
    """Individual approval record in the offer approval chain."""

    __tablename__ = "offer_approvals"

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offers.id", ondelete="CASCADE"),
        nullable=False,
    )
    approver_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="Approver user ID")
    approver_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", comment="pending / approved / rejected"
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="Order in approval chain")

    # Relationships
    offer = relationship("Offer", back_populates="approvals")

    def __repr__(self) -> str:
        return f"<OfferApproval {self.status} by={self.approver_id}>"
