"""
InsightEngine — proactive AI-driven insight generation service.

Scans recruitment data across 8 trigger conditions, generates
actionable insights, and supports insight lifecycle management
(read / ignore / dismiss).

Trigger conditions:
  1. resume_peak     — 简历到达高峰 (>日均值2倍)
  2. match_anomaly   — 匹配异常 (某岗位匹配分骤降)
  3. interview_timeout — 面试超时 (>3天未反馈)
  4. offer_stale     — Offer僵局 (>7天未回应)
  5. funnel_bottleneck — 漏斗瓶颈 (某阶段转化率<10%)
  6. silent_activation — 沉默激活 (候选人库30天无互动)
  7. position_overdue — 岗位超期 (招聘周期>预期)
  8. daily_report / weekly_report — 日报/周报触发
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.offer import Offer
from app.models.position import Position

logger = logging.getLogger("hiremind.services.insight_engine")


class InsightRecord:
    """In-memory insight record (not persisted — could be linked to a model later)."""

    __slots__ = (
        "id", "tenant_id", "category", "title", "content",
        "severity", "trigger_type", "entity_id", "entity_type",
        "action_suggestion", "status", "created_at",
    )

    def __init__(
        self,
        tenant_id: str,
        category: str,
        title: str,
        content: str,
        severity: str = "info",
        trigger_type: str = "",
        entity_id: str | None = None,
        entity_type: str | None = None,
        action_suggestion: str | None = None,
    ):
        self.id = str(uuid.uuid4())
        self.tenant_id = tenant_id
        self.category = category
        self.title = title
        self.content = content
        self.severity = severity
        self.trigger_type = trigger_type
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.action_suggestion = action_suggestion
        self.status = "active"
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "category": self.category,
            "title": self.title,
            "content": self.content,
            "severity": self.severity,
            "trigger_type": self.trigger_type,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "action_suggestion": self.action_suggestion,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


# In-memory insight store (per-process; replace with DB in production)
_insight_store: dict[str, InsightRecord] = {}


class InsightEngine:
    """Async service that scans data and generates proactive insights."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Main Scan Entry ─────────────────────────────────────────

    async def scan_and_generate(self, tenant_id: str) -> list[dict[str, Any]]:
        """主扫描入口 — run all 8 trigger checks and collect insights.

        Args:
            tenant_id: Tenant scope.

        Returns:
            List of generated insight dicts.
        """
        insights: list[InsightRecord] = []

        # 1. Resume arrival peak
        insights.extend(await self._check_resume_peak(tenant_id))

        # 2. Match anomaly
        insights.extend(await self._check_match_anomaly(tenant_id))

        # 3. Interview timeout
        insights.extend(await self._check_interview_timeout(tenant_id))

        # 4. Offer stale
        insights.extend(await self._check_offer_stale(tenant_id))

        # 5. Funnel bottleneck
        insights.extend(await self._check_funnel_bottleneck(tenant_id))

        # 6. Silent activation
        insights.extend(await self._check_silent_activation(tenant_id))

        # 7. Position overdue
        insights.extend(await self._check_position_overdue(tenant_id))

        # 8. Daily/weekly report trigger
        insights.extend(await self._check_report_trigger(tenant_id))

        # Persist to in-memory store
        for ins in insights:
            _insight_store[ins.id] = ins

        logger.info(
            "InsightEngine scan completed: tenant=%s, insights=%d",
            tenant_id, len(insights),
        )
        return [ins.to_dict() for ins in insights]

    # ── Trigger 1: Resume Peak ──────────────────────────────────

    async def _check_resume_peak(self, tenant_id: str) -> list[InsightRecord]:
        """简历到达高峰 — daily count > 2x rolling 30-day average."""
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Average daily resumes (last 30 days)
        avg_result = await self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.created_at >= thirty_days_ago,
            )
        )
        avg_daily = (avg_result or 0) / 30.0

        # Today's count
        today_count = await self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.created_at >= today_start,
            )
        ) or 0

        insights = []
        if avg_daily > 0 and today_count > avg_daily * 2:
            insights.append(InsightRecord(
                tenant_id=tenant_id,
                category="trend",
                title="简历到达高峰",
                content=(
                    f"今日收到 {today_count} 份简历，是日均 {round(avg_daily, 1)} 份的 "
                    f"{round(today_count / avg_daily, 1)} 倍。"
                    f"建议关注简历处理效率，避免积压。"
                ),
                severity="warning",
                trigger_type="resume_peak",
                action_suggestion="查看待筛选简历列表，安排筛选资源。",
            ))

        return insights

    # ── Trigger 2: Match Anomaly ────────────────────────────────

    async def _check_match_anomaly(self, tenant_id: str) -> list[InsightRecord]:
        """匹配异常 — 某岗位匹配分骤降 (>30% drop vs last week)."""
        now = datetime.now(timezone.utc)
        one_week_ago = now - timedelta(weeks=1)
        two_weeks_ago = now - timedelta(weeks=2)

        insights = []

        # Get open positions
        positions = (await self.db.execute(
            select(Position).where(
                Position.tenant_id == tenant_id,
                Position.status == "open",
            )
        )).scalars().all()

        for pos in positions:
            # This week's average match score
            this_week = await self.db.scalar(
                select(func.avg(Candidate.credibility_score)).where(
                    Candidate.position_id == pos.id,
                    Candidate.credibility_score.isnot(None),
                    Candidate.created_at >= one_week_ago,
                )
            )
            # Last week's average match score
            last_week = await self.db.scalar(
                select(func.avg(Candidate.credibility_score)).where(
                    Candidate.position_id == pos.id,
                    Candidate.credibility_score.isnot(None),
                    Candidate.created_at >= two_weeks_ago,
                    Candidate.created_at < one_week_ago,
                )
            )

            if this_week and last_week and last_week > 0:
                drop_pct = (last_week - float(this_week)) / float(last_week) * 100
                if drop_pct > 30:
                    insights.append(InsightRecord(
                        tenant_id=tenant_id,
                        category="risk",
                        title=f"岗位「{pos.title}」匹配分骤降",
                        content=(
                            f"岗位 {pos.title} 本周平均匹配分 {round(float(this_week), 1)}，"
                            f"较上周 {round(float(last_week), 1)} 下降 {round(drop_pct, 1)}%。"
                            f"可能原因：JD 需求变更、候选人来源质量下降。"
                        ),
                        severity="warning",
                        trigger_type="match_anomaly",
                        entity_id=str(pos.id),
                        entity_type="position",
                        action_suggestion="检查 JD 和渠道来源，必要时调整匹配策略。",
                    ))

        return insights

    # ── Trigger 3: Interview Timeout ────────────────────────────

    async def _check_interview_timeout(self, tenant_id: str) -> list[InsightRecord]:
        """面试超时 — 面试完成>3天未提交反馈."""
        now = datetime.now(timezone.utc)
        three_days_ago = now - timedelta(days=3)

        # Interviews that are completed but have no feedback
        timeout_interviews = (await self.db.execute(
            select(Interview).where(
                Interview.tenant_id == tenant_id,
                Interview.status == "completed",
                Interview.updated_at < three_days_ago,
                Interview.overall_score.is_(None),
            )
        )).scalars().all()

        insights = []
        for iv in timeout_interviews[:10]:  # Limit to 10
            insights.append(InsightRecord(
                tenant_id=tenant_id,
                category="alert",
                title="面试反馈超时",
                content=(
                    f"面试 {str(iv.id)[:8]}... 已完成超过3天仍未提交反馈。"
                    f"面试时间: {iv.scheduled_at.strftime('%Y-%m-%d') if iv.scheduled_at else 'N/A'}"
                ),
                severity="urgent",
                trigger_type="interview_timeout",
                entity_id=str(iv.id),
                entity_type="interview",
                action_suggestion="联系面试官催促反馈提交。",
            ))

        return insights

    # ── Trigger 4: Offer Stale ──────────────────────────────────

    async def _check_offer_stale(self, tenant_id: str) -> list[InsightRecord]:
        """Offer僵局 — 发出Offer >7天未回应."""
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)

        stale_offers = (await self.db.execute(
            select(Offer).where(
                Offer.tenant_id == tenant_id,
                Offer.status == "sent",
                Offer.updated_at < seven_days_ago,
            )
        )).scalars().all()

        insights = []
        for offer in stale_offers[:10]:
            insights.append(InsightRecord(
                tenant_id=tenant_id,
                category="alert",
                title="Offer僵局",
                content=(
                    f"Offer {str(offer.id)[:8]}... 已发出超过7天未收到候选人回应。"
                    f"状态: {offer.status}"
                ),
                severity="urgent",
                trigger_type="offer_stale",
                entity_id=str(offer.id),
                entity_type="offer",
                action_suggestion="联系候选人跟进，评估是否需要调整Offer条件。",
            ))

        return insights

    # ── Trigger 5: Funnel Bottleneck ────────────────────────────

    async def _check_funnel_bottleneck(self, tenant_id: str) -> list[InsightRecord]:
        """漏斗瓶颈 — 某阶段转化率<10%."""
        # Get funnel stage distribution
        rows = (await self.db.execute(
            select(Candidate.stage, func.count().label("count")).where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
            ).group_by(Candidate.stage)
        )).all()

        stage_counts = {row.stage: row.count for row in rows}
        ordered = ["applied", "screened", "interviewed", "offered", "hired"]

        insights = []
        for i in range(1, len(ordered)):
            prev_count = stage_counts.get(ordered[i - 1], 0)
            curr_count = stage_counts.get(ordered[i], 0)
            if prev_count > 0:
                rate = curr_count / prev_count * 100
                if rate < 10 and prev_count >= 5:
                    insights.append(InsightRecord(
                        tenant_id=tenant_id,
                        category="risk",
                        title=f"漏斗瓶颈: {ordered[i - 1]} → {ordered[i]}",
                        content=(
                            f"阶段 {ordered[i - 1]}→{ordered[i]} 转化率仅 {round(rate, 1)}% "
                            f"({prev_count}→{curr_count})。"
                            f"该阶段可能存在流程或标准问题。"
                        ),
                        severity="warning",
                        trigger_type="funnel_bottleneck",
                        action_suggestion=f"审查 {ordered[i - 1]}→{ordered[i]} 阶段的筛选标准和流程。",
                    ))

        return insights

    # ── Trigger 6: Silent Activation ────────────────────────────

    async def _check_silent_activation(self, tenant_id: str) -> list[InsightRecord]:
        """沉默激活 — 候选人库30天无互动."""
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        silent_count = await self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
                Candidate.stage.notin_(["hired", "rejected"]),
                Candidate.updated_at < thirty_days_ago,
            )
        ) or 0

        insights = []
        if silent_count > 0:
            insights.append(InsightRecord(
                tenant_id=tenant_id,
                category="opportunity",
                title="沉默候选人激活",
                content=(
                    f"有 {silent_count} 名候选人超过30天无互动。"
                    f"这些候选人可能适合新开放的岗位，建议重新评估。"
                ),
                severity="info",
                trigger_type="silent_activation",
                action_suggestion="筛选沉默候选人，匹配合适的新岗位。",
            ))

        return insights

    # ── Trigger 7: Position Overdue ─────────────────────────────

    async def _check_position_overdue(self, tenant_id: str) -> list[InsightRecord]:
        """岗位超期 — 招聘周期>预期 (default: 45 days)."""
        now = datetime.now(timezone.utc)
        overdue_threshold = timedelta(days=45)

        open_positions = (await self.db.execute(
            select(Position).where(
                Position.tenant_id == tenant_id,
                Position.status == "open",
            )
        )).scalars().all()

        insights = []
        for pos in open_positions:
            if pos.created_at and (now - pos.created_at.replace(tzinfo=timezone.utc) if pos.created_at.tzinfo is None else now - pos.created_at) > overdue_threshold:
                # Count how many hired
                hired = await self.db.scalar(
                    select(func.count()).select_from(Candidate).where(
                        Candidate.position_id == pos.id,
                        Candidate.stage == "hired",
                    )
                ) or 0
                days_open = (now - pos.created_at).days
                fill_rate = round(hired / pos.headcount * 100, 1) if pos.headcount > 0 else 0.0

                insights.append(InsightRecord(
                    tenant_id=tenant_id,
                    category="risk",
                    title=f"岗位超期: {pos.title}",
                    content=(
                        f"岗位「{pos.title}」已开放 {days_open} 天，"
                        f"到岗 {hired}/{pos.headcount} ({fill_rate}%)。"
                        f"建议评估是否需要调整招聘策略。"
                    ),
                    severity="warning",
                    trigger_type="position_overdue",
                    entity_id=str(pos.id),
                    entity_type="position",
                    action_suggestion="考虑扩大招聘渠道、调整JD或放宽要求。",
                ))

        return insights

    # ── Trigger 8: Daily/Weekly Report ──────────────────────────

    async def _check_report_trigger(self, tenant_id: str) -> list[InsightRecord]:
        """日报/周报触发 — always generates a summary insight."""
        now = datetime.now(timezone.utc)

        # Quick stats
        active_positions = await self.db.scalar(
            select(func.count()).select_from(Position).where(
                Position.tenant_id == tenant_id,
                Position.status == "open",
            )
        ) or 0

        pending_resumes = await self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.stage == "applied",
                Candidate.status == "active",
            )
        ) or 0

        interviews_today = await self.db.scalar(
            select(func.count()).select_from(Interview).where(
                Interview.tenant_id == tenant_id,
                func.date(Interview.scheduled_at) == now.date(),
            )
        ) or 0

        pending_offers = await self.db.scalar(
            select(func.count()).select_from(Offer).where(
                Offer.tenant_id == tenant_id,
                Offer.status.in_(["draft", "pending_approval", "sent"]),
            )
        ) or 0

        # Daily report
        daily_insight = InsightRecord(
            tenant_id=tenant_id,
            category="summary",
            title="招聘日报",
            content=(
                f"📊 招聘日报 — {now.strftime('%Y-%m-%d')}\n"
                f"• 在招岗位: {active_positions}\n"
                f"• 待筛选简历: {pending_resumes}\n"
                f"• 今日面试: {interviews_today}\n"
                f"• 待处理Offer: {pending_offers}"
            ),
            severity="info",
            trigger_type="daily_report",
            action_suggestion="关注待筛选简历和待处理Offer。",
        )

        # Weekly report (only on Mondays)
        weekly_insights = [daily_insight]
        if now.weekday() == 0:  # Monday
            week_ago = now - timedelta(weeks=1)
            weekly_hires = await self.db.scalar(
                select(func.count()).select_from(Candidate).where(
                    Candidate.tenant_id == tenant_id,
                    Candidate.stage == "hired",
                    Candidate.updated_at >= week_ago,
                )
            ) or 0

            weekly_insights.append(InsightRecord(
                tenant_id=tenant_id,
                category="summary",
                title="招聘周报",
                content=(
                    f"📋 招聘周报 — 第{now.isocalendar()[1]}周\n"
                    f"• 本周到岗: {weekly_hires}\n"
                    f"• 在招岗位: {active_positions}\n"
                    f"• 待筛选简历: {pending_resumes}\n"
                    f"• 待处理Offer: {pending_offers}"
                ),
                severity="info",
                trigger_type="weekly_report",
                action_suggestion="回顾本周进展，调整下周重点。",
            ))

        return weekly_insights

    # ── Insight Actions ─────────────────────────────────────────

    async def mark_insight(self, insight_id: str, action: str) -> dict[str, Any]:
        """标记洞察操作 (read / ignore / dismiss).

        Args:
            insight_id: Insight UUID.
            action: Action to take (read/ignore/dismiss).

        Returns:
            Dict with action confirmation.
        """
        record = _insight_store.get(insight_id)
        if record is None:
            return {"error": "Insight not found", "insight_id": insight_id}

        if action not in ("read", "ignore", "dismiss"):
            return {"error": "Invalid action", "action": action}

        record.status = action
        return {
            "insight_id": insight_id,
            "action": action,
            "action_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── Insight History ─────────────────────────────────────────

    async def get_insight_history(
        self,
        tenant_id: str,
        filters: dict | None = None,
    ) -> dict[str, Any]:
        """洞察历史查询.

        Args:
            tenant_id: Tenant scope.
            filters: Optional filters (status, category, trigger_type, limit).

        Returns:
            Dict with insights list and total count.
        """
        filters = filters or {}
        limit = filters.get("limit", 50)
        status_filter = filters.get("status")
        category_filter = filters.get("category")
        trigger_filter = filters.get("trigger_type")

        results = []
        for record in _insight_store.values():
            if record.tenant_id != tenant_id:
                continue
            if status_filter and record.status != status_filter:
                continue
            if category_filter and record.category != category_filter:
                continue
            if trigger_filter and record.trigger_type != trigger_filter:
                continue
            results.append(record.to_dict())

        # Sort by created_at descending
        results.sort(key=lambda x: x["created_at"], reverse=True)
        results = results[:limit]

        return {
            "insights": results,
            "total": len(results),
        }

    # ── Proactive AI Insights ───────────────────────────────────

    async def generate_proactive_insights(self, tenant_id: str) -> list[dict[str, Any]]:
        """主动式AI洞察 — based on current data trends.

        Generates higher-order insights beyond simple threshold triggers,
        such as trend acceleration, cross-position patterns, and
        forward-looking recommendations.

        Args:
            tenant_id: Tenant scope.

        Returns:
            List of proactive insight dicts.
        """
        now = datetime.now(timezone.utc)
        insights: list[InsightRecord] = []

        # 1. Pipeline velocity analysis
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)

        recent_hires = await self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.stage == "hired",
                Candidate.updated_at >= thirty_days_ago,
            )
        ) or 0

        previous_hires = await self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.stage == "hired",
                Candidate.updated_at >= sixty_days_ago,
                Candidate.updated_at < thirty_days_ago,
            )
        ) or 0

        if recent_hires > 0 or previous_hires > 0:
            velocity_change = ((recent_hires - previous_hires) / previous_hires * 100
                               if previous_hires > 0 else 100.0)
            direction = "加速" if velocity_change > 0 else "减速"

            insights.append(InsightRecord(
                tenant_id=tenant_id,
                category="trend",
                title=f"招聘流水线{direction}",
                content=(
                    f"近30天到岗 {recent_hires} 人，"
                    f"较前30天 {previous_hires} 人{direction} {abs(round(velocity_change, 1))}%。"
                    f"{'建议保持当前节奏。' if velocity_change > 0 else '建议关注瓶颈环节。'}"
                ),
                severity="info" if velocity_change >= 0 else "warning",
                trigger_type="proactive_velocity",
            ))

        # 2. Source concentration risk
        source_rows = (await self.db.execute(
            select(Candidate.source, func.count().label("cnt")).where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
            ).group_by(Candidate.source).order_by(func.count().desc())
        )).all()

        if source_rows:
            total_candidates = sum(r.cnt for r in source_rows)
            top_source = source_rows[0]
            concentration = top_source.cnt / total_candidates * 100 if total_candidates > 0 else 0

            if concentration > 60:
                insights.append(InsightRecord(
                    tenant_id=tenant_id,
                    category="risk",
                    title="渠道集中度风险",
                    content=(
                        f"渠道「{top_source.source or 'unknown'}」占比 {round(concentration, 1)}%，"
                        f"存在单一渠道依赖风险。建议拓展多元化招聘渠道。"
                    ),
                    severity="warning",
                    trigger_type="proactive_concentration",
                    action_suggestion="评估其他渠道的投入产出，制定渠道多元化计划。",
                ))

        # 3. Offer acceptance trend
        recent_offers = await self.db.scalar(
            select(func.count()).select_from(Offer).where(
                Offer.tenant_id == tenant_id,
                Offer.status == "sent",
                Offer.created_at >= thirty_days_ago,
            )
        ) or 0

        accepted_offers = await self.db.scalar(
            select(func.count()).select_from(Offer).where(
                Offer.tenant_id == tenant_id,
                Offer.status == "accepted",
                Offer.updated_at >= thirty_days_ago,
            )
        ) or 0

        if recent_offers > 0:
            accept_rate = accepted_offers / recent_offers * 100
            if accept_rate < 50:
                insights.append(InsightRecord(
                    tenant_id=tenant_id,
                    category="risk",
                    title="Offer接受率偏低",
                    content=(
                        f"近30天Offer接受率仅 {round(accept_rate, 1)}% "
                        f"({accepted_offers}/{recent_offers})。"
                        f"建议分析拒签原因，优化薪酬方案。"
                    ),
                    severity="warning",
                    trigger_type="proactive_acceptance",
                    action_suggestion="分析候选人拒签原因，对标市场薪资水平。",
                ))

        # Persist to store
        for ins in insights:
            _insight_store[ins.id] = ins

        return [ins.to_dict() for ins in insights]
