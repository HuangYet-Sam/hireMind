"""
Analytics Router.

Recruitment analytics, dashboards, and reporting endpoints.
"""

from datetime import date

from fastapi import APIRouter, Query

from app.dependencies import CurrentUserDep, DbSession
from app.services.analytics_service import AnalyticsService

router = APIRouter()


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
