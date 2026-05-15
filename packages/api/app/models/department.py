"""
Department Model (部门).

Organizational hierarchy tree. Aligned to DDL §7.7a.
"""

import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin


class Department(Base, PrimaryKeyMixin, TimestampMixin):
    """Department / organizational unit model."""

    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Department code, e.g. ENG, HR"
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    head_user_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="Department head user ID"
    )
    headcount_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tree_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Materialized path, e.g. 'tech.backend'"
    )
    manager_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    parent = relationship(
        "Department", remote_side="Department.id", backref="children", lazy="selectin"
    )
    positions = relationship("Position", back_populates="department", lazy="selectin")

    @property
    def current_headcount(self) -> int:
        try:
            return len(self.positions) if self.positions else 0
        except Exception:
            return 0

    def __repr__(self) -> str:
        return f"<Department {self.name}>"
