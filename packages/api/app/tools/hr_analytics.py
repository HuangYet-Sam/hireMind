"""
HR Analytics Agent Tool.

Exposes analytics and reporting capabilities as Agent Tools
via the ``@AiCapability`` decorator.

Registered capabilities:
  - ``hr_analytics_query_funnel``       — Query funnel data
  - ``hr_analytics_query_trends``       — Query trends
  - ``hr_analytics_position_analytics`` — Position analytics
  - ``hr_analytics_channel_roi``        — Channel ROI
  - ``hr_analytics_generate_report``    — Generate report
  - ``hr_analytics_get_insights``       — Get AI insights
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.decorators.ai_capability import AiCapability

logger = logging.getLogger("hiremind.tools.hr_analytics")


# ---------------------------------------------------------------------------
# Tool: HR Analytics Query Funnel — 查询漏斗
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_analytics_query_funnel",
    name="HR Analytics Query Funnel",
    endpoint="/api/v1/analytics/funnel",
    method="GET",
    tool_name="hr_analytics_query_funnel",
    permissions=["analytics:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_analytics_query_funnel_v1",
    description="Query recruitment funnel data with conversion rates for all or a specific position",
    request_model="FunnelQuery",
    response_model="FunnelResponse",
    rate_limit="30/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "analytics", "funnel"],
    timeout=10.0,
)
async def query_funnel(
    tenant_id: str,
    *,
    position_id: str | None = None,
    period: str = "all",
) -> dict[str, Any]:
    """
    Query recruitment funnel data.

    Returns funnel stages (positions → resumes → matches → interviews →
    offers → hired) with counts, conversion rates, and cumulative rates.

    Args:
        tenant_id: Tenant scope identifier.
        position_id: Optional UUID filter for a specific position.
        period: Time period — daily/weekly/monthly/all.

    Returns:
        Dict with funnel analysis data.
    """
    from app.dependencies import get_db
    from app.services.dashboard_service import get_funnel

    async for session in get_db():
        try:
            result = await get_funnel(
                tenant_id=tenant_id,
                db=session,
                position_id=UUID(position_id) if position_id else None,
                period=period,
            )
            return {
                "status": "success",
                **result.model_dump(),
            }
        except Exception as exc:
            return {"error": str(exc)}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Analytics Query Trends — 查询趋势
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_analytics_query_trends",
    name="HR Analytics Query Trends",
    endpoint="/api/v1/analytics/trends",
    method="GET",
    tool_name="hr_analytics_query_trends",
    permissions=["analytics:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_analytics_query_trends_v1",
    description="Query recruitment time-series trends (resumes, matches, interviews, offers, hires)",
    request_model="TrendQuery",
    response_model="TrendResponse",
    rate_limit="30/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "analytics", "trends"],
    timeout=10.0,
)
async def query_trends(
    tenant_id: str,
    *,
    period: str = "daily",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """
    Query recruitment trends over time.

    Returns time-series data points with counts for resumes, matches,
    interviews, offers, and hires.

    Args:
        tenant_id: Tenant scope identifier.
        period: Grouping — daily/weekly/monthly.
        start_date: Optional start date (YYYY-MM-DD).
        end_date: Optional end date (YYYY-MM-DD).

    Returns:
        Dict with trend data.
    """
    from app.dependencies import get_db
    from app.services.dashboard_service import get_trends

    async for session in get_db():
        try:
            result = await get_trends(
                tenant_id=tenant_id,
                db=session,
                period=period,
                start_date=start_date,
                end_date=end_date,
            )
            return {
                "status": "success",
                **result.model_dump(),
            }
        except Exception as exc:
            return {"error": str(exc)}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Analytics Position Analytics — 岗位分析
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_analytics_position_analytics",
    name="HR Analytics Position Analytics",
    endpoint="/api/v1/analytics/positions/{position_id}/analytics",
    method="GET",
    tool_name="hr_analytics_position_analytics",
    permissions=["analytics:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_analytics_position_analytics_v1",
    description="Comprehensive analytics for a single position: funnel, match scores, time-to-hire, pass rates",
    request_model="PositionAnalyticsQuery",
    response_model="PositionAnalytics",
    rate_limit="30/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "analytics", "position"],
    timeout=15.0,
)
async def get_position_analytics(
    position_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Get comprehensive position analytics.

    Returns funnel data, average match score, time-to-hire,
    interview pass rate, and offer accept rate for a single position.

    Args:
        position_id: UUID of the position.
        tenant_id: Tenant scope identifier.

    Returns:
        Dict with position analytics data.
    """
    from app.dependencies import get_db
    from app.services.analytics_service import AnalyticsService

    async for session in get_db():
        svc = AnalyticsService(session)
        try:
            result = await svc.get_position_analytics(
                position_id=UUID(position_id),
                tenant_id=tenant_id,
            )
            return {
                "status": "success",
                **result,
            }
        except Exception as exc:
            return {"error": str(exc), "position_id": position_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Analytics Channel ROI — 渠道ROI
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_analytics_channel_roi",
    name="HR Analytics Channel ROI",
    endpoint="/api/v1/analytics/channel-roi",
    method="GET",
    tool_name="hr_analytics_channel_roi",
    permissions=["analytics:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_analytics_channel_roi_v1",
    description="Channel ROI analysis: cost per hire, conversion rates, and quality indicators by recruitment source",
    request_model="ChannelROIQuery",
    response_model="ChannelROIResponse",
    rate_limit="30/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "analytics", "channel", "roi"],
    timeout=10.0,
)
async def get_channel_roi(
    tenant_id: str,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """
    Get channel ROI analysis.

    Returns per-channel metrics including resume count, interview rate,
    offer rate, cost, cost per hire, and ROI score.

    Args:
        tenant_id: Tenant scope identifier.
        date_from: Optional start date (YYYY-MM-DD).
        date_to: Optional end date (YYYY-MM-DD).

    Returns:
        Dict with channel ROI data.
    """
    from app.dependencies import get_db
    from app.services.analytics_service import AnalyticsService

    async for session in get_db():
        svc = AnalyticsService(session)
        try:
            result = await svc.get_channel_roi_enhanced(
                tenant_id=tenant_id,
                date_from=date_from,
                date_to=date_to,
            )
            return {
                "status": "success",
                **result,
            }
        except Exception as exc:
            return {"error": str(exc)}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Analytics Generate Report — 生成报表
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_analytics_generate_report",
    name="HR Analytics Generate Report",
    endpoint="/api/v1/analytics/reports/export",
    method="POST",
    tool_name="hr_analytics_generate_report",
    permissions=["analytics:read", "report:generate"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_analytics_generate_report_v1",
    description="Generate recruitment analytics report (Excel or PDF) for funnel, trends, positions, channels, or full summary",
    request_model="ReportExportRequest",
    response_model="ReportExportResponse",
    rate_limit="10/minute",
    data_classification="L2",
    audit_level="detailed",
    tags=["hr", "analytics", "report", "export"],
    timeout=30.0,
)
async def generate_report(
    tenant_id: str,
    *,
    report_format: str = "excel",
    report_type: str = "full",
    date_from: str | None = None,
    date_to: str | None = None,
    position_id: str | None = None,
) -> dict[str, Any]:
    """
    Generate a recruitment analytics report.

    Supports Excel and PDF output formats with multiple report types.

    Args:
        tenant_id: Tenant scope identifier.
        report_format: Output format — excel or pdf.
        report_type: Report type — funnel/trend/position/channel/full.
        date_from: Optional start date (YYYY-MM-DD).
        date_to: Optional end date (YYYY-MM-DD).
        position_id: Optional position UUID filter.

    Returns:
        Dict with report_id and file_path or data.
    """
    from app.dependencies import get_db
    from app.services.report_service import ReportService

    filters = {}
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    if position_id:
        filters["position_id"] = position_id

    async for session in get_db():
        svc = ReportService(session)
        try:
            if report_format == "pdf":
                result = await svc.generate_pdf_report(
                    report_type=report_type,
                    filters=filters,
                    tenant_id=tenant_id,
                )
            else:
                result = await svc.generate_excel_report(
                    report_type=report_type,
                    filters=filters,
                    tenant_id=tenant_id,
                )
            return {
                "status": "success",
                **result,
            }
        except Exception as exc:
            return {"error": str(exc)}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Analytics Get Insights — 获取AI洞察
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_analytics_get_insights",
    name="HR Analytics Get Insights",
    endpoint="/api/v1/analytics/insights/scan",
    method="POST",
    tool_name="hr_analytics_get_insights",
    permissions=["analytics:read", "ai:use"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_analytics_get_insights_v1",
    description="Trigger AI insight scan: checks 8 trigger conditions and returns actionable recruitment insights",
    request_model="InsightScanRequest",
    response_model="InsightScanResponse",
    rate_limit="10/minute",
    data_classification="L2",
    audit_level="detailed",
    tags=["hr", "analytics", "ai", "insights"],
    timeout=30.0,
)
async def get_insights(
    tenant_id: str,
    *,
    include_proactive: bool = True,
) -> dict[str, Any]:
    """
    Trigger AI insight scan and return generated insights.

    Runs all 8 trigger condition checks and optionally generates
    proactive AI insights based on current data trends.

    Args:
        tenant_id: Tenant scope identifier.
        include_proactive: Whether to include proactive AI insights.

    Returns:
        Dict with triggered and proactive insights.
    """
    from app.dependencies import get_db
    from app.services.insight_engine import InsightEngine

    async for session in get_db():
        engine = InsightEngine(session)
        try:
            # Run trigger-based scan
            triggered = await engine.scan_and_generate(tenant_id)

            # Optionally generate proactive insights
            proactive = []
            if include_proactive:
                proactive = await engine.generate_proactive_insights(tenant_id)

            return {
                "status": "success",
                "triggered_insights": triggered,
                "proactive_insights": proactive,
                "total_insights": len(triggered) + len(proactive),
            }
        except Exception as exc:
            return {"error": str(exc)}

    return {"error": "Database session unavailable"}
