"""
Resume Model (简历).

Stores resume metadata and links to the actual file in MinIO.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TenantMixin, TimestampMixin


class Resume(Base, PrimaryKeyMixin, TimestampMixin, TenantMixin):
    """Resume model — links to a file stored in MinIO."""

    __tablename__ = "resumes"

    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=True,
        comment="Linked candidate",
    )

    # File info
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False, comment="Original file name")
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False, comment="MinIO object key")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, comment="File size in bytes")
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, comment="MIME type")
    file_hash: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="SHA-256 hash for deduplication"
    )

    # Parsing status
    parse_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        comment="pending / parsing / completed / failed",
    )
    parsed_at: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Timestamp when parsing completed"
    )
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Error message if parsing failed")

    # AI-parsed content
    parsed_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="AI-extracted structured resume data",
    )

    # Metadata
    uploaded_by: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="Uploader user ID")
    language: Mapped[str | None] = mapped_column(
        String(10), nullable=True, default="zh", comment="Detected language code"
    )
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Number of pages")

    # Relationships
    candidate = relationship("Candidate", back_populates="resumes", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Resume {self.original_filename} ({self.parse_status})>"
