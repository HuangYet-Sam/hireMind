"""
OfferTemplate Model (Offer模板).

Stores reusable offer letter templates with variable placeholders
for different position types and employment categories.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PrimaryKeyMixin, TenantMixin, TimestampMixin


class OfferTemplate(Base, PrimaryKeyMixin, TimestampMixin, TenantMixin):
    """Offer letter template with variable placeholders."""

    __tablename__ = "offer_templates"

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Template name",
    )
    template_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="standard",
        comment="technical / management / operations / standard",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Template content with {{variable}} placeholders",
    )
    variables: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="List of variable names used in the template",
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is the default template for its type",
    )

    def __repr__(self) -> str:
        return f"<OfferTemplate {self.name} type={self.template_type}>"
