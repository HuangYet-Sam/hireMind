"""
Candidate Router.

Endpoints for managing candidates (候选人) throughout the recruitment process.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUserDep, DbSession, PaginationDep
from app.schemas.candidate import (
    CandidateCreate,
    CandidateListResponse,
    CandidateResponse,
    CandidateUpdate,
)

router = APIRouter()


@router.get("/", response_model=CandidateListResponse, summary="List candidates")
async def list_candidates(
    db: DbSession,
    pagination: PaginationDep,
    current_user: CurrentUserDep,
    position_id: UUID | None = Query(None, description="Filter by applied position"),
    status: str | None = Query(None, description="Filter by candidate status"),
    keyword: str | None = Query(None, description="Search by name or email"),
):
    """Return a paginated list of candidates."""
    # TODO: delegate to candidate_service.list_candidates(...)
    return CandidateListResponse(
        items=[],
        total=0,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/",
    response_model=CandidateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create candidate",
)
async def create_candidate(
    payload: CandidateCreate,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Register a new candidate."""
    # TODO: delegate to candidate_service.create(...)
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{candidate_id}", response_model=CandidateResponse, summary="Get candidate")
async def get_candidate(
    candidate_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Retrieve a single candidate by ID."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.put("/{candidate_id}", response_model=CandidateResponse, summary="Update candidate")
async def update_candidate(
    candidate_id: UUID,
    payload: CandidateUpdate,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Update candidate information."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.delete(
    "/{candidate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete candidate",
)
async def delete_candidate(
    candidate_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Soft-delete a candidate record."""
    raise HTTPException(status_code=501, detail="Not implemented yet")
