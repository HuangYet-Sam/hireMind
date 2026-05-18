"""
HR Interview Agent Tool.

Exposes interview management capabilities as Agent Tools
via the ``@AiCapability`` decorator.

Registered capabilities:
  - ``hr_interview_schedule``   — Schedule a new interview
  - ``hr_interview_cancel``     — Cancel an existing interview
  - ``hr_interview_feedback``   — Submit interview feedback
  - ``hr_interview_analyze``    — AI-powered interview analysis
  - ``hr_interview_workload``   — Query interviewer workload statistics
  - ``hr_interview_reminder``   — Send interview reminder (skeleton)
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.decorators.ai_capability import AiCapability

logger = logging.getLogger("hiremind.tools.hr_interview")


# ---------------------------------------------------------------------------
# Tool: HR Interview Schedule — 安排面试
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_interview_schedule",
    name="HR Interview Schedule",
    endpoint="/api/v1/interviews/",
    method="POST",
    tool_name="hr_interview_schedule",
    permissions=["interview:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_interview_schedule_v1",
    description="Schedule a new interview for a candidate, optionally specifying round, type, and interviewers",
    request_model="InterviewCreate",
    response_model="InterviewResponse",
    rate_limit="30/minute",
    data_classification="L3",
    audit_level="detailed",
    tags=["hr", "interview", "schedule"],
    timeout=10.0,
)
async def schedule_interview(
    *,
    candidate_id: str,
    position_id: str | None = None,
    round_number: int = 1,
    interview_type: str = "technical",
    scheduled_at: str | None = None,
    duration_minutes: int = 60,
    location: str | None = None,
    interviewer_ids: list[str] | None = None,
    tenant_id: str = "default",
    user_id: str = "agent",
) -> dict[str, Any]:
    """
    Schedule a new interview.

    Creates an interview record linking a candidate to a position
    with specified scheduling details.

    Args:
        candidate_id: UUID of the candidate.
        position_id: UUID of the position (optional).
        round_number: Interview round number (default 1).
        interview_type: Type of interview (technical/behavioral/hr/final).
        scheduled_at: ISO 8601 datetime string for scheduled time.
        duration_minutes: Interview duration in minutes.
        location: Physical location or meeting link.
        interviewer_ids: List of interviewer user IDs.
        tenant_id: Tenant scope identifier.
        user_id: User creating the interview.

    Returns:
        Dict with created interview details.
    """
    from datetime import datetime

    from app.dependencies import get_db
    from app.schemas.interview import InterviewCreate
    from app.services.interview_service import InterviewService

    async for session in get_db():
        svc = InterviewService(session)
        create_data = InterviewCreate(
            candidate_id=UUID(candidate_id),
            position_id=UUID(position_id) if position_id else None,
            round_number=round_number,
            interview_type=interview_type,
            scheduled_at=datetime.fromisoformat(scheduled_at) if scheduled_at else None,
            duration_minutes=duration_minutes,
            location=location,
            interviewer_ids=interviewer_ids,
        )
        try:
            interview = await svc.create(
                data=create_data,
                tenant_id=tenant_id,
                user_id=user_id,
            )
            return {
                "status": "success",
                "interview_id": str(interview.id),
                "candidate_id": str(interview.candidate_id),
                "position_id": str(interview.position_id) if interview.position_id else None,
                "round_number": interview.round_number,
                "interview_type": interview.interview_type,
                "status": interview.status,
                "scheduled_at": str(interview.scheduled_at) if interview.scheduled_at else None,
                "duration_minutes": interview.duration_minutes,
                "interviewer_ids": interview.interviewer_ids,
            }
        except ValueError as exc:
            return {"error": str(exc), "candidate_id": candidate_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Interview Cancel — 取消面试
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_interview_cancel",
    name="HR Interview Cancel",
    endpoint="/api/v1/interviews/{interview_id}",
    method="DELETE",
    tool_name="hr_interview_cancel",
    permissions=["interview:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_interview_cancel_v1",
    description="Cancel an existing interview with an optional reason",
    request_model="InterviewCancelRequest",
    response_model="InterviewResponse",
    rate_limit="30/minute",
    data_classification="L3",
    audit_level="standard",
    tags=["hr", "interview", "cancel"],
    timeout=10.0,
)
async def cancel_interview(
    interview_id: str,
    tenant_id: str,
    *,
    reason: str | None = None,
) -> dict[str, Any]:
    """
    Cancel an existing interview.

    Only interviews in 'scheduled' or 'in_progress' status can be cancelled.

    Args:
        interview_id: UUID of the interview to cancel.
        tenant_id: Tenant scope identifier.
        reason: Optional cancellation reason.

    Returns:
        Dict with cancellation confirmation.
    """
    from app.dependencies import get_db
    from app.services.interview_service import InterviewService

    async for session in get_db():
        svc = InterviewService(session)
        try:
            interview = await svc.cancel(
                interview_id=UUID(interview_id),
                tenant_id=tenant_id,
                reason=reason,
            )
            return {
                "status": "success",
                "interview_id": str(interview.id),
                "previous_status": "cancelled",
                "cancelled_at": str(interview.cancelled_at) if interview.cancelled_at else None,
                "cancel_reason": interview.cancel_reason,
            }
        except ValueError as exc:
            return {"error": str(exc), "interview_id": interview_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Interview Feedback — 提交反馈
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_interview_feedback",
    name="HR Interview Feedback",
    endpoint="/api/v1/interviews/{interview_id}/feedback",
    method="POST",
    tool_name="hr_interview_feedback",
    permissions=["interview:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_interview_feedback_v1",
    description="Submit interview feedback with score, recommendation, and detailed notes",
    request_model="InterviewFeedbackCreate",
    response_model="InterviewResponse",
    rate_limit="30/minute",
    data_classification="L3",
    audit_level="detailed",
    tags=["hr", "interview", "feedback"],
    timeout=10.0,
)
async def submit_feedback(
    interview_id: str,
    tenant_id: str,
    *,
    interviewer_id: str,
    score: float,
    recommendation: str,
    strengths: str | None = None,
    weaknesses: str | None = None,
    comments: str | None = None,
    skill_ratings: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Submit interview feedback.

    Records an interviewer's evaluation including score (0-10),
    recommendation (strong_yes/yes/no/strong_no), strengths,
    weaknesses, and optional per-skill ratings.

    Args:
        interview_id: UUID of the interview.
        tenant_id: Tenant scope identifier.
        interviewer_id: ID of the interviewer submitting feedback.
        score: Score from 0 to 10.
        recommendation: strong_yes / yes / no / strong_no.
        strengths: Observed strengths (comma-separated text).
        weaknesses: Areas of concern (comma-separated text).
        comments: General comments.
        skill_ratings: Per-skill ratings dict.

    Returns:
        Dict with updated interview details.
    """
    from app.dependencies import get_db
    from app.schemas.interview import InterviewFeedbackCreate
    from app.services.interview_service import InterviewService

    async for session in get_db():
        svc = InterviewService(session)
        feedback_data = InterviewFeedbackCreate(
            score=score,
            recommendation=recommendation,
            strengths=strengths,
            weaknesses=weaknesses,
            comments=comments,
            skill_ratings=skill_ratings,
        )
        try:
            interview = await svc.submit_feedback(
                interview_id=UUID(interview_id),
                interviewer_id=interviewer_id,
                data=feedback_data,
                tenant_id=tenant_id,
            )
            return {
                "status": "success",
                "interview_id": str(interview.id),
                "overall_score": interview.overall_score,
                "recommendation": interview.recommendation,
                "status": interview.status,
            }
        except ValueError as exc:
            return {"error": str(exc), "interview_id": interview_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Interview Analyze — AI 分析
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_interview_analyze",
    name="HR Interview Analyze",
    endpoint="/api/v1/interviews/{interview_id}/analyze",
    method="POST",
    tool_name="hr_interview_analyze",
    permissions=["interview:read", "ai:use"],
    llm_model="gpt-4o-mini",
    fallback_model="gpt-3.5-turbo",
    prompt_version="v1",
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_interview_analyze_v1",
    description="AI-powered analysis of interview feedback: score breakdown, strengths, concerns, recommendation",
    request_model="InterviewAnalyzeRequest",
    response_model="InterviewAnalysisResponse",
    rate_limit="10/minute",
    data_classification="L3",
    audit_level="detailed",
    tags=["hr", "interview", "analyze", "ai"],
    timeout=30.0,
)
async def analyze_interview(
    interview_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Perform AI-powered analysis of interview feedback.

    Aggregates all interviewer feedback for an interview and generates
    a comprehensive analysis including score breakdown, strengths,
    concerns, hire recommendation, and improvement suggestions.

    Args:
        interview_id: UUID of the interview to analyze.
        tenant_id: Tenant scope identifier.

    Returns:
        Dict with structured analysis results.
    """
    from app.dependencies import get_db
    from app.services.interview_ai_service import InterviewAIService

    async for session in get_db():
        svc = InterviewAIService(session)
        try:
            result = await svc.analyze_feedback(
                interview_id=UUID(interview_id),
                tenant_id=tenant_id,
            )
            return {
                "status": "success",
                "interview_id": str(result.interview_id),
                "overall_score": result.overall_score,
                "score_breakdown": result.score_breakdown,
                "strengths": result.strengths,
                "concerns": result.concerns,
                "recommendation": result.recommendation,
                "recommendation_reason": result.recommendation_reason,
                "improvement_suggestions": result.improvement_suggestions,
                "candidate_fit_score": result.candidate_fit_score,
            }
        except ValueError as exc:
            return {"error": str(exc), "interview_id": interview_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Interview Workload — 查工作量
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_interview_workload",
    name="HR Interview Workload",
    endpoint="/api/v1/interviews/workload-stats",
    method="GET",
    tool_name="hr_interview_workload",
    permissions=["interview:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_interview_workload_v1",
    description="Query interviewer workload statistics: total interviews, pending feedback, average scores",
    request_model="WorkloadQueryRequest",
    response_model="InterviewerWorkload",
    rate_limit="30/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "interview", "workload"],
    timeout=10.0,
)
async def get_workload(
    tenant_id: str,
) -> dict[str, Any]:
    """
    Query per-interviewer workload statistics.

    Returns aggregated statistics for each interviewer in the tenant,
    including total interviews, pending/completed feedback counts,
    average scores, and upcoming interview counts.

    Args:
        tenant_id: Tenant scope identifier.

    Returns:
        Dict with list of interviewer workload statistics.
    """
    from app.dependencies import get_db
    from app.services.interview_service import InterviewService

    async for session in get_db():
        svc = InterviewService(session)
        stats = await svc.get_workload_stats(tenant_id=tenant_id)
        return {
            "status": "success",
            "interviewers": stats,
            "total_interviewers": len(stats),
        }

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Interview Reminder — 面试提醒 (骨架)
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_interview_reminder",
    name="HR Interview Reminder",
    endpoint="/api/v1/interviews/{interview_id}/reminder",
    method="POST",
    tool_name="hr_interview_reminder",
    permissions=["interview:read", "notification:send"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_interview_reminder_v1",
    description="Send interview reminder notifications to candidate and interviewers",
    request_model="InterviewReminderRequest",
    response_model="InterviewReminderResult",
    rate_limit="20/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "interview", "reminder", "notification"],
    timeout=15.0,
)
async def send_reminder(
    interview_id: str,
    tenant_id: str,
    *,
    reminder_type: str = "upcoming",
    channels: list[str] | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    """
    Send interview reminder notifications.

    Skeleton implementation — currently logs the reminder request
    but does not send actual notifications. To be wired to a
    notification service (email/SMS/in-app).

    Args:
        interview_id: UUID of the interview.
        tenant_id: Tenant scope identifier.
        reminder_type: Type of reminder (upcoming/reschedule/followup).
        channels: Notification channels (email/sms/in_app).
        message: Custom reminder message (optional).

    Returns:
        Dict with reminder status.
    """
    from app.dependencies import get_db
    from app.services.interview_service import InterviewService

    _channels = channels or ["email"]
    logger.info(
        "Reminder requested: interview=%s, type=%s, channels=%s",
        interview_id,
        reminder_type,
        _channels,
    )

    async for session in get_db():
        svc = InterviewService(session)
        interview = await svc.get_by_id(UUID(interview_id), tenant_id)
        if interview is None:
            return {"error": "Interview not found", "interview_id": interview_id}

        # Skeleton: log and return success
        # TODO: Wire to actual notification service
        recipient_count = len(interview.interviewer_ids or []) + 1  # interviewers + candidate

        return {
            "status": "success",
            "interview_id": str(interview.id),
            "reminder_type": reminder_type,
            "channels": _channels,
            "recipients": recipient_count,
            "message": message or f"Reminder: Interview scheduled at {interview.scheduled_at}",
            "note": "Skeleton implementation — no actual notifications sent",
        }

    return {"error": "Database session unavailable"}
