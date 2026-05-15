"""
Resume Model (简历).

Resume file metadata and AI-parsed data. Aligned to DDL §7.2.2.
"""

import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin


class Resume(Base, PrimaryKeyMixin, TimestampMixin):
    """Resume model — links to a file and AI-parsed structured data."""

    __tablename__ = "resumes"

    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=True,
    )
    position_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("positions.id"),
        nullable=True,
        comment="Applied position"
    )

    # File info
    original_filename: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Original file name"
    )
    file_path: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="File storage path"
    )
    file_type: Mapped[str | None] = mapped_column(
        String(10), nullable=True,
        comment="pdf/docx/doc/png/jpg/jpeg"
    )
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, comment="Bytes")
    content_type: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="MIME type"
    )
    file_hash: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="SHA-256 for dedup"
    )

    # Source and upload
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="upload",
        comment="upload/email/boss/referral/headhunter"
    )
    uploaded_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Parsing
    parse_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="pending/processing/completed/failed"
    )
    parsed_at: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Timestamp when parsing completed"
    )
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_data: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict,
        comment="AI-extracted structured data (immutable audit trail)"
    )

    # Traceability and credibility
    source_refs: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=list, comment="Field source annotations"
    )
    credibility: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Credibility check results"
    )

    # AI metadata
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True, default="zh")
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="Optimistic lock version"
    )
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=True, default="default")

    # Relationships
    candidate = relationship("Candidate", back_populates="resumes", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Resume {self.original_filename} ({self.parse_status})>"
