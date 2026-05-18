"""
MemoryRelation Model — 记忆间关联关系。

记录记忆之间的语义/逻辑关系，支持关联检索和记忆图谱构建。

Relation types:
  - similar:      相似记忆（内容接近）
  - contradicts:  矛盾记忆（内容冲突）
  - supplements:  补充记忆（扩展信息）
  - derived_from: 派生记忆（由父记忆推导）
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TenantMixin, TimestampMixin


class MemoryRelation(Base, PrimaryKeyMixin, TimestampMixin, TenantMixin):
    """记忆关联关系 — 记录记忆之间的语义/逻辑关联。"""

    __tablename__ = "memory_relations"

    source_memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="源记忆 ID",
    )
    target_memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="目标记忆 ID",
    )
    relation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="关系类型: similar/contradicts/supplements/derived_from",
    )
    strength: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
        comment="关系强度 (0-1)",
    )

    # Relationships
    source_memory = relationship(
        "Memory",
        foreign_keys=[source_memory_id],
        backref="outgoing_relations",
    )
    target_memory = relationship(
        "Memory",
        foreign_keys=[target_memory_id],
        backref="incoming_relations",
    )

    def __repr__(self) -> str:
        return (
            f"<MemoryRelation {self.source_memory_id} → "
            f"{self.target_memory_id} type={self.relation_type}>"
        )
