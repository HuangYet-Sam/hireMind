"""
HR Offer Agent Tool.

Exposes offer management capabilities as Agent Tools
via the ``@AiCapability`` decorator.

Registered capabilities:
  - ``hr_offer_create``            — Create a new offer
  - ``hr_offer_approve``           — Approve an offer
  - ``hr_offer_reject``            — Reject an offer
  - ``hr_offer_withdraw``          — Withdraw an offer
  - ``hr_offer_salary_suggestion`` — AI salary suggestion
  - ``hr_offer_benchmark``         — Compensation benchmark
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.decorators.ai_capability import AiCapability

logger = logging.getLogger("hiremind.tools.hr_offer")


# ---------------------------------------------------------------------------
# Tool: HR Offer Create — 创建Offer
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_offer_create",
    name="HR Offer Create",
    endpoint="/api/v1/offers/",
    method="POST",
    tool_name="hr_offer_create",
    permissions=["offer:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_offer_create_v1",
    description="Create a new job offer for a candidate with compensation details",
    request_model="OfferCreate",
    response_model="OfferResponse",
    rate_limit="30/minute",
    data_classification="L3",
    audit_level="detailed",
    tags=["hr", "offer", "create"],
    timeout=10.0,
)
async def create_offer(
    *,
    candidate_id: str,
    position_id: str | None = None,
    base_salary: int | None = None,
    annual_bonus_months: float | None = None,
    sign_on_bonus: int | None = None,
    equity: str | None = None,
    benefits_summary: str | None = None,
    proposed_start_date: str | None = None,
    probation_months: int = 3,
    work_location: str | None = None,
    employment_type: str | None = None,
    notes: str | None = None,
    tenant_id: str = "default",
    user_id: str = "agent",
) -> dict[str, Any]:
    """
    Create a new job offer.

    Creates an offer record for a candidate with specified compensation
    and employment details. The offer starts in 'draft' status.

    Args:
        candidate_id: UUID of the candidate.
        position_id: UUID of the position (optional).
        base_salary: Base monthly salary.
        annual_bonus_months: Annual bonus in months.
        sign_on_bonus: One-time sign-on bonus.
        equity: Equity / stock options description.
        benefits_summary: Benefits package summary.
        proposed_start_date: ISO 8601 date string for start date.
        probation_months: Probation period in months (default 3).
        work_location: Work location.
        employment_type: Employment type (full_time / contract / etc.).
        notes: Internal notes.
        tenant_id: Tenant scope identifier.
        user_id: User creating the offer.

    Returns:
        Dict with created offer details.
    """
    from datetime import datetime

    from app.dependencies import get_db
    from app.schemas.offer import OfferCreate
    from app.services.offer_service import OfferService

    async for session in get_db():
        svc = OfferService(session)
        create_data = OfferCreate(
            candidate_id=UUID(candidate_id),
            position_id=UUID(position_id) if position_id else None,
            base_salary=base_salary,
            annual_bonus_months=annual_bonus_months,
            sign_on_bonus=sign_on_bonus,
            equity=equity,
            benefits_summary=benefits_summary,
            proposed_start_date=datetime.fromisoformat(proposed_start_date) if proposed_start_date else None,
            probation_months=probation_months,
            work_location=work_location,
            employment_type=employment_type,
            notes=notes,
        )
        try:
            offer = await svc.create(
                data=create_data,
                tenant_id=tenant_id,
                user_id=user_id,
            )
            return {
                "status": "success",
                "offer_id": str(offer.id),
                "candidate_id": str(offer.candidate_id),
                "position_id": str(offer.position_id) if offer.position_id else None,
                "offer_status": offer.status,
                "base_salary": offer.base_salary,
                "annual_bonus_months": offer.annual_bonus_months,
                "sign_on_bonus": offer.sign_on_bonus,
                "equity": offer.equity,
            }
        except ValueError as exc:
            return {"error": str(exc), "candidate_id": candidate_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Offer Approve — 审批Offer
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_offer_approve",
    name="HR Offer Approve",
    endpoint="/api/v1/offers/{offer_id}/approve",
    method="POST",
    tool_name="hr_offer_approve",
    permissions=["offer:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_offer_approve_v1",
    description="Approve a pending offer, transitioning it through the approval workflow",
    request_model="OfferApprove",
    response_model="OfferResponse",
    rate_limit="30/minute",
    data_classification="L3",
    audit_level="detailed",
    tags=["hr", "offer", "approve"],
    timeout=10.0,
)
async def approve_offer(
    offer_id: str,
    tenant_id: str,
    *,
    approver_id: str = "agent",
    comment: str | None = None,
) -> dict[str, Any]:
    """
    Approve a pending offer.

    Processes the approval action for the specified approver.
    If all approvals are complete, the offer transitions to 'approved'.

    Args:
        offer_id: UUID of the offer.
        tenant_id: Tenant scope identifier.
        approver_id: ID of the approver.
        comment: Optional approval comment.

    Returns:
        Dict with updated offer status.
    """
    from app.dependencies import get_db
    from app.services.offer_service import OfferService

    async for session in get_db():
        svc = OfferService(session)
        try:
            offer = await svc.process_approval(
                offer_id=UUID(offer_id),
                approver_id=approver_id,
                action="approve",
                comment=comment,
                tenant_id=tenant_id,
            )
            return {
                "status": "success",
                "offer_id": str(offer.id),
                "offer_status": offer.status,
                "approved_by": approver_id,
                "comment": comment,
            }
        except ValueError as exc:
            return {"error": str(exc), "offer_id": offer_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Offer Reject — 拒绝Offer
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_offer_reject",
    name="HR Offer Reject",
    endpoint="/api/v1/offers/{offer_id}/reject",
    method="POST",
    tool_name="hr_offer_reject",
    permissions=["offer:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_offer_reject_v1",
    description="Reject a pending offer with an optional reason",
    request_model="OfferApprovalCreate",
    response_model="OfferResponse",
    rate_limit="30/minute",
    data_classification="L3",
    audit_level="standard",
    tags=["hr", "offer", "reject"],
    timeout=10.0,
)
async def reject_offer(
    offer_id: str,
    tenant_id: str,
    *,
    approver_id: str = "agent",
    reason: str | None = None,
) -> dict[str, Any]:
    """
    Reject a pending offer.

    Rejects the offer and records the reason in the approval history.

    Args:
        offer_id: UUID of the offer.
        tenant_id: Tenant scope identifier.
        approver_id: ID of the rejector.
        reason: Optional rejection reason.

    Returns:
        Dict with rejection confirmation.
    """
    from app.dependencies import get_db
    from app.services.offer_service import OfferService

    async for session in get_db():
        svc = OfferService(session)
        try:
            offer = await svc.process_approval(
                offer_id=UUID(offer_id),
                approver_id=approver_id,
                action="reject",
                comment=reason,
                tenant_id=tenant_id,
            )
            return {
                "status": "success",
                "offer_id": str(offer.id),
                "offer_status": offer.status,
                "rejected_by": approver_id,
                "reason": reason,
            }
        except ValueError as exc:
            return {"error": str(exc), "offer_id": offer_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Offer Withdraw — 撤回Offer
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_offer_withdraw",
    name="HR Offer Withdraw",
    endpoint="/api/v1/offers/{offer_id}",
    method="DELETE",
    tool_name="hr_offer_withdraw",
    permissions=["offer:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_offer_withdraw_v1",
    description="Withdraw an offer that has been sent or is pending",
    request_model="OfferWithdrawRequest",
    response_model="OfferResponse",
    rate_limit="30/minute",
    data_classification="L3",
    audit_level="standard",
    tags=["hr", "offer", "withdraw"],
    timeout=10.0,
)
async def withdraw_offer(
    offer_id: str,
    tenant_id: str,
    *,
    reason: str | None = None,
) -> dict[str, Any]:
    """
    Withdraw an offer.

    Only offers that are not already withdrawn can be withdrawn.

    Args:
        offer_id: UUID of the offer to withdraw.
        tenant_id: Tenant scope identifier.
        reason: Optional withdrawal reason.

    Returns:
        Dict with withdrawal confirmation.
    """
    from app.dependencies import get_db
    from app.services.offer_service import OfferService

    async for session in get_db():
        svc = OfferService(session)
        try:
            offer = await svc.withdraw(
                offer_id=UUID(offer_id),
                tenant_id=tenant_id,
                reason=reason,
            )
            return {
                "status": "success",
                "offer_id": str(offer.id),
                "offer_status": offer.status,
                "withdrawal_reason": reason,
            }
        except ValueError as exc:
            return {"error": str(exc), "offer_id": offer_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Offer Salary Suggestion — AI薪资建议
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_offer_salary_suggestion",
    name="HR Offer Salary Suggestion",
    endpoint="/api/v1/offers/ai/salary-suggestion",
    method="POST",
    tool_name="hr_offer_salary_suggestion",
    permissions=["offer:read", "ai:use"],
    llm_model="gpt-4o-mini",
    fallback_model="gpt-3.5-turbo",
    prompt_version="v1",
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_offer_salary_suggestion_v1",
    description="AI-powered salary suggestion based on position, candidate profile, and internal benchmarks",
    request_model="SalarySuggestionRequest",
    response_model="SalarySuggestion",
    rate_limit="10/minute",
    data_classification="L3",
    audit_level="detailed",
    tags=["hr", "offer", "ai", "salary"],
    timeout=30.0,
)
async def get_salary_suggestion(
    position_id: str,
    candidate_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Get AI salary suggestion.

    Analyses the position salary range, candidate experience, and
    internal historical offers to produce a recommended package.

    Args:
        position_id: UUID of the position.
        candidate_id: UUID of the candidate.
        tenant_id: Tenant scope identifier.

    Returns:
        Dict with salary suggestion details.
    """
    from app.dependencies import get_db
    from app.services.offer_ai_service import OfferAIService

    async for session in get_db():
        svc = OfferAIService(session)
        try:
            result = await svc.suggest_salary(
                position_id=UUID(position_id),
                candidate_id=UUID(candidate_id),
                tenant_id=tenant_id,
            )
            return {
                "status": "success",
                "position_id": str(result.position_id),
                "candidate_id": str(result.candidate_id),
                "suggested_base": result.suggested_base,
                "suggested_bonus": result.suggested_bonus,
                "suggested_equity": result.suggested_equity,
                "total_compensation": result.total_compensation,
                "confidence": result.confidence,
                "reasoning": result.reasoning,
                "market_position": result.market_position,
                "risk_factors": result.risk_factors,
                "negotiation_strategy": result.negotiation_strategy,
            }
        except ValueError as exc:
            return {"error": str(exc), "position_id": position_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Offer Benchmark — 薪资对标
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_offer_benchmark",
    name="HR Offer Benchmark",
    endpoint="/api/v1/offers/{offer_id}/compensation-benchmark",
    method="GET",
    tool_name="hr_offer_benchmark",
    permissions=["offer:read", "ai:use"],
    llm_model="gpt-4o-mini",
    fallback_model="gpt-3.5-turbo",
    prompt_version="v1",
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_offer_benchmark_v1",
    description="Calculate internal compensation benchmarks and fairness score for an offer",
    request_model="CompensationBenchmarkRequest",
    response_model="CompensationBenchmark",
    rate_limit="10/minute",
    data_classification="L3",
    audit_level="detailed",
    tags=["hr", "offer", "benchmark", "ai"],
    timeout=30.0,
)
async def benchmark_compensation(
    offer_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Get compensation benchmark analysis.

    Calculates internal percentile benchmarks (P50/P75/P90) and
    generates a fairness score for the given offer.

    Args:
        offer_id: UUID of the offer.
        tenant_id: Tenant scope identifier.

    Returns:
        Dict with benchmark analysis.
    """
    from app.dependencies import get_db
    from app.services.offer_ai_service import OfferAIService

    async for session in get_db():
        svc = OfferAIService(session)
        try:
            result = await svc.get_compensation_benchmark(
                offer_id=UUID(offer_id),
                tenant_id=tenant_id,
            )
            return {
                "status": "success",
                "offer_id": str(result.offer_id),
                "position_title": result.position_title,
                "candidate_name": result.candidate_name,
                "offered_total": result.offered_total,
                "internal_p50": result.internal_p50,
                "internal_p75": result.internal_p75,
                "internal_p90": result.internal_p90,
                "market_p50": result.market_p50,
                "market_p75": result.market_p75,
                "fairness_score": result.fairness_score,
                "recommendation": result.recommendation,
            }
        except ValueError as exc:
            return {"error": str(exc), "offer_id": offer_id}

    return {"error": "Database session unavailable"}
