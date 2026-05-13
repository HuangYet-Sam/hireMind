"""
Interview Router.

Endpoints for scheduling and managing interviews (面试).
"""

from datetime import datetime

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUserDep, DbSession, PaginationDep
from app.schemas.interview import (
    InterviewCreate,
    InterviewListResponse,
    InterviewResponse,
    InterviewUpdate,
)

router = APIRouter()


@router.get("/", response_model=InterviewListResponse, summary="List interviews")
async def list_interviews(
    db: DbSession,
    pagination: PaginationDep,
    current_user: CurrentUserDep,
    candidate_id: UUID | None = Query(None),
    position_id: UUID | None = Query(None),
    interviewer_id: UUID | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
):
    """Return a paginated list of interviews with optional filters."""
    return InterviewListResponse(
        items=[],
        total=0,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule interview",
)
async def create_interview(
    payload: InterviewCreate,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Schedule a new interview."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{interview_id}", response_model=InterviewResponse, summary="Get interview")
async def get_interview(
    interview_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Retrieve a single interview by ID."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.put("/{interview_id}", response_model=InterviewResponse, summary="Update interview")
async def update_interview(
    interview_id: UUID,
    payload: InterviewUpdate,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Update interview details (reschedule, change interviewer, add feedback)."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.delete(
    "/{interview_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel interview",
)
async def cancel_interview(
    interview_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Cancel an interview."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post(
    "/{interview_id}/feedback",
    response_model=InterviewResponse,
    summary="Submit interview feedback",
)
async def submit_feedback(
    interview_id: UUID,
    payload: InterviewUpdate,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Submit interviewer feedback and score for a completed interview."""
    raise HTTPException(status_code=501, detail="Not implemented yet")
