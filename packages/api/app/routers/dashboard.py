"""
Dashboard Router — Dashboard API endpoints.

GET /api/v1/dashboard/todos       — Pending todo items
GET /api/v1/dashboard/schedule    — Today's schedule
GET /api/v1/dashboard/metrics     — Quick metrics
GET /api/v1/dashboard/ai-insights — AI insights
"""

from fastapi import APIRouter, Request

from app.dependencies import CurrentUserDep, DbSession
from app.schemas.dashboard import (
    AiInsightsResponse,
    MetricsResponse,
    ScheduleResponse,
    TodoListResponse,
)
from app.services.dashboard_service import (
    get_ai_insights,
    get_metrics,
    get_schedule,
    get_todos,
)

router = APIRouter()


@router.get("/todos", response_model=TodoListResponse)
async def list_todos(
    user: CurrentUserDep,
    db: DbSession,
) -> TodoListResponse:
    """Get pending todo items for the current user."""
    return await get_todos(user.tenant_id, db)


@router.get("/schedule", response_model=ScheduleResponse)
async def list_schedule(
    user: CurrentUserDep,
    db: DbSession,
) -> ScheduleResponse:
    """Get today's schedule events."""
    return await get_schedule(user.tenant_id, db)


@router.get("/metrics", response_model=MetricsResponse)
async def list_metrics(
    user: CurrentUserDep,
    db: DbSession,
) -> MetricsResponse:
    """Get key recruitment metrics."""
    return await get_metrics(user.tenant_id, db)


@router.get("/ai-insights", response_model=AiInsightsResponse)
async def list_ai_insights(
    user: CurrentUserDep,
    db: DbSession,
) -> AiInsightsResponse:
    """Get AI-generated insights and recommendations."""
    return await get_ai_insights(user.tenant_id, db)
