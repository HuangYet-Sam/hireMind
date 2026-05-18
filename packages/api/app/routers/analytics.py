"""
Analytics Router.

Recruitment analytics, dashboards, and reporting endpoints.

Original endpoints:
  GET /api/v1/analytics/dashboard          — Recruitment dashboard
  GET /api/v1/analytics/pipeline           — Pipeline funnel
  GET /api/v1/analytics/time-to-hire       — Time-to-hire metrics
  GET /api/v1/analytics/source-effectiveness — Source effectiveness
  GET /api/v1/analytics/department-summary — Department summary

M7 additions:
  GET /api/v1/analytics/funnel              — Funnel analysis
  GET /api/v1/analytics/trends              — Trends
  GET /api/v1/analytics/source-distribution — Source distribution
  GET /api/v1/analytics/channel-roi         — Channel ROI
  GET /api/v1/analytics/position-performance — Position performance
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query

from app.dependencies import CurrentUserDep, DbSession
from app.schemas.dashboard import (
    FunnelResponse,
    SourceResponse,
    TrendResponse,
)
from app.services.analytics_service import AnalyticsService
from app.services.dashboard_service import (
    get_funnel,
    get_source_distribution,
    get_trends,
)

router = APIRouter()


# ── Original Endpoints ─────────────────────────────────────────

@router.get("/dashboard", summary="Recruitment dashboard")
async def get_dashboard(
    db: DbSession,
    current_user: CurrentUserDep,
    department_id: str | None = Query(None),
):
    """
    Return aggregate recruitment dashboard data.

    Includes: open positions count, candidates in pipeline, interviews this week,
    offers pending, time-to-hire metrics.
    """
    svc = AnalyticsService(db)
    return await svc.get_dashboard(current_user.tenant_id, department_id)


@router.get("/pipeline", summary="Pipeline funnel")
async def get_pipeline_funnel(
    db: DbSession,
    current_user: CurrentUserDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
):
    """Return the hiring pipeline funnel (applied -> screened -> interviewed -> offered -> hired)."""
    svc = AnalyticsService(db)
    return await svc.get_pipeline_funnel(current_user.tenant_id, date_from, date_to)


@router.get("/time-to-hire", summary="Time-to-hire metrics")
async def get_time_to_hire(
    db: DbSession,
    current_user: CurrentUserDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    group_by: str = Query("month", description="Group by: day/week/month"),
):
    """Return average time-to-hire metrics grouped by period."""
    svc = AnalyticsService(db)
    return await svc.get_time_to_hire(current_user.tenant_id, date_from, date_to, group_by)


@router.get("/source-effectiveness", summary="Source effectiveness")
async def get_source_effectiveness(
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Return candidate source effectiveness comparison (referral, job board, social, etc.)."""
    svc = AnalyticsService(db)
    return await svc.get_source_effectiveness(current_user.tenant_id)


@router.get("/department-summary", summary="Department summary")
async def get_department_summary(
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Return per-department recruitment metrics."""
    svc = AnalyticsService(db)
    return await svc.get_department_summary(current_user.tenant_id)


# ══════════════════════════════════════════════════════════════════
# M7 Enhancement Endpoints
# ══════════════════════════════════════════════════════════════════


# ── M7: Funnel Analysis ───────────────────────────────────────

@router.get("/funnel", response_model=FunnelResponse, summary="Funnel analysis")
async def get_analytics_funnel(
    db: DbSession,
    current_user: CurrentUserDep,
    position_id: UUID | None = Query(None, description="Filter by position"),
    period: str = Query("all", description="Time period: daily/weekly/monthly/all"),
) -> FunnelResponse:
    """
    Recruitment funnel analysis with conversion rates.

    Stages: positions → resumes → matches → interviews → offers → hired
    Returns per-stage counts, conversion rates, and cumulative rates.
    """
    return await get_funnel(current_user.tenant_id, db, position_id, period)


# ── M7: Trends ────────────────────────────────────────────────

@router.get("/trends", response_model=TrendResponse, summary="Recruitment trends")
async def get_analytics_trends(
    db: DbSession,
    current_user: CurrentUserDep,
    period: str = Query("daily", description="Grouping: daily/weekly/monthly"),
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
) -> TrendResponse:
    """
    Time-series recruitment trend data.

    Returns data points with counts for resumes, matches, interviews,
    offers, and hires grouped by the specified period.
    """
    return await get_trends(current_user.tenant_id, db, period, start_date, end_date)


# ── M7: Source Distribution ───────────────────────────────────

@router.get("/source-distribution", response_model=SourceResponse, summary="Source distribution")
async def get_analytics_source_distribution(
    db: DbSession,
    current_user: CurrentUserDep,
) -> SourceResponse:
    """
    Candidate source distribution with effectiveness metrics.

    Returns per-source stats: count, interview rate, offer rate, and cost.
    """
    return await get_source_distribution(current_user.tenant_id, db)


# ── M7: Channel ROI ───────────────────────────────────────────

@router.get("/channel-roi", summary="Channel ROI analysis")
async def get_channel_roi(
    db: DbSession,
    current_user: CurrentUserDep,
):
    """
    Channel ROI analysis.

    Compares recruitment channels by:
    - Cost per hire
    - Time to hire per channel
    - Conversion rates
    - Quality of hire indicators

    Returns a list of channel ROI summaries.
    """
    svc = AnalyticsService(db)

    # Get source effectiveness data
    source_data = await svc.get_source_effectiveness(current_user.tenant_id)

    # Enhance with ROI calculations
    roi_data = []
    for source in source_data:
        total = source.get("total", 0)
        hired = source.get("hired", 0)
        conversion_rate = source.get("conversion_rate", 0.0)

        # Placeholder cost per candidate by channel
        # In production, this would come from a budget/spend table
        cost_per_candidate = {
            "referral": 500,
            "boss": 200,
            "linkedin": 1500,
            "job_board": 300,
            "headhunter": 5000,
            "email": 50,
            "upload": 0,
            "social": 200,
        }.get(source.get("source", ""), 100)

        cost_per_hire = (cost_per_candidate * total / hired) if hired > 0 else None

        roi_data.append({
            "source": source.get("source", "unknown"),
            "total_candidates": total,
            "hired": hired,
            "conversion_rate": conversion_rate,
            "estimated_cost_per_candidate": cost_per_candidate,
            "total_estimated_cost": cost_per_candidate * total,
            "cost_per_hire": cost_per_hire,
            "roi_score": round(
                (hired * 10000) / (cost_per_candidate * total) if total > 0 and cost_per_candidate > 0 else 0,
                2,
            ),
        })

    # Sort by ROI score descending
    roi_data.sort(key=lambda x: x["roi_score"], reverse=True)
    return {"channels": roi_data}


# ── M7: Position Performance ──────────────────────────────────

@router.get("/position-performance", summary="Position performance")
async def get_position_performance(
    db: DbSession,
    current_user: CurrentUserDep,
    department_id: UUID | None = Query(None, description="Filter by department"),
    status: str | None = Query(None, description="Filter by status"),
):
    """
    Position performance analysis.

    Returns per-position metrics:
    - Days open
    - Candidates in pipeline
    - Interview count
    - Offer count
    - Hired count
    - Fill rate
    - Average match score
    """
    svc = AnalyticsService(db)

    # Build position performance from analytics service
    dashboard_data = await svc.get_dashboard(current_user.tenant_id, department_id)

    # Get detailed position data
    from sqlalchemy import func, select
    from app.models.candidate import Candidate
    from app.models.interview import Interview
    from app.models.offer import Offer
    from app.models.position import Position
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    # Query positions with aggregated metrics
    pos_query = select(Position).where(
        Position.tenant_id == current_user.tenant_id,
    )
    if status:
        pos_query = pos_query.where(Position.status == status)
    if department_id:
        pos_query = pos_query.where(Position.department_id == department_id)

    pos_result = await db.execute(
        pos_query.order_by(Position.created_at.desc()).limit(100)
    )
    positions = pos_result.scalars().all()

    performance_data = []
    for pos in positions:
        # Candidates count
        cand_count = await db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.position_id == pos.id,
                Candidate.status == "active",
            )
        ) or 0

        # Interview count
        iv_count = await db.scalar(
            select(func.count()).select_from(Interview).where(
                Interview.position_id == pos.id,
            )
        ) or 0

        # Offer count
        off_count = await db.scalar(
            select(func.count()).select_from(Offer).where(
                Offer.position_id == pos.id,
            )
        ) or 0

        # Hired count
        hired_count = await db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.position_id == pos.id,
                Candidate.stage == "hired",
            )
        ) or 0

        # Days open
        created = pos.created_at
        if created:
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            days_open = (now - created).days
        else:
            days_open = 0

        # Fill rate
        fill_rate = round(hired_count / pos.headcount * 100, 1) if pos.headcount > 0 else 0.0

        performance_data.append({
            "position_id": str(pos.id),
            "title": pos.title,
            "status": pos.status,
            "department": pos.department.name if pos.department else None,
            "headcount": pos.headcount,
            "filled_count": pos.filled_count,
            "days_open": days_open,
            "candidates": cand_count,
            "interviews": iv_count,
            "offers": off_count,
            "hired": hired_count,
            "fill_rate": fill_rate,
            "priority": pos.priority,
        })

    # Sort by fill rate ascending (most urgent first), then days open descending
    performance_data.sort(
        key=lambda x: (x["fill_rate"], -x["days_open"])
    )

    return {"positions": performance_data}
