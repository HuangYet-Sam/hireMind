"""
Interview Router.

Endpoints for scheduling and managing interviews (面试).
"""

import math
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import CurrentUser, CurrentUserDep, DbSession, PaginationDep, require_role
from app.schemas.interview import (
    InterviewCreate,
    InterviewFeedbackCreate,
    InterviewListResponse,
    InterviewResponse,
    InterviewUpdate,
)
from app.services.interview_service import InterviewService

router = APIRouter()

_RecruiterOrAbove = Annotated[CurrentUser, Depends(require_role("recruiter", "hr_manager", "admin"))]


@router.post("/ai/questions", summary="Generate AI interview questions")
async def generate_ai_questions(
    payload: dict,
    current_user: CurrentUserDep,
):
    """
    Generate AI-powered interview questions for a position-candidate pair.

    Request body: {
        "position": {"title": "...", "required_skills": [...], "description": "..."},
        "candidate": {"skills": [...], "profile": {...}},
        "interview_type": "technical|behavioral|system|case",
        "num_questions": 5
    }
    """
    from app.services.ai_client import ai_client

    position_info = payload.get("position", {})
    candidate_info = payload.get("candidate", {})
    interview_type = payload.get("interview_type", "technical")
    num_questions = payload.get("num_questions", 5)

    result = await ai_client.generate_interview_questions(
        position_info=position_info,
        candidate_info=candidate_info,
        interview_type=interview_type,
        num_questions=num_questions,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service unavailable. Configure Hermes Agent or OpenAI API key.",
        )
    return result


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
    service = InterviewService(db)
    items, total = await service.list_interviews(
        tenant_id=current_user.tenant_id,
        candidate_id=candidate_id,
        position_id=position_id,
        interviewer_id=interviewer_id,
        date_from=date_from,
        date_to=date_to,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    return InterviewListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
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
    current_user: _RecruiterOrAbove,
):
    service = InterviewService(db)
    try:
        interview = await service.create(
            data=payload,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )
    return interview


@router.get("/{interview_id}", response_model=InterviewResponse, summary="Get interview")
async def get_interview(
    interview_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    service = InterviewService(db)
    interview = await service.get_by_id(interview_id, current_user.tenant_id)
    if interview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found"
        )
    return interview


@router.patch("/{interview_id}", response_model=InterviewResponse, summary="Update interview")
async def update_interview(
    interview_id: UUID,
    payload: InterviewUpdate,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    service = InterviewService(db)
    try:
        interview = await service.update(
            interview_id=interview_id,
            data=payload,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=msg
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=msg
        )
    return interview


@router.delete(
    "/{interview_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel interview",
)
async def cancel_interview(
    interview_id: UUID,
    db: DbSession,
    current_user: _RecruiterOrAbove,
    reason: str | None = Query(None, description="Cancellation reason"),
):
    service = InterviewService(db)
    try:
        await service.cancel(
            interview_id=interview_id,
            tenant_id=current_user.tenant_id,
            reason=reason,
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=msg
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=msg
        )


@router.post(
    "/{interview_id}/feedback",
    response_model=InterviewResponse,
    summary="Submit interview feedback",
)
async def submit_feedback(
    interview_id: UUID,
    payload: InterviewFeedbackCreate,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    service = InterviewService(db)
    try:
        interview = await service.submit_feedback(
            interview_id=interview_id,
            interviewer_id=current_user.user_id,
            data=payload,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=msg
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=msg
        )
    return interview
