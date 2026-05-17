"""
Offer Router.

Endpoints for creating, approving, and managing job offers (Offer).
"""

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import CurrentUser, CurrentUserDep, DbSession, PaginationDep, require_role
from app.schemas.offer import (
    OfferApprove,
    OfferCreate,
    OfferListResponse,
    OfferResponse,
    OfferUpdate,
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
