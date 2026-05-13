"""
Department Model (部门).

Represents organizational departments in the company hierarchy.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TenantMixin, TimestampMixin


class Department(Base, PrimaryKeyMixin, TimestampMixin, TenantMixin):
    """Department / organizational unit model."""

    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Department name")
    code: Mapped[str | None] = mapped_column(
        String(50), nullable=True, unique=True, comment="Department code (e.g. ENG, HR, MKT)"
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        comment="Parent department ID (for hierarchy)",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    head_user_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="Department head user ID"
    )
    headcount_limit: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Maximum headcount"
    )
    current_headcount: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Current headcount"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active", comment="active / archived"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Display order")

    # Relationships
    parent = relationship("Department", remote_side="Department.id", backref="children", lazy="selectin")
    positions = relationship("Position", back_populates="department", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Department {self.name}>"
