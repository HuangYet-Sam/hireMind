"""
Offer Router.

Endpoints for creating, approving, and managing job offers (Offer).
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUserDep, DbSession, PaginationDep
from app.schemas.offer import (
    OfferApprove,
    OfferCreate,
    OfferListResponse,
    OfferResponse,
    OfferUpdate,
)

router = APIRouter()


@router.get("/", response_model=OfferListResponse, summary="List offers")
async def list_offers(
    db: DbSession,
    pagination: PaginationDep,
    current_user: CurrentUserDep,
    candidate_id: UUID | None = Query(None),
    position_id: UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status", description="draft/sent/accepted/rejected/withdrawn"),
):
    """Return a paginated list of offers."""
    return OfferListResponse(
        items=[],
        total=0,
        page=pagination.page,
        page_size=pagination.page_size,
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
    current_user: CurrentUserDep,
):
    """Create a new offer for a candidate."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{offer_id}", response_model=OfferResponse, summary="Get offer")
async def get_offer(
    offer_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Retrieve a single offer by ID."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.put("/{offer_id}", response_model=OfferResponse, summary="Update offer")
async def update_offer(
    offer_id: UUID,
    payload: OfferUpdate,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Update offer details (salary, benefits, etc.)."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post(
    "/{offer_id}/approve",
    response_model=OfferResponse,
    summary="Approve offer",
)
async def approve_offer(
    offer_id: UUID,
    payload: OfferApprove,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Approve an offer (multi-level approval workflow)."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post(
    "/{offer_id}/send",
    response_model=OfferResponse,
    summary="Send offer to candidate",
)
async def send_offer(
    offer_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Send the offer to the candidate via email / portal."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.delete(
    "/{offer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Withdraw offer",
)
async def withdraw_offer(
    offer_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Withdraw (cancel) an offer."""
    raise HTTPException(status_code=501, detail="Not implemented yet")
