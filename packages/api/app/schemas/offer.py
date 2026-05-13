"""
Offer Pydantic Schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OfferCreate(BaseModel):
    """Schema for creating a new offer."""

    candidate_id: UUID = Field(...)
    position_id: UUID | None = None
    base_salary: int | None = Field(None, description="Base monthly salary")
    annual_bonus_months: float | None = Field(None, description="Annual bonus in months")
    sign_on_bonus: int | None = Field(None, description="One-time sign-on bonus")
    equity: str | None = Field(None, description="Equity / stock options")
    benefits_summary: str | None = None
    proposed_start_date: datetime | None = None
    probation_months: int | None = Field(3, description="Probation period in months")
    work_location: str | None = None
    employment_type: str | None = None
    notes: str | None = None
    expiry_date: datetime | None = None


class OfferUpdate(BaseModel):
    """Schema for updating offer details."""

    base_salary: int | None = None
    annual_bonus_months: float | None = None
    sign_on_bonus: int | None = None
    equity: str | None = None
    benefits_summary: str | None = None
    proposed_start_date: datetime | None = None
    probation_months: int | None = None
    work_location: str | None = None
    employment_type: str | None = None
    notes: str | None = None
    expiry_date: datetime | None = None


class OfferApprove(BaseModel):
    """Schema for approving an offer."""

    comment: str | None = Field(None, description="Approval comment")


class OfferResponse(BaseModel):
    """Offer response schema."""

    id: UUID
    candidate_id: UUID
    position_id: UUID | None
    status: str
    base_salary: int | None
    annual_bonus_months: float | None
    sign_on_bonus: int | None
    equity: str | None
    benefits_summary: str | None
    proposed_start_date: datetime | None
    probation_months: int | None
    work_location: str | None
    employment_type: str | None
    notes: str | None
    offer_letter_url: str | None
    sent_at: datetime | None
    responded_at: datetime | None
    response_note: str | None
    expiry_date: datetime | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OfferListResponse(BaseModel):
    """Paginated offer list."""

    items: list[OfferResponse]
    total: int
    page: int
    page_size: int
