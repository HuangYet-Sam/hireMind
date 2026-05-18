"""
Proactive AI Engine — 主动式AI推送引擎。

Provides 8 scenario-based proactive alerts:
  - check_resume_arrival:      新简历到达 → 分析匹配度 → 建议操作
  - check_match_anomaly:       匹配异常 → 预警
  - check_interview_timeout:   面试超时 → 催促提醒
  - check_offer_stale:         Offer僵局 → 跟进建议
  - check_funnel_bottleneck:   漏斗瓶颈 → 改进建议
  - check_silent_activation:   沉默候选人匹配新岗位 → 推荐激活
  - generate_daily_digest:     招聘日报
  - generate_weekly_digest:    招聘周报
  - run_all_scenarios:         运行所有场景，返回 ProactiveAlert 列表

Each scenario: query business data → check trigger condition →
LLM generate content (placeholder) → return alert.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.offer import Offer
from app.models.position import Position
from app.models.resume import Resume
from app.schemas.dashboard import ProactiveAlert

logger = logging.getLogger("hiremind.services.proactive_ai")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_alert(
    scenario_type: str,
    title: str,
    content: str,
    severity: str = "info",
    entity_id: UUID | None = None,
    entity_type: str | None = None,
    action_suggestion: str | None = None,
) -> ProactiveAlert:
    """Create a ProactiveAlert with auto-generated id and timestamp."""
    return ProactiveAlert(
        id=str(uuid.uuid4()),
        scenario_type=scenario_type,
        title=title,
        content=content,
        severity=severity,
        entity_id=entity_id,
        entity_type=entity_type,
        action_suggestion=action_suggestion,
        created_at=_now(),
    )


class ProactiveAIEngine:
    """Proactive AI engine — monitors recruitment pipeline and generates
    actionable alerts for HR teams.

    All LLM-dependent methods use deterministic placeholder logic;
    swap with real LLM calls when the AI provider is configured.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Data Gathering Helpers ────────────────────────────────────

    async def _get_pipeline_counts(self, tenant_id: str) -> dict[str, int]:
        """Get candidate counts by pipeline stage."""
        result = await self.db.execute(
            select(Candidate.stage, func.count().label("count"))
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
            )
            .group_by(Candidate.stage)
        )
        rows = result.all()
        stage_counts = {row.stage: row.count for row in rows}
        return {
            "applied": stage_counts.get("applied", 0),
            "screened": stage_counts.get("screened", 0),
            "interviewed": stage_counts.get("interviewed", 0),
            "offered": stage_counts.get("offered", 0),
            "hired": stage_counts.get("hired", 0),
            "rejected": stage_counts.get("rejected", 0),
        }

    async def _get_recent_resumes(
        self, tenant_id: str, hours: int = 24
    ) -> list[Any]:
        """Get resumes parsed in the last N hours."""
        cutoff = _now() - timedelta(hours=hours)
        result = await self.db.execute(
            select(Resume).where(
                Resume.tenant_id == tenant_id,
                Resume.parse_status == "completed",
                Resume.created_at >= cutoff,
            ).order_by(Resume.created_at.desc()).limit(50)
        )
        return result.scalars().all()

    async def _get_open_positions(self, tenant_id: str) -> list[Any]:
        """Get all open positions."""
        result = await self.db.execute(
            select(Position).where(
                Position.tenant_id == tenant_id,
                Position.status == "open",
            ).order_by(Position.created_at.desc())
        )
        return result.scalars().all()

    # ── LLM Placeholder ──────────────────────────────────────────

    async def _generate_llm_content(self, prompt: str, context: dict) -> str:
        """Placeholder for LLM content generation.

        In production, this would call the configured LLM provider
        with the given prompt and context data.

        Returns a structured placeholder string.
        """
        # Mock: generate a deterministic response based on context
        scenario = context.get("scenario", "unknown")
        return (
            f"[AI分析-{scenario}] 基于当前数据自动生成：{prompt[:100]}...\n"
            f"上下文: {list(context.keys())}"
        )

    # ══════════════════════════════════════════════════════════════
    # Scenario 1: Resume Arrival Check
    # ══════════════════════════════════════════════════════════════

    async def check_resume_arrival(self, tenant_id: str) -> list[ProactiveAlert]:
        """新简历到达 → 分析匹配度 → 建议操作。

        Checks for resumes parsed in the last 24 hours, evaluates
        match potential against open positions, and generates alerts
        for high-potential matches.
        """
        alerts: list[ProactiveAlert] = []
        recent_resumes = await self._get_recent_resumes(tenant_id, hours=24)
        open_positions = await self._get_open_positions(tenant_id)

        if not recent_resumes:
            return alerts

        for resume in recent_resumes:
            # Determine candidate from resume
            candidate = None
            if resume.candidate_id:
                candidate = await self.db.scalar(
                    select(Candidate).where(Candidate.id == resume.candidate_id)
                )

            candidate_name = "未知候选人"
            if candidate and candidate.name:
                candidate_name = candidate.name

            # Evaluate match potential (mock scoring)
            match_score = 0.0
            best_position = None
            best_position_title = ""

            for pos in open_positions:
                # Simple mock: score based on credibility and position headcount
                score = 0.5
                if candidate and candidate.credibility_score:
                    score = min(candidate.credibility_score / 100.0, 1.0)
                if score > match_score:
                    match_score = score
                    best_position = pos
                    best_position_title = pos.title

            # Only alert for high-potential matches (>0.7)
            if match_score >= 0.7 and best_position:
                content = (
                    f"新候选人「{candidate_name}」与岗位「{best_position_title}」"
                    f"匹配度较高（{match_score:.0%}），建议优先安排匹配评估。"
                    f"\n简历ID: {resume.id}"
                )

                # LLM enhancement (placeholder)
                llm_content = await self._generate_llm_content(
                    f"分析候选人{candidate_name}与岗位{best_position_title}的匹配建议",
                    {"scenario": "resume_arrival", "match_score": match_score},
                )
                content += f"\n\n{llm_content}"

                alerts.append(_make_alert(
                    scenario_type="resume_arrival",
                    title=f"高匹配新简历: {candidate_name} → {best_position_title}",
                    content=content,
                    severity="info",
                    entity_id=resume.candidate_id,
                    entity_type="candidate",
                    action_suggestion=f"建议立即为该候选人发起与「{best_position_title}」的匹配评估",
                ))

        if len(recent_resumes) > 10:
            alerts.append(_make_alert(
                scenario_type="resume_arrival",
                title=f"简历涌入提醒: 过去24小时收到{len(recent_resumes)}份简历",
                content=(
                    f"过去24小时内共收到{len(recent_resumes)}份简历，"
                    f"当前有{len(open_positions)}个在招岗位。"
                    f"建议及时处理简历筛选以避免积压。"
                ),
                severity="info",
                action_suggestion="建议批量处理简历筛选",
            ))

        return alerts

    # ══════════════════════════════════════════════════════════════
    # Scenario 2: Match Anomaly Detection
    # ══════════════════════════════════════════════════════════════

    async def check_match_anomaly(self, tenant_id: str) -> list[ProactiveAlert]:
        """匹配异常检测 — 高匹配无面试、低匹配被推进 → 预警。

        Identifies candidates with unusual matching patterns:
        - High credibility but stuck at early stages (no interview)
        - Low credibility but advanced to late stages (interview/offer)
        """
        alerts: list[ProactiveAlert] = []

        # High match, no interview: screened but not interviewed
        high_match_stuck = await self.db.execute(
            select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
                Candidate.stage == "screened",
                Candidate.credibility_score >= 70,
            ).limit(20)
        )
        stuck_candidates = high_match_stuck.scalars().all()

        for c in stuck_candidates:
            content = (
                f"候选人「{c.name or '未知'}」（可信度评分: {c.credibility_score}）"
                f"已通过筛选但尚未安排面试，停留在screened阶段。"
                f"高匹配度候选人可能流失，建议尽快安排面试。"
            )
            llm_content = await self._generate_llm_content(
                f"高匹配候选人{c.name}未安排面试的风险分析",
                {"scenario": "match_anomaly", "score": c.credibility_score},
            )

            alerts.append(_make_alert(
                scenario_type="match_anomaly",
                title=f"高匹配无面试: {c.name or '未知'} (评分{c.credibility_score})",
                content=content + f"\n\n{llm_content}",
                severity="warning",
                entity_id=c.id,
                entity_type="candidate",
                action_suggestion="建议立即安排面试，避免优秀候选人流失",
            ))

        # Low match, advanced: low credibility at interview+ stages
        low_match_advanced = await self.db.execute(
            select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
                Candidate.stage.in_(["interviewed", "offered"]),
                Candidate.credibility_score <= 40,
            ).limit(20)
        )
        advanced_candidates = low_match_advanced.scalars().all()

        for c in advanced_candidates:
            content = (
                f"候选人「{c.name or '未知'}」（可信度评分: {c.credibility_score}）"
                f"评分较低但已推进至{c.stage}阶段，可能存在匹配偏差。"
                f"建议重新评估该候选人的岗位适配度。"
            )

            alerts.append(_make_alert(
                scenario_type="match_anomaly",
                title=f"低匹配被推进: {c.name or '未知'} @ {c.stage}",
                content=content,
                severity="warning",
                entity_id=c.id,
                entity_type="candidate",
                action_suggestion="建议重新进行匹配评估，确认是否继续推进",
            ))

        return alerts

    # ══════════════════════════════════════════════════════════════
    # Scenario 3: Interview Timeout Check
    # ══════════════════════════════════════════════════════════════

    async def check_interview_timeout(self, tenant_id: str) -> list[ProactiveAlert]:
        """面试超时检测 — 待反馈超过24h → 催促提醒。

        Finds completed interviews that have no feedback submitted
        for over 24 hours.
        """
        alerts: list[ProactiveAlert] = []
        cutoff = _now() - timedelta(hours=24)

        # Find interviews completed but without feedback
        timeout_interviews = await self.db.execute(
            select(Interview).where(
                Interview.tenant_id == tenant_id,
                Interview.status == "completed",
                Interview.updated_at < cutoff,
            ).order_by(Interview.updated_at.asc()).limit(30)
        )
        interviews = timeout_interviews.scalars().all()

        for iv in interviews:
            # Get candidate info
            candidate = await self.db.scalar(
                select(Candidate).where(Candidate.id == iv.candidate_id)
            )
            candidate_name = candidate.name if candidate else "未知"

            # Calculate hours since completion
            hours_elapsed = int((_now() - iv.updated_at).total_seconds() / 3600)

            content = (
                f"候选人「{candidate_name}」的面试（{iv.interview_type or '技术面'}）"
                f"已完成{hours_elapsed}小时，但尚未收到面试官反馈。"
                f"面试轮次: 第{iv.round_number}轮"
            )

            if hours_elapsed > 48:
                severity = "urgent"
                suggestion = f"⚠️ 已超时{hours_elapsed}小时，建议立即联系面试官提交反馈"
            else:
                severity = "warning"
                suggestion = f"已超过24小时，建议发送催促提醒"

            llm_content = await self._generate_llm_content(
                f"面试反馈催促: {candidate_name} 第{iv.round_number}轮",
                {"scenario": "interview_timeout", "hours": hours_elapsed},
            )

            alerts.append(_make_alert(
                scenario_type="interview_timeout",
                title=f"面试反馈超时: {candidate_name} ({hours_elapsed}h)",
                content=content + f"\n\n{llm_content}",
                severity=severity,
                entity_id=iv.id,
                entity_type="interview",
                action_suggestion=suggestion,
            ))

        return alerts

    # ══════════════════════════════════════════════════════════════
    # Scenario 4: Offer Stale Check
    # ══════════════════════════════════════════════════════════════

    async def check_offer_stale(self, tenant_id: str) -> list[ProactiveAlert]:
        """Offer僵局检测 — 发送超3天无回应 → 跟进建议。

        Finds offers sent more than 3 days ago with no candidate response.
        """
        alerts: list[ProactiveAlert] = []
        cutoff = _now() - timedelta(days=3)

        stale_offers = await self.db.execute(
            select(Offer).where(
                Offer.tenant_id == tenant_id,
                Offer.status.in_(["sent", "pending_approval"]),
                Offer.created_at < cutoff,
            ).order_by(Offer.created_at.asc()).limit(30)
        )
        offers = stale_offers.scalars().all()

        for offer in offers:
            # Get candidate info
            candidate = await self.db.scalar(
                select(Candidate).where(Candidate.id == offer.candidate_id)
            )
            candidate_name = candidate.name if candidate else "未知"

            # Get position info
            position_title = ""
            if offer.position_id:
                pos = await self.db.scalar(
                    select(Position).where(Position.id == offer.position_id)
                )
                if pos:
                    position_title = pos.title

            days_elapsed = (_now() - offer.created_at).days

            content = (
                f"候选人「{candidate_name}」的Offer（岗位: {position_title}）"
                f"已发送{days_elapsed}天，状态为{offer.status}，候选人尚未回应。"
                f"\nOffer金额: base={offer.base_salary or 'N/A'}/月"
            )

            llm_content = await self._generate_llm_content(
                f"Offer僵局分析: {candidate_name} {position_title}",
                {"scenario": "offer_stale", "days": days_elapsed, "status": offer.status},
            )

            severity = "urgent" if days_elapsed > 7 else "warning"
            if days_elapsed > 7:
                suggestion = (
                    f"Offer已僵持{days_elapsed}天，建议：\n"
                    f"1. 联系候选人了解犹豫原因\n"
                    f"2. 考虑调整薪资/福利方案\n"
                    f"3. 准备备选候选人"
                )
            else:
                suggestion = f"建议主动联系候选人，了解对方意向和顾虑"

            alerts.append(_make_alert(
                scenario_type="offer_stale",
                title=f"Offer僵局: {candidate_name} ({days_elapsed}天无回应)",
                content=content + f"\n\n{llm_content}",
                severity=severity,
                entity_id=offer.id,
                entity_type="offer",
                action_suggestion=suggestion,
            ))

        return alerts

    # ══════════════════════════════════════════════════════════════
    # Scenario 5: Funnel Bottleneck Detection
    # ══════════════════════════════════════════════════════════════

    async def check_funnel_bottleneck(self, tenant_id: str) -> list[ProactiveAlert]:
        """漏斗瓶颈检测 → 改进建议。

        Analyzes the recruitment funnel to identify stages with
        abnormally low conversion rates.
        """
        alerts: list[ProactiveAlert] = []
        pipeline_counts = await self._get_pipeline_counts(tenant_id)

        stages_ordered = ["applied", "screened", "interviewed", "offered", "hired"]
        total_applied = pipeline_counts.get("applied", 0)

        if total_applied == 0:
            return alerts

        # Check each transition for bottlenecks
        bottleneck_thresholds = {
            ("applied", "screened"): 0.50,    # Expected: 50%+ pass screening
            ("screened", "interviewed"): 0.60, # Expected: 60%+ get interviews
            ("interviewed", "offered"): 0.30,  # Expected: 30%+ get offers
            ("offered", "hired"): 0.60,        # Expected: 60%+ accept
        }

        for (from_stage, to_stage), threshold in bottleneck_thresholds.items():
            from_count = pipeline_counts.get(from_stage, 0)
            to_count = pipeline_counts.get(to_stage, 0)

            if from_count == 0:
                continue

            conversion = to_count / from_count
            if conversion < threshold and from_count >= 5:
                content = (
                    f"招聘漏斗瓶颈：{from_stage} → {to_stage} 转化率仅{conversion:.1%}，"
                    f"低于预期{threshold:.0%}。\n"
                    f"当前数据: {from_stage}={from_count}, {to_stage}={to_count}"
                )

                # Stage-specific recommendations
                recommendations = {
                    ("applied", "screened"): "建议优化简历筛选标准或增加筛选人力",
                    ("screened", "interviewed"): "建议检查面试官排期，加快面试安排速度",
                    ("interviewed", "offered"): "建议统一面试评估标准，减少决策犹豫",
                    ("offered", "hired"): "建议优化Offer竞争力或加强候选人沟通",
                }
                recommendation = recommendations.get((from_stage, to_stage), "")
                content += f"\n建议: {recommendation}"

                llm_content = await self._generate_llm_content(
                    f"漏斗瓶颈分析: {from_stage}→{to_stage}",
                    {
                        "scenario": "funnel_bottleneck",
                        "from": from_count,
                        "to": to_count,
                        "conversion": conversion,
                    },
                )

                alerts.append(_make_alert(
                    scenario_type="funnel_bottleneck",
                    title=f"漏斗瓶颈: {from_stage}→{to_stage} ({conversion:.1%})",
                    content=content + f"\n\n{llm_content}",
                    severity="warning" if conversion < threshold * 0.5 else "info",
                    action_suggestion=recommendation,
                ))

        # Overall funnel health check
        total_hired = pipeline_counts.get("hired", 0)
        overall_rate = total_hired / total_applied if total_applied > 0 else 0
        if overall_rate < 0.05 and total_applied >= 20:
            alerts.append(_make_alert(
                scenario_type="funnel_bottleneck",
                title=f"整体转化率偏低: {overall_rate:.1%}",
                content=(
                    f"当前整体招聘转化率（applied→hired）仅{overall_rate:.1%}，"
                    f"远低于行业基准5-15%。共{total_applied}名候选人，仅{total_hired}人入职。"
                ),
                severity="urgent",
                action_suggestion="建议全面审视招聘流程，从源头质量到各环节转化效率进行系统性优化",
            ))

        return alerts

    # ══════════════════════════════════════════════════════════════
    # Scenario 6: Silent Activation
    # ══════════════════════════════════════════════════════════════

    async def check_silent_activation(self, tenant_id: str) -> list[ProactiveAlert]:
        """沉默候选人激活 — 匹配新岗位 → 推荐激活。

        Finds inactive candidates whose profiles match newly opened
        positions, suggesting re-engagement.
        """
        alerts: list[ProactiveAlert] = []

        # Find recently opened positions (last 7 days)
        recent_cutoff = _now() - timedelta(days=7)
        new_positions = await self.db.execute(
            select(Position).where(
                Position.tenant_id == tenant_id,
                Position.status == "open",
                Position.created_at >= recent_cutoff,
            ).limit(20)
        )
        positions = new_positions.scalars().all()

        if not positions:
            return alerts

        # Find inactive candidates (no activity in 30+ days)
        inactive_cutoff = _now() - timedelta(days=30)
        inactive_candidates = await self.db.execute(
            select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
                Candidate.stage == "rejected",
                Candidate.last_activity_at < inactive_cutoff,
            ).limit(50)
        )
        candidates = inactive_candidates.scalars().all()

        activation_count = 0
        for pos in positions:
            for c in candidates:
                # Simple matching logic (mock)
                # In production, use the matching service for real scoring
                match_score = 0.0

                # Check skill overlap from profile
                if c.profile and pos.requirements:
                    candidate_skills = set(
                        s.lower()
                        for s in (c.profile.get("skills", []) or [])
                    )
                    if isinstance(pos.requirements, dict):
                        req_skills = set(
                            s.lower()
                            for s in pos.requirements.get("required_skills", [])
                        )
                    else:
                        req_skills = set()

                    if candidate_skills and req_skills:
                        overlap = candidate_skills & req_skills
                        match_score = len(overlap) / len(req_skills) if req_skills else 0

                # Boost by credibility score
                if c.credibility_score and c.credibility_score > 60:
                    match_score = min(match_score + 0.2, 1.0)

                if match_score >= 0.5:
                    activation_count += 1
                    content = (
                        f"候选人「{c.name or '未知'}」此前曾投递但未通过，"
                        f"但与新发布的岗位「{pos.title}」存在较高匹配度（{match_score:.0%}）。\n"
                        f"候选人最近30天无活动，建议主动联系。"
                    )

                    alerts.append(_make_alert(
                        scenario_type="silent_activation",
                        title=f"沉默候选人激活: {c.name or '未知'} → {pos.title}",
                        content=content,
                        severity="info",
                        entity_id=c.id,
                        entity_type="candidate",
                        action_suggestion=f"建议主动联系该候选人，推荐「{pos.title}」岗位",
                    ))

                    if activation_count >= 10:
                        break
            if activation_count >= 10:
                break

        return alerts

    # ══════════════════════════════════════════════════════════════
    # Scenario 7: Daily Digest
    # ══════════════════════════════════════════════════════════════

    async def generate_daily_digest(self, tenant_id: str) -> ProactiveAlert:
        """生成招聘日报。

        Aggregates today's recruitment activity into a daily digest
        with highlights, concerns, and action items.
        """
        today_start = _now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Today's metrics
        new_candidates = await self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.created_at >= today_start,
            )
        ) or 0

        interviews_today = await self.db.scalar(
            select(func.count()).select_from(Interview).where(
                Interview.tenant_id == tenant_id,
                Interview.scheduled_at >= today_start,
                Interview.scheduled_at < _now(),
            )
        ) or 0

        offers_today = await self.db.scalar(
            select(func.count()).select_from(Offer).where(
                Offer.tenant_id == tenant_id,
                Offer.created_at >= today_start,
            )
        ) or 0

        hires_today = await self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.stage == "hired",
                Candidate.updated_at >= today_start,
            )
        ) or 0

        open_positions = await self.db.scalar(
            select(func.count()).select_from(Position).where(
                Position.tenant_id == tenant_id,
                Position.status == "open",
            )
        ) or 0

        pipeline_counts = await self._get_pipeline_counts(tenant_id)
        total_pipeline = sum(pipeline_counts.values()) - pipeline_counts.get("rejected", 0)

        # Pending items
        pending_feedback = await self.db.scalar(
            select(func.count()).select_from(Interview).where(
                Interview.tenant_id == tenant_id,
                Interview.status == "completed",
            )
        ) or 0

        pending_offers = await self.db.scalar(
            select(func.count()).select_from(Offer).where(
                Offer.tenant_id == tenant_id,
                Offer.status.in_(["draft", "sent", "pending_approval"]),
            )
        ) or 0

        # Build daily report
        date_str = _now().strftime("%Y-%m-%d")
        content = (
            f"📋 HireMind 招聘日报 — {date_str}\n"
            f"{'=' * 40}\n\n"
            f"📊 今日数据:\n"
            f"  • 新增候选人: {new_candidates}\n"
            f"  • 面试安排: {interviews_today}\n"
            f"  • 新发Offer: {offers_today}\n"
            f"  • 今日入职: {hires_today}\n\n"
            f"📈 当前状态:\n"
            f"  • 在招岗位: {open_positions}\n"
            f"  • 管道候选人: {total_pipeline}\n"
            f"  • 待反馈面试: {pending_feedback}\n"
            f"  • 待处理Offer: {pending_offers}\n\n"
        )

        # Highlights and concerns
        highlights = []
        concerns = []
        if hires_today > 0:
            highlights.append(f"🎉 今日有{hires_today}位候选人成功入职！")
        if new_candidates > 10:
            highlights.append(f"📈 收到{new_candidates}份新简历，招聘需求旺盛")
        if offers_today > 0:
            highlights.append(f"💼 今日发出{offers_today}份Offer")

        if pending_feedback > 5:
            concerns.append(f"⚠️ {pending_feedback}场面试待反馈，可能影响候选人体验")
        if pending_offers > 3:
            concerns.append(f"⚠️ {pending_offers}份Offer待处理，建议尽快推进")

        if highlights:
            content += "✅ 亮点:\n" + "\n".join(f"  {h}" for h in highlights) + "\n\n"
        if concerns:
            content += "⚠️ 关注:\n" + "\n".join(f"  {c}" for c in concerns) + "\n\n"

        # LLM summary (placeholder)
        llm_content = await self._generate_llm_content(
            "生成今日招聘日报总结和建议",
            {
                "scenario": "daily_report",
                "new_candidates": new_candidates,
                "hires": hires_today,
                "open_positions": open_positions,
            },
        )
        content += f"💡 AI建议:\n{llm_content}"

        action_items = []
        if pending_feedback > 0:
            action_items.append(f"催促{pending_feedback}场面试的反馈提交")
        if pending_offers > 0:
            action_items.append(f"处理{pending_offers}份待审批Offer")

        return _make_alert(
            scenario_type="daily_report",
            title=f"📋 招聘日报 — {date_str}",
            content=content,
            severity="info",
            action_suggestion="; ".join(action_items) if action_items else None,
        )

    # ══════════════════════════════════════════════════════════════
    # Scenario 8: Weekly Digest
    # ══════════════════════════════════════════════════════════════

    async def generate_weekly_digest(self, tenant_id: str) -> ProactiveAlert:
        """生成招聘周报。

        Aggregates the past week's recruitment data with comparisons
        to the previous week, including trends and strategic recommendations.
        """
        now = _now()
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        prev_week_start = week_start - timedelta(days=7)

        # This week's metrics
        this_week_candidates = await self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.created_at >= week_start,
            )
        ) or 0

        this_week_interviews = await self.db.scalar(
            select(func.count()).select_from(Interview).where(
                Interview.tenant_id == tenant_id,
                Interview.created_at >= week_start,
            )
        ) or 0

        this_week_offers = await self.db.scalar(
            select(func.count()).select_from(Offer).where(
                Offer.tenant_id == tenant_id,
                Offer.created_at >= week_start,
            )
        ) or 0

        this_week_hires = await self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.stage == "hired",
                Candidate.updated_at >= week_start,
            )
        ) or 0

        # Previous week's metrics for comparison
        prev_week_candidates = await self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.created_at >= prev_week_start,
                Candidate.created_at < week_start,
            )
        ) or 0

        prev_week_hires = await self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.stage == "hired",
                Candidate.updated_at >= prev_week_start,
                Candidate.updated_at < week_start,
            )
        ) or 0

        # Pipeline overview
        pipeline_counts = await self._get_pipeline_counts(tenant_id)
        open_positions = await self.db.scalar(
            select(func.count()).select_from(Position).where(
                Position.tenant_id == tenant_id,
                Position.status == "open",
            )
        ) or 0

        # Source distribution
        source_result = await self.db.execute(
            select(Candidate.source, func.count().label("count"))
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.created_at >= week_start,
            )
            .group_by(Candidate.source)
        )
        sources = {row.source or "unknown": row.count for row in source_result.all()}

        # Calculate week-over-week changes
        def _wow_change(current: int, previous: int) -> str:
            if previous == 0:
                return "+∞" if current > 0 else "0%"
            change = round((current - previous) / previous * 100, 1)
            return f"+{change}%" if change > 0 else f"{change}%"

        week_str = f"{week_start.strftime('%m/%d')} - {now.strftime('%m/%d')}"
        content = (
            f"📊 HireMind 招聘周报 — {week_str}\n"
            f"{'=' * 40}\n\n"
            f"📊 本周核心数据:\n"
            f"  • 新增候选人: {this_week_candidates} ({_wow_change(this_week_candidates, prev_week_candidates)})\n"
            f"  • 面试安排: {this_week_interviews}\n"
            f"  • Offer发出: {this_week_offers}\n"
            f"  • 成功入职: {this_week_hires} ({_wow_change(this_week_hires, prev_week_hires)})\n\n"
            f"📈 管道概览:\n"
            f"  • 在招岗位: {open_positions}\n"
        )
        for stage, count in pipeline_counts.items():
            content += f"  • {stage}: {count}\n"

        if sources:
            content += f"\n📢 本周来源分布:\n"
            for src, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
                content += f"  • {src}: {count}\n"

        # Strategic insights
        content += "\n"
        if this_week_hires > 0:
            content += f"✅ 本周完成{this_week_hires}位候选人入职，招聘效率良好。\n"
        if this_week_candidates < prev_week_candidates and prev_week_candidates > 0:
            content += f"⚠️ 本周新增候选人环比下降，建议检查招聘渠道效果。\n"
        if open_positions > 10 and this_week_hires < 2:
            content += f"⚠️ 在招岗位{open_positions}个但入职仅{this_week_hires}人，需加快招聘进度。\n"

        # LLM strategic recommendations (placeholder)
        llm_content = await self._generate_llm_content(
            "基于本周数据提供下周招聘策略建议",
            {
                "scenario": "weekly_report",
                "candidates": this_week_candidates,
                "hires": this_week_hires,
                "open_positions": open_positions,
                "sources": sources,
            },
        )
        content += f"\n💡 AI策略建议:\n{llm_content}"

        return _make_alert(
            scenario_type="weekly_report",
            title=f"📊 招聘周报 — {week_str}",
            content=content,
            severity="info",
            action_suggestion="请查阅周报详情，关注数据变化趋势并制定下周计划",
        )

    # ══════════════════════════════════════════════════════════════
    # Run All Scenarios
    # ══════════════════════════════════════════════════════════════

    async def run_all_scenarios(self, tenant_id: str) -> list[ProactiveAlert]:
        """运行所有主动式AI场景，返回合并后的 ProactiveAlert 列表。

        Executes all 8 scenarios and aggregates their alerts.
        Sorts by severity (urgent > warning > info).
        """
        all_alerts: list[ProactiveAlert] = []

        # Scenario 1: Resume arrival
        try:
            alerts = await self.check_resume_arrival(tenant_id)
            all_alerts.extend(alerts)
            logger.info("resume_arrival: %d alerts", len(alerts))
        except Exception as e:
            logger.error("resume_arrival error: %s", e)

        # Scenario 2: Match anomaly
        try:
            alerts = await self.check_match_anomaly(tenant_id)
            all_alerts.extend(alerts)
            logger.info("match_anomaly: %d alerts", len(alerts))
        except Exception as e:
            logger.error("match_anomaly error: %s", e)

        # Scenario 3: Interview timeout
        try:
            alerts = await self.check_interview_timeout(tenant_id)
            all_alerts.extend(alerts)
            logger.info("interview_timeout: %d alerts", len(alerts))
        except Exception as e:
            logger.error("interview_timeout error: %s", e)

        # Scenario 4: Offer stale
        try:
            alerts = await self.check_offer_stale(tenant_id)
            all_alerts.extend(alerts)
            logger.info("offer_stale: %d alerts", len(alerts))
        except Exception as e:
            logger.error("offer_stale error: %s", e)

        # Scenario 5: Funnel bottleneck
        try:
            alerts = await self.check_funnel_bottleneck(tenant_id)
            all_alerts.extend(alerts)
            logger.info("funnel_bottleneck: %d alerts", len(alerts))
        except Exception as e:
            logger.error("funnel_bottleneck error: %s", e)

        # Scenario 6: Silent activation
        try:
            alerts = await self.check_silent_activation(tenant_id)
            all_alerts.extend(alerts)
            logger.info("silent_activation: %d alerts", len(alerts))
        except Exception as e:
            logger.error("silent_activation error: %s", e)

        # Scenario 7: Daily digest
        try:
            alert = await self.generate_daily_digest(tenant_id)
            all_alerts.append(alert)
            logger.info("daily_digest: generated")
        except Exception as e:
            logger.error("daily_digest error: %s", e)

        # Scenario 8: Weekly digest
        try:
            alert = await self.generate_weekly_digest(tenant_id)
            all_alerts.append(alert)
            logger.info("weekly_digest: generated")
        except Exception as e:
            logger.error("weekly_digest error: %s", e)

        # Sort by severity: urgent > warning > info
        severity_order = {"urgent": 0, "warning": 1, "info": 2}
        all_alerts.sort(key=lambda a: severity_order.get(a.severity, 3))

        logger.info(
            "run_all_scenarios complete: %d total alerts for tenant=%s",
            len(all_alerts), tenant_id,
        )
        return all_alerts
