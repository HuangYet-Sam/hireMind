"""
Dashboard Pydantic Schemas.
"""

from datetime import datetime
from pydantic import BaseModel, Field


# ── Todos ──────────────────────────────────────────────────────

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


# ── Schedule ───────────────────────────────────────────────────

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


# ── Metrics ────────────────────────────────────────────────────

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


# ── AI Insights ────────────────────────────────────────────────

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
