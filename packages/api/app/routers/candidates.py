"""
Candidate Router.

Endpoints for managing candidates (候选人) throughout the recruitment process.
"""

import math
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.dependencies import CurrentUserDep, DbSession, PaginationDep
from app.schemas.candidate import (
    CandidateCreate,
    CandidateListResponse,
    CandidateResponse,
    CandidateUpdate,
)
from app.services.candidate_service import CandidateService

router = APIRouter()


class StageAdvanceRequest(BaseModel):
    stage: str


@router.get("/", response_model=CandidateListResponse, summary="List candidates")
async def list_candidates(
    db: DbSession,
    pagination: PaginationDep,
    current_user: CurrentUserDep,
    position_id: UUID | None = Query(None, description="Filter by applied position"),
    status: str | None = Query(None, description="Filter by candidate status"),
    stage: str | None = Query(None, description="Filter by pipeline stage"),
    keyword: str | None = Query(None, description="Search by summary keyword"),
):
    svc = CandidateService(db)
    items, total = await svc.list_candidates(
        tenant_id=current_user.tenant_id,
        position_id=position_id,
        status=status,
        stage=stage,
        keyword=keyword,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    return CandidateListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
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
    svc = CandidateService(db)
    try:
        candidate = await svc.create(
            data=payload,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return candidate


@router.get("/{candidate_id}", response_model=CandidateResponse, summary="Get candidate")
async def get_candidate(
    candidate_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    svc = CandidateService(db)
    candidate = await svc.get_by_id(candidate_id, current_user.tenant_id)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )
    return candidate


@router.patch("/{candidate_id}", response_model=CandidateResponse, summary="Update candidate")
async def update_candidate(
    candidate_id: UUID,
    payload: CandidateUpdate,
    db: DbSession,
    current_user: CurrentUserDep,
):
    svc = CandidateService(db)
    candidate = await svc.update(
        candidate_id=candidate_id,
        data=payload,
        tenant_id=current_user.tenant_id,
    )
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )
    return candidate


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
    svc = CandidateService(db)
    try:
        await svc.soft_delete(candidate_id, current_user.tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )


@router.post(
    "/{candidate_id}/stage",
    response_model=CandidateResponse,
    summary="Advance candidate stage",
)
async def advance_stage(
    candidate_id: UUID,
    body: StageAdvanceRequest,
    db: DbSession,
    current_user: CurrentUserDep,
):
    svc = CandidateService(db)
    try:
        candidate = await svc.advance_stage(
            candidate_id=candidate_id,
            new_stage=body.stage,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )
    return candidate
