"""
Dashboard Service — Business logic for dashboard endpoints.

Queries real data from the database via SQLAlchemy async.
Returns empty / zero values when tables are empty — no mock data.
"""

from datetime import date, datetime, timedelta, timezone
import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_task import AiTask, TaskStatus
from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.offer import Offer
from app.models.position import Position
from app.schemas.dashboard import (
    AiInsight,
    AiInsightsResponse,
    MetricItem,
    MetricsResponse,
    ScheduleEvent,
    ScheduleResponse,
    TodoItem,
    TodoListResponse,
)


# ── Helpers ──────────────────────────────────────────────────────

def _week_bounds(dt: datetime) -> tuple[datetime, datetime]:
    """Return (monday 00:00, sunday 23:59:59.999999) for the ISO week of *dt*."""
    monday = dt - timedelta(days=dt.weekday())
    week_start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7) - timedelta(microseconds=1)
    return week_start, week_end


def _compute_trend(current: int | float, previous: int | float) -> tuple[str | None, float | None]:
    """Return (trend, trend_value) comparing current vs previous."""
    if previous == 0:
        if current > 0:
            return "up", 100.0
        return None, None
    pct = round((current - previous) / abs(previous) * 100, 1)
    if pct > 0:
        return "up", pct
    elif pct < 0:
        return "down", pct
    return "flat", 0.0


# ── GET /dashboard/todos ─────────────────────────────────────────

async def get_todos(tenant_id: str, db: AsyncSession) -> TodoListResponse:
    """
    Build a unified todo list from real database records:
      - Open positions
      - Interviews scheduled within the next 3 days
      - Pending offers
    """
    items: list[TodoItem] = []
    now = datetime.now(timezone.utc)

    # 1) Open positions (may need follow-up)
    open_pos_result = await db.execute(
        select(Position).where(
            Position.tenant_id == tenant_id,
            Position.status == "open",
        ).order_by(Position.created_at.desc())
    )
    open_positions = open_pos_result.scalars().all()
    for pos in open_positions:
        items.append(TodoItem(
            id=f"todo-position-{pos.id}",
            title=f"招聘中：{pos.title}",
            description=f"职位 [{pos.title}] 正在招聘中，待跟进候选人",
            due_date=None,
            priority="high" if pos.priority == "urgent" else "medium",
            status="pending",
            related_type="position",
            related_id=str(pos.id),
        ))

    # 2) Interviews scheduled in the next 3 days
    three_days_later = now + timedelta(days=3)
    upcoming_interviews = await db.execute(
        select(Interview).where(
            Interview.tenant_id == tenant_id,
            Interview.status == "scheduled",
            Interview.scheduled_at >= now,
            Interview.scheduled_at <= three_days_later,
        ).order_by(Interview.scheduled_at.asc())
    )
    interviews = upcoming_interviews.scalars().all()
    for iv in interviews:
        candidate_name = iv.candidate.name if iv.candidate else "未知候选人"
        position_title = iv.position.title if iv.position else "未知职位"
        days_until = (iv.scheduled_at - now).days if iv.scheduled_at else 0
        items.append(TodoItem(
            id=f"todo-interview-{iv.id}",
            title=f"即将面试：{candidate_name}",
            description=f"候选人 {candidate_name} 的「{position_title}」面试将于 "
                        f"{days_until} 天内进行",
            due_date=iv.scheduled_at,
            priority="high",
            status="pending",
            related_type="interview",
            related_id=str(iv.id),
        ))

    # 3) Pending offers (status 'pending_approval' or 'sent')
    pending_offers = await db.execute(
        select(Offer).where(
            Offer.tenant_id == tenant_id,
            Offer.status.in_(["pending_approval", "sent"]),
        ).order_by(Offer.created_at.desc())
    )
    offers = pending_offers.scalars().all()
    for offer in offers:
        candidate_name = offer.candidate.name if offer.candidate else "未知候选人"
        position_title = offer.position.title if offer.position else "未知职位"
        items.append(TodoItem(
            id=f"todo-offer-{offer.id}",
            title=f"Offer 待处理：{candidate_name}",
            description=f"候选人 {candidate_name} 的「{position_title}」Offer 待跟进",
            due_date=offer.expiry_date,
            priority="medium",
            status="pending",
            related_type="offer",
            related_id=str(offer.id),
        ))

    # Sort: highest priority first, then earliest due_date
    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    items.sort(key=lambda t: (priority_order.get(t.priority, 2), t.due_date or datetime.max.replace(tzinfo=timezone.utc)))

    return TodoListResponse(items=items, total=len(items))


# ── GET /dashboard/schedule ──────────────────────────────────────

async def get_schedule(tenant_id: str, db: AsyncSession) -> ScheduleResponse:
    """
    Return today's interview schedule from real data.
    If no interviews today, return events=[] (no placeholder).
    """
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)

    events: list[ScheduleEvent] = []

    result = await db.execute(
        select(Interview).where(
            Interview.tenant_id == tenant_id,
            Interview.status == "scheduled",
            Interview.scheduled_at >= today_start,
            Interview.scheduled_at <= today_end,
        ).order_by(Interview.scheduled_at.asc()).limit(50)
    )
    interviews = result.scalars().all()

    for iv in interviews:
        scheduled = iv.scheduled_at or datetime.now(timezone.utc)
        end_time = scheduled + timedelta(minutes=iv.duration_minutes or 60)
        candidate_name = iv.candidate.name if iv.candidate else None
        position_title = iv.position.title if iv.position else None

        events.append(ScheduleEvent(
            id=str(iv.id),
            title=f"面试：{candidate_name or '候选人'} - {position_title or '职位'}",
            start_time=scheduled,
            end_time=end_time,
            type="interview",
            location=iv.location or "线上",
            candidate_name=candidate_name,
            position_title=position_title,
            status="scheduled",
        ))

    return ScheduleResponse(
        date=today.isoformat(),
        events=events,
        total=len(events),
    )


# ── GET /dashboard/metrics ───────────────────────────────────────

async def get_metrics(tenant_id: str, db: AsyncSession) -> MetricsResponse:
    """
    Aggregate real recruitment metrics from the database.
    Computes week-over-week trends where applicable.
    """
    now = datetime.now(timezone.utc)
    this_week_start, this_week_end = _week_bounds(now)
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start - timedelta(microseconds=1)

    # ── Open positions ────────────────────────────────────────────
    open_pos_count = await db.scalar(
        select(func.count()).select_from(Position).where(
            Position.tenant_id == tenant_id,
            Position.status == "open",
        )
    ) or 0

    last_week_open_pos = await db.scalar(
        select(func.count()).select_from(Position).where(
            Position.tenant_id == tenant_id,
            Position.status == "open",
            Position.created_at <= last_week_end,
        )
    ) or 0

    trend_pos, trend_pos_val = _compute_trend(open_pos_count, last_week_open_pos)

    # ── Active candidates (new / screening / interview) ───────────
    active_candidates_count = await db.scalar(
        select(func.count()).select_from(Candidate).where(
            Candidate.tenant_id == tenant_id,
            Candidate.stage.in_(["applied", "screened", "interviewed"]),
        )
    ) or 0

    # Candidates whose stage was active before last week ended
    last_week_active_candidates = await db.scalar(
        select(func.count()).select_from(Candidate).where(
            Candidate.tenant_id == tenant_id,
            Candidate.stage.in_(["applied", "screened", "interviewed"]),
            Candidate.created_at <= last_week_end,
        )
    ) or 0

    trend_cand, trend_cand_val = _compute_trend(active_candidates_count, last_week_active_candidates)

    # ── Interviews this week ──────────────────────────────────────
    interviews_this_week = await db.scalar(
        select(func.count()).select_from(Interview).where(
            Interview.tenant_id == tenant_id,
            Interview.scheduled_at >= this_week_start,
            Interview.scheduled_at <= this_week_end,
        )
    ) or 0

    interviews_last_week = await db.scalar(
        select(func.count()).select_from(Interview).where(
            Interview.tenant_id == tenant_id,
            Interview.scheduled_at >= last_week_start,
            Interview.scheduled_at <= last_week_end,
        )
    ) or 0

    trend_iv, trend_iv_val = _compute_trend(interviews_this_week, interviews_last_week)

    # ── Pending offers ────────────────────────────────────────────
    offers_pending = await db.scalar(
        select(func.count()).select_from(Offer).where(
            Offer.tenant_id == tenant_id,
            Offer.status.in_(["pending_approval", "sent"]),
        )
    ) or 0

    last_week_offers_pending = await db.scalar(
        select(func.count()).select_from(Offer).where(
            Offer.tenant_id == tenant_id,
            Offer.status.in_(["pending_approval", "sent"]),
            Offer.created_at <= last_week_end,
        )
    ) or 0

    trend_offer, trend_offer_val = _compute_trend(offers_pending, last_week_offers_pending)

    # ── Average time-to-hire (days from candidate created_at to offer accepted) ─
    # We look at offers with status 'accepted' and their candidates
    avg_tth_result = await db.execute(
        select(
            func.avg(
                func.extract("epoch", Offer.updated_at - Candidate.created_at) / 86400.0
            )
        )
        .join(Candidate, Offer.candidate_id == Candidate.id)
        .where(
            Offer.tenant_id == tenant_id,
            Offer.status == "accepted",
        )
    )
    avg_time_to_hire = avg_tth_result.scalar()
    if avg_time_to_hire is not None:
        avg_time_to_hire = round(float(avg_time_to_hire), 1)

    metrics = [
        MetricItem(
            key="open_positions",
            label="在招职位",
            value=open_pos_count,
            trend=trend_pos,
            trend_value=trend_pos_val,
            period="vs 上周",
        ),
        MetricItem(
            key="active_candidates",
            label="候选人管线",
            value=active_candidates_count,
            trend=trend_cand,
            trend_value=trend_cand_val,
            period="vs 上周",
        ),
        MetricItem(
            key="interviews_this_week",
            label="本周面试",
            value=interviews_this_week,
            trend=trend_iv,
            trend_value=trend_iv_val,
            period="vs 上周",
        ),
        MetricItem(
            key="pending_offers",
            label="待处理 Offer",
            value=offers_pending,
            trend=trend_offer,
            trend_value=trend_offer_val,
            period="vs 上周",
        ),
        MetricItem(
            key="avg_time_to_hire",
            label="平均招聘周期",
            value=avg_time_to_hire if avg_time_to_hire is not None else 0,
            unit="天",
            trend=None,
            trend_value=None,
        ),
    ]

    return MetricsResponse(metrics=metrics)


# ── GET /dashboard/ai-insights ───────────────────────────────────

async def get_ai_insights(tenant_id: str, db: AsyncSession) -> AiInsightsResponse:
    """
    Return recent completed AI task results as insights.
    If no tasks, return empty list.
    """
    result = await db.execute(
        select(AiTask).where(
            AiTask.tenant_id == tenant_id,
            AiTask.status == TaskStatus.completed,
        ).order_by(AiTask.updated_at.desc()).limit(5)
    )
    tasks = result.scalars().all()

    insights: list[AiInsight] = []

    for task in tasks:
        # Try to extract a summary from output_data
        summary = _extract_task_summary(task)

        # Map task_type to insight type
        task_type_str = task.task_type.value if task.task_type else "unknown"
        insight_type = _map_task_type_to_insight_type(task_type_str)

        insights.append(AiInsight(
            id=str(task.id),
            type=insight_type,
            title=f"AI 任务完成：{task_type_str}",
            content=summary,
            priority="medium",
            created_at=task.updated_at,
        ))

    return AiInsightsResponse(insights=insights, total=len(insights))


def _extract_task_summary(task: AiTask) -> str:
    """Extract a human-readable summary from the task's output_data."""
    if not task.output_data:
        return f"任务 {task.task_type.value if task.task_type else 'unknown'} 已完成"

    try:
        data = json.loads(task.output_data)
        if isinstance(data, dict):
            # Try common summary fields
            for key in ("summary", "result", "message", "description", "content"):
                val = data.get(key)
                if val and isinstance(val, str):
                    return val
            # Fallback: return a compact JSON snippet
            return json.dumps(data, ensure_ascii=False)[:200]
        elif isinstance(data, str):
            return data[:200]
        else:
            return json.dumps(data, ensure_ascii=False)[:200]
    except (json.JSONDecodeError, TypeError):
        return task.output_data[:200]


def _map_task_type_to_insight_type(task_type: str) -> str:
    """Map AI task type to insight display type."""
    mapping = {
        "resume_parse": "summary",
        "candidate_match": "recommendation",
        "batch_score": "summary",
        "report_generate": "summary",
        "data_import": "alert",
    }
    return mapping.get(task_type, "suggestion")
