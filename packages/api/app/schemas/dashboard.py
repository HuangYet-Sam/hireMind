"""
Dashboard Pydantic Schemas.

Includes M7 Dashboard schemas: funnel, todos, trends, sources,
metrics, AI insights, and report generation.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Todos (original) ───────────────────────────────────────────

class TodoItem(BaseModel):
    """A single todo item."""

    id: str
    title: str
    description: str | None = None
    due_date: datetime | None = None
    priority: str = "medium"  # low / medium / high / urgent
    status: str = "pending"   # pending / in_progress / completed
    related_type: str | None = None   # candidate / position / interview / offer
    related_id: str | None = None


class TodoListResponse(BaseModel):
    """Response for GET /dashboard/todos."""

    items: list[TodoItem]
    total: int


# ── Schedule (original) ────────────────────────────────────────

class ScheduleEvent(BaseModel):
    """A single schedule event."""

    id: str
    title: str
    start_time: datetime
    end_time: datetime | None = None
    type: str = "interview"  # interview / meeting / deadline / reminder
    location: str | None = None
    candidate_name: str | None = None
    position_title: str | None = None
    status: str = "scheduled"  # scheduled / completed / cancelled


class ScheduleResponse(BaseModel):
    """Response for GET /dashboard/schedule."""

    date: str
    events: list[ScheduleEvent]
    total: int


# ── Metrics (original) ─────────────────────────────────────────

class MetricItem(BaseModel):
    """A single metric card."""

    key: str
    label: str
    value: int | float | str
    unit: str | None = None
    trend: str | None = None     # up / down / flat
    trend_value: float | None = None
    period: str | None = None    # e.g. "vs last week"


class MetricsResponse(BaseModel):
    """Response for GET /dashboard/metrics."""

    metrics: list[MetricItem]


# ── AI Insights (original) ─────────────────────────────────────

class AiInsight(BaseModel):
    """A single AI-generated insight."""

    id: str
    type: str          # recommendation / alert / summary / suggestion
    title: str
    content: str
    priority: str = "medium"  # low / medium / high
    created_at: datetime | None = None
    action_label: str | None = None   # e.g. "查看候选人"
    action_link: str | None = None    # e.g. "/hr/candidates/xxx"


class AiInsightsResponse(BaseModel):
    """Response for GET /dashboard/ai-insights."""

    insights: list[AiInsight]
    total: int


# ── M7: Recruitment Funnel ─────────────────────────────────────

class FunnelStage(BaseModel):
    """漏斗阶段"""

    stage: str  # position/resume/match/interview/offer/hired
    label: str  # 显示名
    count: int
    conversion_rate: float | None  # 相对上一阶段转化率
    cumulative_rate: float | None  # 相对第一阶段总转化率


class FunnelResponse(BaseModel):
    """招聘漏斗"""

    position_id: UUID | None  # None=全局
    stages: list[FunnelStage]
    period: str  # daily/weekly/monthly/all
    generated_at: datetime


# ── M7: Todo (enhanced for dashboard) ──────────────────────────

class DashboardTodoItem(BaseModel):
    """待办事项"""

    id: str
    type: str  # resume_pending/interview_feedback/offer_followup/approval_pending/position_overdue
    title: str
    description: str
    urgency: str  # urgent/high/medium/low
    entity_id: UUID | None
    entity_type: str | None
    due_at: datetime | None
    created_at: datetime


class TodoResponse(BaseModel):
    """待办清单"""

    items: list[DashboardTodoItem]
    total_count: int
    urgent_count: int


# ── M7: Trends ─────────────────────────────────────────────────

class TrendDataPoint(BaseModel):
    """趋势数据点"""

    date: str  # YYYY-MM-DD or YYYY-WXX
    resumes: int
    matches: int
    interviews: int
    offers: int
    hires: int


class TrendResponse(BaseModel):
    """趋势数据"""

    period: str  # daily/weekly/monthly
    data_points: list[TrendDataPoint]
    start_date: str
    end_date: str


# ── M7: Source Distribution ────────────────────────────────────

class SourceDistribution(BaseModel):
    """来源分布"""

    source: str
    count: int
    interview_rate: float
    offer_rate: float
    cost: float | None


class SourceResponse(BaseModel):
    """来源分布响应"""

    sources: list[SourceDistribution]
    total_count: int


# ── M7: Dashboard Metrics (quick) ──────────────────────────────

class DashboardMetrics(BaseModel):
    """核心指标"""

    active_positions: int
    total_candidates: int
    interviews_this_week: int
    pending_offers: int
    resumes_pending: int
    overdue_positions: int


# ── M7: AI Insights (enhanced for M7) ──────────────────────────

class AIInsight(BaseModel):
    """AI洞察"""

    id: str
    category: str  # trend/risk/opportunity/recommendation
    title: str
    content: str
    confidence: float
    action_suggestion: str | None
    created_at: datetime


class AIInsightsResponse(BaseModel):
    """AI洞察响应"""

    insights: list[AIInsight]
    generated_at: datetime


# ── M7: Reports ────────────────────────────────────────────────

class ReportGenerateRequest(BaseModel):
    """报告生成请求"""

    report_type: str  # daily/weekly
    date: str | None  # 报告日期 YYYY-MM-DD


class ReportResponse(BaseModel):
    """报告响应"""

    report_type: str
    title: str
    period: str
    summary: str
    metrics: dict
    highlights: list[str]
    concerns: list[str]
    recommendations: list[str]
    generated_at: datetime
