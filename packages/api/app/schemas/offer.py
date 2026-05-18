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
    pages: int


# ---------------------------------------------------------------------------
# Offer Approval Schemas
# ---------------------------------------------------------------------------

class OfferApprovalCreate(BaseModel):
    """审批操作"""
    action: str  # approve / reject / withdraw / counter
    comment: str | None = None
    next_approver_id: str | None = None


class OfferApprovalResponse(BaseModel):
    """审批记录"""
    id: UUID
    offer_id: UUID
    approver_id: str
    approver_name: str | None
    action: str
    comment: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Offer Template Schemas
# ---------------------------------------------------------------------------

class OfferTemplateCreate(BaseModel):
    """Offer模板"""
    name: str
    template_type: str  # technical / management / operations / standard
    content: str  # 模板内容(支持变量占位符 {{candidate_name}} 等)
    variables: list[str]  # 模板变量列表
    is_default: bool = False


class OfferTemplateResponse(BaseModel):
    """Offer模板响应"""
    id: UUID
    name: str
    template_type: str
    content: str
    variables: list[str]
    is_default: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Compensation Benchmark & Salary Suggestion Schemas
# ---------------------------------------------------------------------------

class CompensationBenchmark(BaseModel):
    """薪资对标"""
    offer_id: UUID
    position_title: str
    candidate_name: str
    offered_total: float  # Offer总包
    internal_p50: float  # 内部P50
    internal_p75: float
    internal_p90: float
    market_p50: float | None  # 市场P50(如有数据)
    market_p75: float | None
    fairness_score: float  # 内部公平性评分 0-100
    recommendation: str  # below_market / at_market / above_market


class SalarySuggestion(BaseModel):
    """AI薪资建议"""
    suggested_base: float
    suggested_bonus: float | None
    suggested_equity: str | None
    total_compensation: float
    confidence: float  # 0-1
    reasoning: str  # 建议理由
    market_position: str  # below_p50 / p50_p75 / p75_p90 / above_p90
    risk_factors: list[str]  # 风险因素
    negotiation_strategy: str  # 谈判策略建议


# ---------------------------------------------------------------------------
# Additional Offer Schemas (counter, generate, negotiation)
# ---------------------------------------------------------------------------

class OfferCounterCreate(BaseModel):
    """Counter-offer request."""
    base_salary: int | None = None
    annual_bonus_months: float | None = None
    sign_on_bonus: int | None = None
    equity: str | None = None
    benefits_summary: str | None = None
    notes: str | None = None


class OfferGenerateRequest(BaseModel):
    """AI生成Offer请求"""
    candidate_id: UUID
    position_id: UUID | None = None
    template_id: UUID | None = None
    use_ai_suggestion: bool = True


class OfferNegotiationAdvice(BaseModel):
    """谈判策略建议"""
    offer_id: UUID
    candidate_name: str
    current_package: float
    advice: str
    key_negotiation_points: list[str]
    risk_assessment: str
    recommended_actions: list[str]
    alternative_packages: list[dict]
    timeline_suggestion: str


class OfferTimelineEvent(BaseModel):
    """Offer状态变更事件"""
    status: str
    changed_at: datetime
    changed_by: str | None
    comment: str | None


class OfferTimelineResponse(BaseModel):
    """Offer状态时间轴"""
    offer_id: UUID
    events: list[OfferTimelineEvent]
