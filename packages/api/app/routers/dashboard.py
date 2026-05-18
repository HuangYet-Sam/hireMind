"""
Dashboard Router — Dashboard API endpoints.

Original endpoints:
  GET /api/v1/dashboard/todos       — Pending todo items
  GET /api/v1/dashboard/schedule    — Today's schedule
  GET /api/v1/dashboard/metrics     — Quick metrics
  GET /api/v1/dashboard/ai-insights — AI insights

M7 additions:
  GET  /api/v1/dashboard/metrics          — Core metrics (quick)
  GET  /api/v1/dashboard/funnel           — Recruitment funnel
  GET  /api/v1/dashboard/todos            — Enhanced todo list
  GET  /api/v1/dashboard/trends           — Trend data
  GET  /api/v1/dashboard/sources          — Source distribution
  GET  /api/v1/dashboard/insights         — AI insights (M7)
  POST /api/v1/dashboard/daily-report     — Generate daily report
  POST /api/v1/dashboard/weekly-report    — Generate weekly report
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.dependencies import CurrentUserDep, DbSession
from app.schemas.dashboard import (
    AiInsightsResponse,
    DashboardMetrics,
    FunnelResponse,
    MetricsResponse,
    ReportGenerateRequest,
    ReportResponse,
    ScheduleResponse,
    SourceResponse,
    TodoListResponse,
    TodoResponse,
    TrendResponse,
    AIInsightsResponse,
)
from app.services.dashboard_service import (
    get_ai_insights,
    get_dashboard_metrics,
    get_dashboard_todos,
    get_funnel,
    get_metrics,
    get_schedule,
    get_source_distribution,
    get_todos,
    get_trends,
)
from app.services.dashboard_ai_service import DashboardAIService

router = APIRouter()


# ── Original Endpoints ─────────────────────────────────────────

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


# ── M7: Core Metrics (quick) ──────────────────────────────────

@router.get("/metrics/quick", response_model=DashboardMetrics)
async def get_quick_metrics(
    user: CurrentUserDep,
    db: DbSession,
) -> DashboardMetrics:
    """Get core dashboard metrics for the header cards."""
    return await get_dashboard_metrics(user.tenant_id, db)


# ── M7: Recruitment Funnel ────────────────────────────────────

@router.get("/funnel", response_model=FunnelResponse)
async def get_recruitment_funnel(
    user: CurrentUserDep,
    db: DbSession,
    position_id: UUID | None = Query(None, description="Filter by position ID"),
    period: str = Query("all", description="Time period: daily/weekly/monthly/all"),
) -> FunnelResponse:
    """
    Get recruitment funnel data with conversion rates.

    Stages: positions → resumes → matches → interviews → offers → hired
    """
    return await get_funnel(user.tenant_id, db, position_id, period)


# ── M7: Enhanced Todos ────────────────────────────────────────

@router.get("/todos/enhanced", response_model=TodoResponse)
async def list_enhanced_todos(
    user: CurrentUserDep,
    db: DbSession,
) -> TodoResponse:
    """
    Get enhanced todo list with categories and urgency levels.

    Categories: resume_pending, interview_feedback, offer_followup,
    approval_pending, position_overdue.
    """
    return await get_dashboard_todos(user.tenant_id, user.user_id, db)


# ── M7: Trends ────────────────────────────────────────────────

@router.get("/trends", response_model=TrendResponse)
async def get_trend_data(
    user: CurrentUserDep,
    db: DbSession,
    period: str = Query("daily", description="Grouping: daily/weekly/monthly"),
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
) -> TrendResponse:
    """
    Get time-series recruitment trend data.

    Returns counts for resumes, matches, interviews, offers, and hires
    grouped by day, week, or month.
    """
    return await get_trends(user.tenant_id, db, period, start_date, end_date)


# ── M7: Source Distribution ───────────────────────────────────

@router.get("/sources", response_model=SourceResponse)
async def get_sources(
    user: CurrentUserDep,
    db: DbSession,
) -> SourceResponse:
    """
    Get candidate source distribution with effectiveness metrics.

    Returns per-source stats: count, interview rate, offer rate.
    """
    return await get_source_distribution(user.tenant_id, db)


# ── M7: AI Insights ──────────────────────────────────────────

@router.get("/insights", response_model=AIInsightsResponse)
async def get_ai_dashboard_insights(
    user: CurrentUserDep,
    db: DbSession,
) -> AIInsightsResponse:
    """
    Get AI-generated dashboard insights.

    Analyzes current recruitment trends and produces:
    - Trend insights
    - Risk alerts
    - Opportunities
    - Action recommendations
    """
    svc = DashboardAIService(db)
    return await svc.generate_insights(user.tenant_id)


# ── M7: Daily Report ─────────────────────────────────────────

@router.post("/daily-report", response_model=ReportResponse)
async def generate_daily_report(
    user: CurrentUserDep,
    db: DbSession,
    body: ReportGenerateRequest | None = None,
) -> ReportResponse:
    """
    Generate a daily recruitment report.

    Includes day's data summary, key metric changes, highlights,
    concerns, and action recommendations.
    """
    svc = DashboardAIService(db)
    target_date = None
    if body and body.date:
        target_date = date.fromisoformat(body.date)
    return await svc.generate_daily_report(user.tenant_id, target_date)


# ── M7: Weekly Report ────────────────────────────────────────

@router.post("/weekly-report", response_model=ReportResponse)
async def generate_weekly_report(
    user: CurrentUserDep,
    db: DbSession,
) -> ReportResponse:
    """
    Generate a weekly recruitment report.

    Includes weekly data summary, trend analysis, comparison with
    previous week, and next week predictions.
    """
    svc = DashboardAIService(db)
    return await svc.generate_weekly_report(user.tenant_id)
