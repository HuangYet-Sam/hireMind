"""
SkillRegistry Model — registered AI skills / tools / prompts.

A Skill is an executable capability registered in the system that can be
invoked by agents or users. Types include: tool (external API call),
prompt (LLM prompt template), and workflow (multi-step orchestration).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PrimaryKeyMixin, TenantMixin, TimestampMixin


class SkillRegistry(Base, PrimaryKeyMixin, TimestampMixin, TenantMixin):
    """Registered AI skill / tool / prompt / workflow."""

    __tablename__ = "skill_registry"

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Skill display name",
    )
    skill_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="tool / prompt / workflow",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Skill description",
    )
    prompt_template: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Prompt template with {{variable}} placeholders (for prompt/workflow types)",
    )
    input_schema: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="JSON Schema for input validation",
    )
    output_schema: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="JSON Schema for output validation",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether the skill is currently active",
    )
    call_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total invocation count",
    )
    avg_latency_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Average execution latency in milliseconds",
    )
    last_called_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last invocation timestamp",
    )
    tags: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="Tags for categorization and search",
    )

    def __repr__(self) -> str:
        return f"<SkillRegistry {self.name} type={self.skill_type}>"
