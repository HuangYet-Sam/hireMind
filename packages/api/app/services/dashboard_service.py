"""
Dashboard Service — Business logic for dashboard endpoints.

Queries real data from the database via SQLAlchemy async.
Returns empty / zero values when tables are empty — no mock data.

M7 additions:
  - get_funnel(): Recruitment funnel with conversion rates
  - get_dashboard_todos(): Enhanced todo list with urgency levels
  - get_trends(): Time-series trend data
  - get_source_distribution(): Candidate source breakdown
  - get_dashboard_metrics(): Quick metrics summary
"""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID
import json

from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_task import AiTask, TaskStatus
from app.models.candidate import Candidate
from app.models.interview import Interview, InterviewFeedback
from app.models.matching import Match
from app.models.offer import Offer, OfferApproval
from app.models.position import Position
from app.models.resume import Resume
from app.schemas.dashboard import (
    AiInsight,
    AiInsightsResponse,
    DashboardMetrics,
    DashboardTodoItem,
    FunnelResponse,
    FunnelStage,
    MetricItem,
    MetricsResponse,
    ScheduleEvent,
    ScheduleResponse,
    SourceDistribution,
    SourceResponse,
    TodoItem,
    TodoListResponse,
    TodoResponse,
    TrendDataPoint,
    TrendResponse,
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


def _date_range_for_period(period: str) -> tuple[datetime, datetime] | None:
    """Return (start, end) for a given period string, or None for 'all'."""
    now = datetime.now(timezone.utc)
    if period == "daily":
        start = now - timedelta(days=1)
        return start, now
    elif period == "weekly":
        start = now - timedelta(weeks=1)
        return start, now
    elif period == "monthly":
        start = now - timedelta(days=30)
        return start, now
    return None  # "all"


# ── GET /dashboard/todos (original) ────────────────────────────

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


# ── GET /dashboard/schedule (original) ─────────────────────────

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


# ── GET /dashboard/metrics (original) ──────────────────────────

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


# ── GET /dashboard/ai-insights (original) ──────────────────────

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


# ══════════════════════════════════════════════════════════════════
# M7 Enhancement Methods
# ══════════════════════════════════════════════════════════════════


# ── GET /dashboard/funnel ──────────────────────────────────────

async def get_funnel(
    tenant_id: str,
    db: AsyncSession,
    position_id: UUID | None = None,
    period: str = "all",
) -> FunnelResponse:
    """
    Build a recruitment funnel with conversion rates.

    Stages: positions → resumes → matches → interviews → offers → hired

    Args:
        tenant_id: Tenant scope
        db: Async database session
        position_id: Optional filter for a specific position
        period: Time period filter (daily/weekly/monthly/all)

    Returns:
        FunnelResponse with stages and conversion rates.
    """
    now = datetime.now(timezone.utc)
    date_range = _date_range_for_period(period)
    start_dt, end_dt = date_range if date_range else (None, None)

    # Stage labels
    stage_labels = {
        "position": "岗位发布",
        "resume": "简历接收",
        "match": "匹配筛选",
        "interview": "面试",
        "offer": "Offer",
        "hired": "入职",
    }

    # ── Positions count ────────────────────────────────────────
    pos_query = select(func.count()).select_from(Position).where(
        Position.tenant_id == tenant_id,
    )
    if position_id is not None:
        pos_query = pos_query.where(Position.id == position_id)
    if start_dt is not None:
        pos_query = pos_query.where(Position.created_at >= start_dt)
    positions_count = await db.scalar(pos_query) or 0

    # ── Resumes count ──────────────────────────────────────────
    resume_query = select(func.count()).select_from(Resume).where(
        Resume.tenant_id == tenant_id,
    )
    if position_id is not None:
        resume_query = resume_query.where(Resume.position_id == position_id)
    if start_dt is not None:
        resume_query = resume_query.where(Resume.created_at >= start_dt)
    resumes_count = await db.scalar(resume_query) or 0

    # ── Matches count ──────────────────────────────────────────
    match_query = select(func.count()).select_from(Match).where(
        Match.tenant_id == tenant_id,
    )
    if position_id is not None:
        match_query = match_query.where(Match.position_id == position_id)
    if start_dt is not None:
        match_query = match_query.where(Match.matched_at >= start_dt)
    matches_count = await db.scalar(match_query) or 0

    # ── Interviews count ───────────────────────────────────────
    iv_query = select(func.count()).select_from(Interview).where(
        Interview.tenant_id == tenant_id,
    )
    if position_id is not None:
        iv_query = iv_query.where(Interview.position_id == position_id)
    if start_dt is not None:
        iv_query = iv_query.where(Interview.scheduled_at >= start_dt)
    interviews_count = await db.scalar(iv_query) or 0

    # ── Offers count ───────────────────────────────────────────
    offer_query = select(func.count()).select_from(Offer).where(
        Offer.tenant_id == tenant_id,
    )
    if position_id is not None:
        offer_query = offer_query.where(Offer.position_id == position_id)
    if start_dt is not None:
        offer_query = offer_query.where(Offer.created_at >= start_dt)
    offers_count = await db.scalar(offer_query) or 0

    # ── Hired count ────────────────────────────────────────────
    hired_query = select(func.count()).select_from(Candidate).where(
        Candidate.tenant_id == tenant_id,
        Candidate.stage == "hired",
    )
    if position_id is not None:
        hired_query = hired_query.where(Candidate.position_id == position_id)
    if start_dt is not None:
        hired_query = hired_query.where(Candidate.updated_at >= start_dt)
    hired_count = await db.scalar(hired_query) or 0

    # Build funnel stages
    counts = [positions_count, resumes_count, matches_count,
              interviews_count, offers_count, hired_count]
    stage_keys = ["position", "resume", "match", "interview", "offer", "hired"]

    stages: list[FunnelStage] = []
    for i, (key, count) in enumerate(zip(stage_keys, counts)):
        # Conversion rate relative to previous stage
        if i > 0 and counts[i - 1] > 0:
            conversion_rate = round(count / counts[i - 1] * 100, 1)
        elif i > 0:
            conversion_rate = None
        else:
            conversion_rate = None

        # Cumulative rate relative to first stage
        if i > 0 and counts[0] > 0:
            cumulative_rate = round(count / counts[0] * 100, 1)
        else:
            cumulative_rate = None

        stages.append(FunnelStage(
            stage=key,
            label=stage_labels.get(key, key),
            count=count,
            conversion_rate=conversion_rate,
            cumulative_rate=cumulative_rate,
        ))

    return FunnelResponse(
        position_id=position_id,
        stages=stages,
        period=period,
        generated_at=now,
    )


# ── GET /dashboard/todos (enhanced M7) ─────────────────────────

async def get_dashboard_todos(
    tenant_id: str,
    user_id: str,
    db: AsyncSession,
) -> TodoResponse:
    """
    Build enhanced todo list for the dashboard.

    Categories:
      - resume_pending: Resumes awaiting screening
      - interview_feedback: Completed interviews needing feedback
      - offer_followup: Sent/pending offers needing follow-up
      - approval_pending: Offers awaiting current user's approval
      - position_overdue: Positions past their deadline but still open

    Args:
        tenant_id: Tenant scope
        user_id: Current user ID (for approval filtering)
        db: Async database session

    Returns:
        TodoResponse with categorized items and urgency counts.
    """
    now = datetime.now(timezone.utc)
    items: list[DashboardTodoItem] = []

    # 1) 简历待筛选 — Resumes with parse_status='pending'
    pending_resumes = await db.execute(
        select(Resume).where(
            Resume.tenant_id == tenant_id,
            Resume.parse_status == "pending",
        ).order_by(Resume.created_at.asc()).limit(50)
    )
    for resume in pending_resumes.scalars().all():
        items.append(DashboardTodoItem(
            id=f"todo-resume-{resume.id}",
            type="resume_pending",
            title=f"简历待筛选：{resume.original_filename}",
            description=f"简历「{resume.original_filename}」已上传，等待筛选处理。",
            urgency="high",
            entity_id=resume.id,
            entity_type="resume",
            due_at=None,
            created_at=resume.created_at or now,
        ))

    # 2) 面试待反馈 — Interviews completed but no feedback
    completed_interviews = await db.execute(
        select(Interview).where(
            Interview.tenant_id == tenant_id,
            Interview.status == "completed",
        ).order_by(Interview.completed_at.asc()).limit(50)
    )
    for iv in completed_interviews.scalars().all():
        # Check if feedback exists (simplified: check if summary is None)
        candidate_name = iv.candidate.name if iv.candidate else "未知候选人"
        items.append(DashboardTodoItem(
            id=f"todo-feedback-{iv.id}",
            type="interview_feedback",
            title=f"面试待反馈：{candidate_name}",
            description=f"候选人 {candidate_name} 的面试已完成，请提交面试反馈。",
            urgency="high",
            entity_id=iv.id,
            entity_type="interview",
            due_at=None,
            created_at=iv.completed_at or iv.created_at or now,
        ))

    # 3) Offer待跟进 — Offers in 'sent' or 'pending' status
    followup_offers = await db.execute(
        select(Offer).where(
            Offer.tenant_id == tenant_id,
            Offer.status.in_(["sent", "pending"]),
        ).order_by(Offer.created_at.asc()).limit(50)
    )
    for offer in followup_offers.scalars().all():
        candidate_name = offer.candidate.name if offer.candidate else "未知候选人"
        position_title = offer.position.title if offer.position else "未知职位"
        # Check urgency based on expiry
        urgency = "medium"
        if offer.expiry_date:
            days_to_expire = (offer.expiry_date - now).days
            if days_to_expire <= 1:
                urgency = "urgent"
            elif days_to_expire <= 3:
                urgency = "high"

        items.append(DashboardTodoItem(
            id=f"todo-offer-{offer.id}",
            type="offer_followup",
            title=f"Offer待跟进：{candidate_name}",
            description=f"候选人 {candidate_name} 的「{position_title}」Offer 待跟进。",
            urgency=urgency,
            entity_id=offer.id,
            entity_type="offer",
            due_at=offer.expiry_date,
            created_at=offer.created_at or now,
        ))

    # 4) 审批待处理 — Offers with pending approvals for current user
    pending_approvals = await db.execute(
        select(OfferApproval).where(
            OfferApproval.approver_id == user_id,
            OfferApproval.status == "pending",
        ).order_by(OfferApproval.created_at.asc()).limit(50)
    )
    for approval in pending_approvals.scalars().all():
        # Get the offer details
        offer_result = await db.execute(
            select(Offer).where(Offer.id == approval.offer_id)
        )
        offer = offer_result.scalar_one_or_none()
        if offer is None:
            continue

        candidate_name = offer.candidate.name if offer.candidate else "未知候选人"
        position_title = offer.position.title if offer.position else "未知职位"
        items.append(DashboardTodoItem(
            id=f"todo-approval-{approval.id}",
            type="approval_pending",
            title=f"审批待处理：{candidate_name} 的 Offer",
            description=f"候选人 {candidate_name} 的「{position_title}」Offer 需要您的审批。",
            urgency="high",
            entity_id=offer.id,
            entity_type="offer",
            due_at=offer.expiry_date,
            created_at=approval.created_at or now,
        ))

    # 5) 岗位超期 — Positions past deadline but still open
    overdue_positions = await db.execute(
        select(Position).where(
            Position.tenant_id == tenant_id,
            Position.status == "open",
            Position.created_at < now - timedelta(days=30),
        ).order_by(Position.created_at.asc()).limit(50)
    )
    for pos in overdue_positions.scalars().all():
        days_open = (now - (pos.created_at.replace(tzinfo=timezone.utc) if pos.created_at and pos.created_at.tzinfo is None else (pos.created_at or now))).days
        items.append(DashboardTodoItem(
            id=f"todo-overdue-{pos.id}",
            type="position_overdue",
            title=f"岗位超期：{pos.title}",
            description=f"「{pos.title}」已招聘 {days_open} 天，超过预期周期。",
            urgency="urgent" if days_open > 60 else "high",
            entity_id=pos.id,
            entity_type="position",
            due_at=None,
            created_at=pos.created_at or now,
        ))

    # Sort by urgency
    urgency_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    items.sort(
        key=lambda t: (urgency_order.get(t.urgency, 2), t.created_at)
    )

    urgent_count = sum(1 for item in items if item.urgency == "urgent")

    return TodoResponse(
        items=items,
        total_count=len(items),
        urgent_count=urgent_count,
    )


# ── GET /dashboard/trends ──────────────────────────────────────

async def get_trends(
    tenant_id: str,
    db: AsyncSession,
    period: str = "daily",
    start_date: str | None = None,
    end_date: str | None = None,
) -> TrendResponse:
    """
    Get time-series recruitment trend data.

    Groups data by day, week, or month and returns counts for:
    resumes, matches, interviews, offers, hires.

    Args:
        tenant_id: Tenant scope
        db: Async database session
        period: Grouping period (daily/weekly/monthly)
        start_date: Start date string (YYYY-MM-DD), defaults to 30 days ago
        end_date: End date string (YYYY-MM-DD), defaults to today

    Returns:
        TrendResponse with data points for the requested period.
    """
    now = datetime.now(timezone.utc)

    # Parse date range
    if start_date:
        range_start = datetime.strptime(start_date, "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
        )
    else:
        range_start = now - timedelta(days=30)

    if end_date:
        range_end = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc
        )
    else:
        range_end = now

    # Generate date buckets based on period
    data_points: list[TrendDataPoint] = []

    if period == "daily":
        current = range_start
        while current <= range_end:
            day_end = current + timedelta(days=1) - timedelta(microseconds=1)

            resumes = await db.scalar(
                select(func.count()).select_from(Resume).where(
                    Resume.tenant_id == tenant_id,
                    Resume.created_at >= current,
                    Resume.created_at <= day_end,
                )
            ) or 0

            matches = await db.scalar(
                select(func.count()).select_from(Match).where(
                    Match.tenant_id == tenant_id,
                    Match.matched_at >= current,
                    Match.matched_at <= day_end,
                )
            ) or 0

            interviews = await db.scalar(
                select(func.count()).select_from(Interview).where(
                    Interview.tenant_id == tenant_id,
                    Interview.scheduled_at >= current,
                    Interview.scheduled_at <= day_end,
                )
            ) or 0

            offers = await db.scalar(
                select(func.count()).select_from(Offer).where(
                    Offer.tenant_id == tenant_id,
                    Offer.created_at >= current,
                    Offer.created_at <= day_end,
                )
            ) or 0

            hires = await db.scalar(
                select(func.count()).select_from(Candidate).where(
                    Candidate.tenant_id == tenant_id,
                    Candidate.stage == "hired",
                    Candidate.updated_at >= current,
                    Candidate.updated_at <= day_end,
                )
            ) or 0

            data_points.append(TrendDataPoint(
                date=current.strftime("%Y-%m-%d"),
                resumes=resumes,
                matches=matches,
                interviews=interviews,
                offers=offers,
                hires=hires,
            ))
            current += timedelta(days=1)

    elif period == "weekly":
        current = range_start
        while current <= range_end:
            week_end = current + timedelta(days=7) - timedelta(microseconds=1)
            iso_year, iso_week, _ = current.isocalendar()

            resumes = await db.scalar(
                select(func.count()).select_from(Resume).where(
                    Resume.tenant_id == tenant_id,
                    Resume.created_at >= current,
                    Resume.created_at <= week_end,
                )
            ) or 0

            matches = await db.scalar(
                select(func.count()).select_from(Match).where(
                    Match.tenant_id == tenant_id,
                    Match.matched_at >= current,
                    Match.matched_at <= week_end,
                )
            ) or 0

            interviews = await db.scalar(
                select(func.count()).select_from(Interview).where(
                    Interview.tenant_id == tenant_id,
                    Interview.scheduled_at >= current,
                    Interview.scheduled_at <= week_end,
                )
            ) or 0

            offers = await db.scalar(
                select(func.count()).select_from(Offer).where(
                    Offer.tenant_id == tenant_id,
                    Offer.created_at >= current,
                    Offer.created_at <= week_end,
                )
            ) or 0

            hires = await db.scalar(
                select(func.count()).select_from(Candidate).where(
                    Candidate.tenant_id == tenant_id,
                    Candidate.stage == "hired",
                    Candidate.updated_at >= current,
                    Candidate.updated_at <= week_end,
                )
            ) or 0

            data_points.append(TrendDataPoint(
                date=f"{iso_year}-W{iso_week:02d}",
                resumes=resumes,
                matches=matches,
                interviews=interviews,
                offers=offers,
                hires=hires,
            ))
            current += timedelta(days=7)

    else:  # monthly
        current = range_start
        while current <= range_end:
            # End of month
            if current.month == 12:
                month_end = current.replace(
                    year=current.year + 1, month=1, day=1
                ) - timedelta(microseconds=1)
            else:
                month_end = current.replace(
                    month=current.month + 1, day=1
                ) - timedelta(microseconds=1)

            resumes = await db.scalar(
                select(func.count()).select_from(Resume).where(
                    Resume.tenant_id == tenant_id,
                    Resume.created_at >= current,
                    Resume.created_at <= month_end,
                )
            ) or 0

            matches = await db.scalar(
                select(func.count()).select_from(Match).where(
                    Match.tenant_id == tenant_id,
                    Match.matched_at >= current,
                    Match.matched_at <= month_end,
                )
            ) or 0

            interviews = await db.scalar(
                select(func.count()).select_from(Interview).where(
                    Interview.tenant_id == tenant_id,
                    Interview.scheduled_at >= current,
                    Interview.scheduled_at <= month_end,
                )
            ) or 0

            offers = await db.scalar(
                select(func.count()).select_from(Offer).where(
                    Offer.tenant_id == tenant_id,
                    Offer.created_at >= current,
                    Offer.created_at <= month_end,
                )
            ) or 0

            hires = await db.scalar(
                select(func.count()).select_from(Candidate).where(
                    Candidate.tenant_id == tenant_id,
                    Candidate.stage == "hired",
                    Candidate.updated_at >= current,
                    Candidate.updated_at <= month_end,
                )
            ) or 0

            data_points.append(TrendDataPoint(
                date=current.strftime("%Y-%m"),
                resumes=resumes,
                matches=matches,
                interviews=interviews,
                offers=offers,
                hires=hires,
            ))
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1, day=1)
            else:
                current = current.replace(month=current.month + 1, day=1)

    return TrendResponse(
        period=period,
        data_points=data_points,
        start_date=range_start.strftime("%Y-%m-%d"),
        end_date=range_end.strftime("%Y-%m-%d"),
    )


# ── GET /dashboard/sources ─────────────────────────────────────

async def get_source_distribution(
    tenant_id: str,
    db: AsyncSession,
) -> SourceResponse:
    """
    Get candidate source distribution with effectiveness metrics.

    Returns per-source stats: count, interview rate, offer rate, and
    optional cost data.

    Args:
        tenant_id: Tenant scope
        db: Async database session

    Returns:
        SourceResponse with per-source breakdown.
    """
    # Query candidate counts and stage breakdown by source
    result = await db.execute(
        select(
            Candidate.source,
            func.count().label("total"),
            func.count(
                case((Candidate.stage.in_(["interviewed", "offered", "hired"]), Candidate.id))
            ).label("interviewed"),
            func.count(
                case((Candidate.stage.in_(["offered", "hired"]), Candidate.id))
            ).label("offered"),
        )
        .where(
            Candidate.tenant_id == tenant_id,
            Candidate.status == "active",
        )
        .group_by(Candidate.source)
    )
    rows = result.all()

    sources: list[SourceDistribution] = []
    total_count = 0

    for row in rows:
        source_label = row.source or "unknown"
        count = row.total
        total_count += count

        interview_rate = round(row.interviewed / count * 100, 1) if count > 0 else 0.0
        offer_rate = round(row.offered / count * 100, 1) if count > 0 else 0.0

        # Cost data would come from a separate budget table — placeholder
        cost = None

        sources.append(SourceDistribution(
            source=source_label,
            count=count,
            interview_rate=interview_rate,
            offer_rate=offer_rate,
            cost=cost,
        ))

    # Sort by count descending
    sources.sort(key=lambda s: s.count, reverse=True)

    return SourceResponse(
        sources=sources,
        total_count=total_count,
    )


# ── GET /dashboard/metrics (M7 quick) ─────────────────────────

async def get_dashboard_metrics(
    tenant_id: str,
    db: AsyncSession,
) -> DashboardMetrics:
    """
    Quick metrics summary for dashboard header.

    Returns key counts: active positions, total candidates,
    interviews this week, pending offers, resumes pending, overdue positions.

    Args:
        tenant_id: Tenant scope
        db: Async database session

    Returns:
        DashboardMetrics with core indicators.
    """
    now = datetime.now(timezone.utc)
    week_start, week_end = _week_bounds(now)

    # Active positions
    active_positions = await db.scalar(
        select(func.count()).select_from(Position).where(
            Position.tenant_id == tenant_id,
            Position.status == "open",
        )
    ) or 0

    # Total candidates in pipeline
    total_candidates = await db.scalar(
        select(func.count()).select_from(Candidate).where(
            Candidate.tenant_id == tenant_id,
            Candidate.status == "active",
            Candidate.stage.notin_(["hired", "rejected"]),
        )
    ) or 0

    # Interviews this week
    interviews_this_week = await db.scalar(
        select(func.count()).select_from(Interview).where(
            Interview.tenant_id == tenant_id,
            Interview.scheduled_at >= week_start,
            Interview.scheduled_at <= week_end,
        )
    ) or 0

    # Pending offers
    pending_offers = await db.scalar(
        select(func.count()).select_from(Offer).where(
            Offer.tenant_id == tenant_id,
            Offer.status.in_(["pending_approval", "sent", "draft"]),
        )
    ) or 0

    # Resumes pending screening
    resumes_pending = await db.scalar(
        select(func.count()).select_from(Resume).where(
            Resume.tenant_id == tenant_id,
            Resume.parse_status == "pending",
        )
    ) or 0

    # Overdue positions (open for > 30 days)
    overdue_cutoff = now - timedelta(days=30)
    overdue_positions = await db.scalar(
        select(func.count()).select_from(Position).where(
            Position.tenant_id == tenant_id,
            Position.status == "open",
            Position.created_at < overdue_cutoff,
        )
    ) or 0

    return DashboardMetrics(
        active_positions=active_positions,
        total_candidates=total_candidates,
        interviews_this_week=interviews_this_week,
        pending_offers=pending_offers,
        resumes_pending=resumes_pending,
        overdue_positions=overdue_positions,
    )
