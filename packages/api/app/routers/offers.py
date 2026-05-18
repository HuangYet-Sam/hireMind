"""
Offer Router.

Endpoints for creating, approving, and managing job offers (Offer).
Includes AI-powered salary suggestion, compensation benchmarking,
approval workflow, template management, and negotiation advice.
"""

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import CurrentUser, CurrentUserDep, DbSession, PaginationDep, require_role
from app.schemas.offer import (
    CompensationBenchmark,
    OfferApprovalCreate,
    OfferApprovalResponse,
    OfferApprove,
    OfferCounterCreate,
    OfferCreate,
    OfferGenerateRequest,
    OfferListResponse,
    OfferNegotiationAdvice,
    OfferResponse,
    OfferTemplateCreate,
    OfferTemplateResponse,
    OfferTimelineResponse,
    OfferUpdate,
    SalarySuggestion,
)
from app.services.offer_service import OfferService

router = APIRouter()

_HrManagerOrAbove = Annotated[CurrentUser, Depends(require_role("hr_manager", "admin"))]
_RecruiterOrAbove = Annotated[CurrentUser, Depends(require_role("recruiter", "hr_manager", "admin"))]


@router.post("/ai/salary-recommendation", summary="Generate AI salary recommendation")
async def generate_salary_recommendation(
    payload: dict,
    current_user: CurrentUserDep,
):
    """
    Generate AI-powered offer salary recommendation.

    Request body: {
        "candidate": {"skills": [...], "profile": {...}},
        "position": {"title": "...", "salary_min": ..., "salary_max": ...},
        "market_data": {} // optional
    }
    """
    from app.services.ai_client import ai_client

    result = await ai_client.generate_offer_recommendation(
        candidate_info=payload.get("candidate", {}),
        position_info=payload.get("position", {}),
        market_data=payload.get("market_data"),
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service unavailable. Configure Hermes Agent or OpenAI API key.",
        )
    return result


@router.get("", response_model=OfferListResponse, summary="List offers")
async def list_offers(
    db: DbSession,
    pagination: PaginationDep,
    current_user: CurrentUserDep,
    candidate_id: UUID | None = Query(None),
    position_id: UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status", description="draft/sent/accepted/rejected/withdrawn"),
):
    service = OfferService(db)
    items, total = await service.list_offers(
        tenant_id=current_user.tenant_id,
        candidate_id=candidate_id,
        position_id=position_id,
        status=status_filter,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    return OfferListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
    )


@router.post(
    "/",
    response_model=OfferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create offer",
)
async def create_offer(
    payload: OfferCreate,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    service = OfferService(db)
    try:
        offer = await service.create(
            data=payload,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return offer


@router.get("/{offer_id}", response_model=OfferResponse, summary="Get offer")
async def get_offer(
    offer_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    service = OfferService(db)
    offer = await service.get_by_id(offer_id, current_user.tenant_id)
    if offer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found"
        )
    return offer


@router.patch("/{offer_id}", response_model=OfferResponse, summary="Update offer")
async def update_offer(
    offer_id: UUID,
    payload: OfferUpdate,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    service = OfferService(db)
    try:
        offer = await service.update(
            offer_id=offer_id,
            data=payload,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        msg = str(exc)
        if "draft" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=msg
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=msg
        )
    return offer


@router.post(
    "/{offer_id}/approve",
    response_model=OfferResponse,
    summary="Approve offer",
)
async def approve_offer(
    offer_id: UUID,
    payload: OfferApprove,
    db: DbSession,
    current_user: _HrManagerOrAbove,
):
    service = OfferService(db)
    try:
        offer = await service.approve(
            offer_id=offer_id,
            approver_id=current_user.user_id,
            approver_name=None,
            comment=payload.comment,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        msg = str(exc)
        if "already acted" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=msg
            )
        if "pending approval" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=msg
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=msg
        )
    return offer


@router.post(
    "/{offer_id}/send",
    response_model=OfferResponse,
    summary="Send offer to candidate",
)
async def send_offer(
    offer_id: UUID,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    service = OfferService(db)
    try:
        offer = await service.send(
            offer_id=offer_id,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )
    return offer


@router.delete(
    "/{offer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Withdraw offer",
)
async def withdraw_offer(
    offer_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
    reason: str | None = Query(None, description="Withdrawal reason"),
):
    service = OfferService(db)
    try:
        await service.withdraw(
            offer_id=offer_id,
            tenant_id=current_user.tenant_id,
            reason=reason,
        )
    except ValueError as exc:
        msg = str(exc)
        if "already withdrawn" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=msg
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=msg
        )


# =====================================================================
# M6 New Endpoints — AI, Approval, Templates, Negotiation
# =====================================================================


@router.post("/generate", summary="AI generate offer with salary suggestion")
async def generate_offer(
    payload: OfferGenerateRequest,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    """AI-generate an offer with salary suggestion.

    Creates a new offer populated with AI-suggested salary data for the
    given candidate and position.
    """
    from app.services.offer_ai_service import OfferAIService

    ai_svc = OfferAIService(db)
    offer_svc = OfferService(db)

    # Get AI salary suggestion if position provided
    salary_suggestion = None
    if payload.position_id and payload.use_ai_suggestion:
        try:
            salary_suggestion = await ai_svc.suggest_salary(
                position_id=payload.position_id,
                candidate_id=payload.candidate_id,
                tenant_id=current_user.tenant_id,
            )
        except ValueError:
            salary_suggestion = None

    # Build offer create data
    create_data = OfferCreate(
        candidate_id=payload.candidate_id,
        position_id=payload.position_id,
        base_salary=int(salary_suggestion.suggested_base) if salary_suggestion else None,
        annual_bonus_months=salary_suggestion.suggested_bonus if salary_suggestion else None,
        equity=salary_suggestion.suggested_equity if salary_suggestion else None,
    )

    try:
        offer = await offer_svc.create(
            data=create_data,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )

    return {
        "offer": offer,
        "salary_suggestion": {
            "suggested_base": salary_suggestion.suggested_base,
            "suggested_bonus": salary_suggestion.suggested_bonus,
            "suggested_equity": salary_suggestion.suggested_equity,
            "total_compensation": salary_suggestion.total_compensation,
            "confidence": salary_suggestion.confidence,
            "reasoning": salary_suggestion.reasoning,
            "market_position": salary_suggestion.market_position,
            "risk_factors": salary_suggestion.risk_factors,
            "negotiation_strategy": salary_suggestion.negotiation_strategy,
        } if salary_suggestion else None,
    }


@router.get(
    "/{offer_id}/compensation-benchmark",
    response_model=CompensationBenchmark,
    summary="Compensation benchmark",
)
async def get_compensation_benchmark(
    offer_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Get compensation benchmark analysis for an offer.

    Returns internal percentile benchmarks and a fairness score.
    """
    from app.services.offer_ai_service import OfferAIService

    ai_svc = OfferAIService(db)
    try:
        result = await ai_svc.get_compensation_benchmark(
            offer_id=offer_id,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )

    return CompensationBenchmark(
        offer_id=result.offer_id,
        position_title=result.position_title,
        candidate_name=result.candidate_name,
        offered_total=result.offered_total,
        internal_p50=result.internal_p50,
        internal_p75=result.internal_p75,
        internal_p90=result.internal_p90,
        market_p50=result.market_p50,
        market_p75=result.market_p75,
        fairness_score=result.fairness_score,
        recommendation=result.recommendation,
    )


@router.post(
    "/{offer_id}/reject",
    response_model=OfferResponse,
    summary="Reject offer",
)
async def reject_offer(
    offer_id: UUID,
    payload: OfferApprovalCreate,
    db: DbSession,
    current_user: _HrManagerOrAbove,
):
    """Reject a pending offer."""
    service = OfferService(db)
    try:
        offer = await service.process_approval(
            offer_id=offer_id,
            approver_id=current_user.user_id,
            action="reject",
            comment=payload.comment,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )
    return offer


@router.post(
    "/{offer_id}/withdraw",
    response_model=OfferResponse,
    summary="Withdraw offer (POST variant)",
)
async def withdraw_offer_post(
    offer_id: UUID,
    payload: OfferApprovalCreate,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Withdraw an offer via POST."""
    service = OfferService(db)
    try:
        offer = await service.process_approval(
            offer_id=offer_id,
            approver_id=current_user.user_id,
            action="withdraw",
            comment=payload.comment,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )
    return offer


@router.post(
    "/{offer_id}/counter",
    response_model=OfferResponse,
    summary="Counter offer",
)
async def counter_offer(
    offer_id: UUID,
    payload: OfferCounterCreate,
    db: DbSession,
    current_user: _HrManagerOrAbove,
):
    """Process a counter-offer with updated compensation."""
    service = OfferService(db)
    try:
        offer = await service.counter_offer(
            offer_id=offer_id,
            tenant_id=current_user.tenant_id,
            data=payload.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    return offer


@router.get(
    "/{offer_id}/approvals",
    response_model=list[OfferApprovalResponse],
    summary="Approval history",
)
async def get_approvals(
    offer_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Get the full approval history for an offer."""
    service = OfferService(db)

    # Verify offer exists in tenant
    offer = await service.get_by_id(offer_id, current_user.tenant_id)
    if offer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found"
        )

    approvals = await service.get_approval_history(offer_id)
    return [
        OfferApprovalResponse(
            id=a.id,
            offer_id=a.offer_id,
            approver_id=a.approver_id,
            approver_name=a.approver_name,
            action=a.status,
            comment=a.comment,
            created_at=a.approved_at or a.created_at,
        )
        for a in approvals
    ]


@router.get(
    "/{offer_id}/timeline",
    response_model=OfferTimelineResponse,
    summary="Offer status timeline",
)
async def get_timeline(
    offer_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Get the full status change timeline for an offer."""
    from app.schemas.offer import OfferTimelineEvent

    service = OfferService(db)
    try:
        events = await service.get_status_timeline(
            offer_id=offer_id,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )

    return OfferTimelineResponse(
        offer_id=offer_id,
        events=[
            OfferTimelineEvent(
                status=e["status"],
                changed_at=e["changed_at"],
                changed_by=e["changed_by"],
                comment=e["comment"],
            )
            for e in events
        ],
    )


@router.post(
    "/{offer_id}/negotiation-advice",
    response_model=OfferNegotiationAdvice,
    summary="Negotiation advice",
)
async def get_negotiation_advice(
    offer_id: UUID,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    """Get AI-powered negotiation strategy advice for an offer."""
    from app.services.offer_ai_service import OfferAIService

    ai_svc = OfferAIService(db)
    try:
        result = await ai_svc.get_negotiation_advice(
            offer_id=offer_id,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )

    return OfferNegotiationAdvice(
        offer_id=result.offer_id,
        candidate_name=result.candidate_name,
        current_package=result.current_package,
        advice=result.advice,
        key_negotiation_points=result.key_negotiation_points,
        risk_assessment=result.risk_assessment,
        recommended_actions=result.recommended_actions,
        alternative_packages=result.alternative_packages,
        timeline_suggestion=result.timeline_suggestion,
    )


# -----------------------------------------------------------------
# Template endpoints
# -----------------------------------------------------------------

@router.get(
    "/templates",
    response_model=list[OfferTemplateResponse],
    summary="List offer templates",
)
async def list_templates(
    db: DbSession,
    current_user: CurrentUserDep,
    template_type: str | None = Query(None, description="Filter by template type"),
):
    """List available offer templates for the current tenant."""
    service = OfferService(db)
    templates = await service.list_templates(
        tenant_id=current_user.tenant_id,
        template_type=template_type,
    )
    return templates


@router.post(
    "/templates",
    response_model=OfferTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create offer template",
)
async def create_template(
    payload: OfferTemplateCreate,
    db: DbSession,
    current_user: _HrManagerOrAbove,
):
    """Create a new offer letter template."""
    service = OfferService(db)
    template = await service.create_template(
        name=payload.name,
        template_type=payload.template_type,
        content=payload.content,
        variables=payload.variables,
        is_default=payload.is_default,
        tenant_id=current_user.tenant_id,
    )
    return template


@router.post(
    "/{offer_id}/render-letter",
    summary="Render offer letter",
)
async def render_offer_letter(
    offer_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
    template_id: UUID | None = Query(None, description="Template ID (default template if omitted)"),
):
    """Render an offer letter using a template with variable substitution."""
    service = OfferService(db)
    try:
        content = await service.render_offer_letter(
            offer_id=offer_id,
            template_id=template_id,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )

    return {"offer_id": str(offer_id), "content": content, "template_id": str(template_id) if template_id else None}
