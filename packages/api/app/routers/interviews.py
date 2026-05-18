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
    InterviewAnalysisResponse,
    InterviewBriefingResponse,
    InterviewCalendarEvent,
    InterviewCalendarResponse,
    InterviewQuestionsResponse,
    InterviewerWorkload,
    TimeSlotRecommendation,
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


@router.get("", response_model=InterviewListResponse, summary="List interviews")
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


# ===================================================================
# M5 Extended Endpoints — calendar, workload, batch, AI, round advance
# ===================================================================


@router.get("/calendar", response_model=InterviewCalendarResponse, summary="Interview calendar view")
async def get_calendar(
    db: DbSession,
    current_user: CurrentUserDep,
    date_from: datetime = Query(..., description="Range start (inclusive)"),
    date_to: datetime = Query(..., description="Range end (inclusive)"),
):
    """Get interview events in a date range for calendar display."""
    service = InterviewService(db)
    interviews = await service.get_calendar_events(
        tenant_id=current_user.tenant_id,
        date_from=date_from,
        date_to=date_to,
    )

    events: list[InterviewCalendarEvent] = []
    for iv in interviews:
        candidate_name = ""
        if iv.candidate:
            candidate_name = getattr(iv.candidate, "name_encrypted", "") or str(iv.candidate_id)

        position_title = None
        if iv.position:
            position_title = getattr(iv.position, "title", None)

        from datetime import timedelta
        end_time = (
            iv.scheduled_at + timedelta(minutes=iv.duration_minutes)
            if iv.scheduled_at
            else iv.scheduled_at
        )

        events.append(InterviewCalendarEvent(
            id=iv.id,
            title=f"Round {iv.round_number} {iv.interview_type} – {candidate_name}",
            start=iv.scheduled_at,
            end=end_time,
            status=iv.status,
            candidate_name=candidate_name,
            position_title=position_title,
            interview_type=iv.interview_type,
            interviewer_ids=iv.interviewer_ids or [],
        ))

    return InterviewCalendarResponse(
        events=events,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/workload-stats", response_model=list[InterviewerWorkload], summary="Interviewer workload stats")
async def get_workload_stats(
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Get per-interviewer workload statistics for the current tenant."""
    service = InterviewService(db)
    stats = await service.get_workload_stats(tenant_id=current_user.tenant_id)
    return [InterviewerWorkload(**s) for s in stats]


@router.post("/batch", response_model=list[InterviewResponse], status_code=status.HTTP_201_CREATED, summary="Batch schedule interviews")
async def batch_create_interviews(
    payload: list[InterviewCreate],
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    """Create multiple interviews in a single request (batch scheduling)."""
    service = InterviewService(db)
    try:
        created = await service.batch_create(
            items=payload,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )
    return created


@router.post("/{interview_id}/briefing", response_model=InterviewBriefingResponse, summary="Generate AI interview briefing")
async def generate_briefing(
    interview_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Generate an AI-powered interview briefing based on position-candidate gap analysis."""
    from app.services.interview_ai_service import InterviewAIService

    ai_svc = InterviewAIService(db)
    try:
        result = await ai_svc.generate_briefing(
            interview_id=interview_id,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    return InterviewBriefingResponse(
        interview_id=result.interview_id,
        position_requirements=result.position_requirements,
        candidate_strengths=result.candidate_strengths,
        candidate_gaps=result.candidate_gaps,
        verification_points=result.verification_points,
        focus_areas=result.focus_areas,
        suggested_questions=result.suggested_questions,
    )


@router.post("/{interview_id}/questions", response_model=InterviewQuestionsResponse, summary="Generate AI interview questions")
async def generate_questions(
    interview_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Generate AI-powered interview questions grouped by competency dimension."""
    from app.services.interview_ai_service import InterviewAIService

    ai_svc = InterviewAIService(db)
    try:
        result = await ai_svc.generate_questions(
            interview_id=interview_id,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    return InterviewQuestionsResponse(
        interview_id=result.interview_id,
        question_groups=[
            {
                "dimension": g.dimension,
                "difficulty": g.difficulty,
                "questions": [
                    {
                        "question": q.question,
                        "follow_ups": q.follow_ups,
                        "evaluation_criteria": q.evaluation_criteria,
                    }
                    for q in g.questions
                ],
            }
            for g in result.question_groups
        ],
        total_questions=result.total_questions,
    )


@router.get("/{interview_id}/recommend-slots", response_model=list[TimeSlotRecommendation], summary="AI recommend time slots")
async def recommend_slots(
    interview_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
    duration_minutes: int = Query(60, ge=15, le=480),
    num_slots: int = Query(5, ge=1, le=20),
):
    """Recommend available time slots for scheduling, avoiding conflicts."""
    from app.services.interview_ai_service import InterviewAIService

    svc = InterviewService(db)
    interview = await svc.get_by_id(interview_id, current_user.tenant_id)
    if interview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found"
        )

    ai_svc = InterviewAIService(db)
    try:
        result = await ai_svc.recommend_timeslots(
            position_id=interview.position_id,
            candidate_id=interview.candidate_id,
            duration_minutes=duration_minutes,
            tenant_id=current_user.tenant_id,
            num_slots=num_slots,
            interviewer_ids=interview.interviewer_ids,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    return [
        TimeSlotRecommendation(
            start=slot.start,
            end=slot.end,
            score=slot.score,
            reason=slot.reason,
            conflicts=slot.conflicts,
        )
        for slot in result.recommended_slots
    ]


@router.post("/{interview_id}/analyze", response_model=InterviewAnalysisResponse, summary="AI feedback analysis")
async def analyze_interview(
    interview_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Perform AI-powered analysis of interview feedback."""
    from app.services.interview_ai_service import InterviewAIService

    ai_svc = InterviewAIService(db)
    try:
        result = await ai_svc.analyze_feedback(
            interview_id=interview_id,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg or "No feedback" in msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=msg
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=msg
        )
    return InterviewAnalysisResponse(
        interview_id=result.interview_id,
        overall_score=result.overall_score,
        score_breakdown=result.score_breakdown,
        strengths=result.strengths,
        concerns=result.concerns,
        recommendation=result.recommendation,
        recommendation_reason=result.recommendation_reason,
        improvement_suggestions=result.improvement_suggestions,
        candidate_fit_score=result.candidate_fit_score,
    )


@router.post("/{interview_id}/advance-round", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED, summary="Advance to next round")
async def advance_round(
    interview_id: UUID,
    db: DbSession,
    current_user: _RecruiterOrAbove,
    payload: dict | None = None,
):
    """Advance a completed interview to the next round.

    Request body (optional): {
        "next_interview_type": "technical|behavioral|hr|final",
        "next_scheduled_at": "ISO 8601 datetime",
        "next_interviewer_ids": ["id1", "id2"]
    }
    """
    service = InterviewService(db)
    body = payload or {}

    next_type = body.get("next_interview_type")
    next_at = body.get("next_scheduled_at")
    next_interviewers = body.get("next_interviewer_ids")

    from datetime import datetime as _dt

    try:
        next_interview = await service.advance_round(
            interview_id=interview_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
            next_interview_type=next_type,
            next_scheduled_at=_dt.fromisoformat(next_at) if next_at else None,
            next_interviewer_ids=next_interviewers,
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
    return next_interview
