"""
Dashboard Service — Business logic for dashboard endpoints.

M1 milestone: returns mock data with simple aggregations from existing tables.
Future: integrate real-time statistics and AI-generated insights.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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


async def get_todos(tenant_id: str, db: AsyncSession) -> TodoListResponse:
    """
    Return pending todo items.

    M1: generates mock todos based on database state.
    """
    items: list[TodoItem] = []

    # Count open positions needing attention
    open_positions = await db.execute(
        select(func.count()).select_from(Position).where(Position.status == "open")
    )
    open_pos_count = open_positions.scalar() or 0

    if open_pos_count > 0:
        items.append(TodoItem(
            id="todo-open-positions",
            title=f"{open_pos_count} 个职位正在招聘中",
            description="有待处理的招聘职位需要跟进",
            priority="high",
            status="pending",
            related_type="position",
        ))

    # Count candidates in screening stage
    screening = await db.execute(
        select(func.count()).select_from(Candidate).where(Candidate.stage == "screening")
    )
    screening_count = screening.scalar() or 0

    if screening_count > 0:
        items.append(TodoItem(
            id="todo-screening",
            title=f"{screening_count} 位候选人待筛选",
            description="有新的候选人需要简历筛选",
            priority="high",
            status="pending",
            related_type="candidate",
        ))

    # Count pending offers
    pending_offers = await db.execute(
        select(func.count()).select_from(Offer).where(Offer.status == "pending")
    )
    offer_count = pending_offers.scalar() or 0

    if offer_count > 0:
        items.append(TodoItem(
            id="todo-offers",
            title=f"{offer_count} 个 Offer 待处理",
            description="有待跟进的 Offer",
            priority="medium",
            status="pending",
            related_type="offer",
        ))

    # Always add some default items if list is empty
    if not items:
        items.append(TodoItem(
            id="todo-welcome",
            title="欢迎使用 HireMind",
            description="开始创建您的第一个招聘职位",
            priority="medium",
            status="pending",
        ))

    return TodoListResponse(items=items, total=len(items))


async def get_schedule(tenant_id: str, db: AsyncSession) -> ScheduleResponse:
    """
    Return today's schedule.

    M1: looks up today's interviews from the database, adds mock events.
    """
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)

    events: list[ScheduleEvent] = []

    # Fetch today's interviews
    result = await db.execute(
        select(Interview).where(
            Interview.scheduled_at >= today_start,
            Interview.scheduled_at <= today_end,
        ).limit(20)
    )
    interviews = result.scalars().all()

    for idx, iv in enumerate(interviews):
        scheduled = iv.scheduled_at or datetime.now(timezone.utc)
        events.append(ScheduleEvent(
            id=str(iv.id),
            title=f"面试 #{idx + 1}",
            start_time=scheduled,
            end_time=scheduled + timedelta(hours=1),
            type="interview",
            location=iv.location or "线上",
            status="scheduled",
        ))

    # Mock defaults if no events
    if not events:
        now = datetime.now(timezone.utc)
        events.append(ScheduleEvent(
            id="schedule-placeholder",
            title="今日暂无面试安排",
            start_time=now,
            end_time=now + timedelta(minutes=30),
            type="reminder",
            status="completed",
        ))

    return ScheduleResponse(
        date=today.isoformat(),
        events=events,
        total=len(events),
    )


async def get_metrics(tenant_id: str, db: AsyncSession) -> MetricsResponse:
    """
    Return key recruitment metrics.

    M1: aggregated counts from existing tables.
    """
    # Open positions
    open_pos = await db.execute(
        select(func.count()).select_from(Position).where(Position.status == "open")
    )
    # Candidates in pipeline (active)
    active_candidates = await db.execute(
        select(func.count()).select_from(Candidate).where(
            Candidate.status.in_(["active", "screening", "interviewing"])
        )
    )
    # Interviews this week
    week_start = datetime.now(timezone.utc) - timedelta(days=datetime.now(timezone.utc).weekday())
    week_interviews = await db.execute(
        select(func.count()).select_from(Interview).where(
            Interview.scheduled_at >= week_start
        )
    )
    # Pending offers
    pending_offers = await db.execute(
        select(func.count()).select_from(Offer).where(Offer.status == "pending")
    )
    # Hired (accepted offers)
    hired = await db.execute(
        select(func.count()).select_from(Offer).where(Offer.status == "accepted")
    )

    metrics = [
        MetricItem(
            key="open_positions",
            label="在招职位",
            value=open_pos.scalar() or 0,
            trend="flat",
        ),
        MetricItem(
            key="active_candidates",
            label="候选人管线",
            value=active_candidates.scalar() or 0,
            trend="up",
            trend_value=12.5,
            period="vs 上周",
        ),
        MetricItem(
            key="interviews_this_week",
            label="本周面试",
            value=week_interviews.scalar() or 0,
            trend="flat",
        ),
        MetricItem(
            key="pending_offers",
            label="待处理 Offer",
            value=pending_offers.scalar() or 0,
            trend="down",
            trend_value=-5.0,
            period="vs 上周",
        ),
        MetricItem(
            key="hired",
            label="已录用",
            value=hired.scalar() or 0,
            trend="up",
            trend_value=8.3,
            period="vs 上月",
        ),
    ]

    return MetricsResponse(metrics=metrics)


async def get_ai_insights(tenant_id: str, db: AsyncSession) -> AiInsightsResponse:
    """
    Return AI-generated insights and recommendations.

    M1: returns mock insights based on data patterns.
    Future: integrate with Hermes Agent for real AI analysis.
    """
    now = datetime.now(timezone.utc)

    insights = [
        AiInsight(
            id="insight-1",
            type="recommendation",
            title="智能推荐：高匹配候选人",
            content="有 3 位候选人与「高级前端工程师」职位匹配度超过 85%，建议优先安排面试。",
            priority="high",
            created_at=now,
            action_label="查看匹配结果",
            action_link="/hr/matching",
        ),
        AiInsight(
            id="insight-2",
            type="alert",
            title="面试安排提醒",
            content="本周有 2 场面试尚未确认时间，请及时跟进候选人 availability。",
            priority="medium",
            created_at=now - timedelta(hours=2),
            action_label="查看日程",
            action_link="/hr/interviews",
        ),
        AiInsight(
            id="insight-3",
            type="summary",
            title="本周招聘周报",
            content="本周新增候选人 15 人，安排面试 8 场，发出 Offer 2 份，招聘进度良好。",
            priority="low",
            created_at=now - timedelta(days=1),
            action_label="查看报表",
            action_link="/hr/analytics",
        ),
        AiInsight(
            id="insight-4",
            type="suggestion",
            title="优化建议：缩短招聘周期",
            content="当前平均招聘周期为 28 天，建议优化简历筛选环节以提升效率。",
            priority="medium",
            created_at=now - timedelta(days=1),
        ),
    ]

    return AiInsightsResponse(insights=insights, total=len(insights))
