"""
Dashboard AI Service — AI-powered dashboard insights and report generation.

Provides:
  - generate_insights(): AI-generated trend insights, risk alerts, action suggestions
  - generate_daily_report(): Daily recruitment report with highlights and concerns
  - generate_weekly_report(): Weekly recruitment report with comparisons
  - analyze_funnel_bottleneck(): Identify funnel bottlenecks and suggest improvements

All LLM calls use structured prompts with real data. Currently uses placeholder
responses — the interface is complete and ready to be wired to a real LLM provider.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.offer import Offer
from app.models.position import Position
from app.models.resume import Resume
from app.schemas.dashboard import (
    AIInsight,
    AIInsightsResponse,
    ReportResponse,
)

logger = logging.getLogger("hiremind.services.dashboard_ai")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _format_date(d: date | datetime) -> str:
    """Format date to YYYY-MM-DD string."""
    if isinstance(d, datetime):
        return d.strftime("%Y-%m-%d")
    return d.isoformat()


# ---------------------------------------------------------------------------
# DashboardAIService
# ---------------------------------------------------------------------------

class DashboardAIService:
    """
    AI-powered dashboard analytics and report generation.

    Generates insights from recruitment data, produces daily/weekly reports,
    and analyzes funnel bottlenecks.
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

    async def _get_period_metrics(
        self, tenant_id: str, start: datetime, end: datetime
    ) -> dict[str, int | float]:
        """Get aggregated metrics for a specific time period."""
        # New candidates in period
        new_candidates = await self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.created_at >= start,
                Candidate.created_at <= end,
            )
        ) or 0

        # Interviews in period
        interviews = await self.db.scalar(
            select(func.count()).select_from(Interview).where(
                Interview.tenant_id == tenant_id,
                Interview.scheduled_at >= start,
                Interview.scheduled_at <= end,
            )
        ) or 0

        # Offers in period
        offers = await self.db.scalar(
            select(func.count()).select_from(Offer).where(
                Offer.tenant_id == tenant_id,
                Offer.created_at >= start,
                Offer.created_at <= end,
            )
        ) or 0

        # Hired in period
        hired = await self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.stage == "hired",
                Candidate.updated_at >= start,
                Candidate.updated_at <= end,
            )
        ) or 0

        # Resumes parsed in period
        resumes_parsed = await self.db.scalar(
            select(func.count()).select_from(Resume).where(
                Resume.tenant_id == tenant_id,
                Resume.parse_status == "completed",
                Resume.created_at >= start,
                Resume.created_at <= end,
            )
        ) or 0

        # Open positions
        open_positions = await self.db.scalar(
            select(func.count()).select_from(Position).where(
                Position.tenant_id == tenant_id,
                Position.status == "open",
            )
        ) or 0

        return {
            "new_candidates": new_candidates,
            "interviews": interviews,
            "offers": offers,
            "hired": hired,
            "resumes_parsed": resumes_parsed,
            "open_positions": open_positions,
        }

    async def _get_source_breakdown(self, tenant_id: str) -> list[dict[str, Any]]:
        """Get candidate count by source."""
        result = await self.db.execute(
            select(
                Candidate.source,
                func.count().label("total"),
            )
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
            )
            .group_by(Candidate.source)
        )
        rows = result.all()
        return [
            {"source": row.source or "unknown", "count": row.total}
            for row in rows
        ]

    # ── LLM Placeholder ──────────────────────────────────────────

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Placeholder for LLM call.

        In production, this would call OpenAI / Azure / other LLM provider.
        Currently returns structured placeholder text.
        """
        # TODO: Wire to real LLM provider (OpenAI / Azure OpenAI / etc.)
        logger.info("LLM call (placeholder): system=%s..., user=%s...",
                     system_prompt[:80], user_prompt[:80])
        return ""

    # ── generate_insights ────────────────────────────────────────

    async def generate_insights(self, tenant_id: str) -> AIInsightsResponse:
        """
        Generate AI-powered insights for the dashboard.

        Analyzes current recruitment trends and produces:
        - Trend insights (hiring velocity changes)
        - Risk alerts (overdue positions, funnel bottlenecks)
        - Opportunities (high-quality candidate pools)
        - Action recommendations

        Returns:
            AIInsightsResponse with multiple categorized insights.
        """
        now = _now()
        insights: list[AIInsight] = []

        # Gather current data
        pipeline = await self._get_pipeline_counts(tenant_id)
        this_week_start = now - timedelta(days=now.weekday())
        this_week_start = this_week_start.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        last_week_start = this_week_start - timedelta(days=7)
        last_week_end = this_week_start - timedelta(microseconds=1)

        this_week_metrics = await self._get_period_metrics(
            tenant_id, this_week_start, now
        )
        last_week_metrics = await self._get_period_metrics(
            tenant_id, last_week_start, last_week_end
        )

        # Build context for AI analysis
        context = {
            "pipeline": pipeline,
            "this_week": this_week_metrics,
            "last_week": last_week_metrics,
            "total_in_pipeline": sum(
                v for k, v in pipeline.items()
                if k not in ("hired", "rejected")
            ),
        }

        system_prompt = (
            "你是一个专业的招聘数据分析师。基于提供的招聘数据，生成洞察报告。"
            "请从以下维度分析：\n"
            "1. 趋势分析：招聘速度、候选人流入流出趋势\n"
            "2. 风险提示：岗位超期、漏斗瓶颈、候选人流失\n"
            "3. 机会识别：高质量候选人池、即将完成的招聘\n"
            "4. 行动建议：具体可执行的改进措施\n"
            "请用 JSON 格式返回，格式为：\n"
            '[{"category": "trend/risk/opportunity/recommendation", '
            '"title": "...", "content": "...", "confidence": 0.8, '
            '"action_suggestion": "..."}]'
        )

        user_prompt = f"以下是当前招聘数据：\n{json.dumps(context, ensure_ascii=False, default=str)}"

        # Try LLM call; fall back to rule-based insights
        llm_response = self._call_llm(system_prompt, user_prompt)

        if llm_response:
            try:
                parsed = json.loads(llm_response)
                for i, item in enumerate(parsed[:10]):
                    insights.append(AIInsight(
                        id=f"insight-{uuid.uuid4().hex[:8]}",
                        category=item.get("category", "recommendation"),
                        title=item.get("title", ""),
                        content=item.get("content", ""),
                        confidence=item.get("confidence", 0.7),
                        action_suggestion=item.get("action_suggestion"),
                        created_at=now,
                    ))
            except (json.JSONDecodeError, KeyError):
                insights = self._generate_rule_based_insights(
                    pipeline, this_week_metrics, last_week_metrics, now
                )
        else:
            insights = self._generate_rule_based_insights(
                pipeline, this_week_metrics, last_week_metrics, now
            )

        return AIInsightsResponse(insights=insights, generated_at=now)

    def _generate_rule_based_insights(
        self,
        pipeline: dict[str, int],
        this_week: dict[str, int | float],
        last_week: dict[str, int | float],
        now: datetime,
    ) -> list[AIInsight]:
        """Generate insights using rule-based logic as fallback."""
        insights: list[AIInsight] = []

        # 1) Pipeline health trend
        total_pipeline = sum(
            v for k, v in pipeline.items() if k not in ("hired", "rejected")
        )
        new_candidates_delta = (
            (this_week.get("new_candidates", 0) - last_week.get("new_candidates", 0))
        )
        if new_candidates_delta > 0:
            insights.append(AIInsight(
                id=f"insight-{uuid.uuid4().hex[:8]}",
                category="trend",
                title="候选人流入量上升",
                content=(
                    f"本周新增候选人 {this_week.get('new_candidates', 0)} 人，"
                    f"较上周增加 {new_candidates_delta} 人。"
                    f"当前管线中共有 {total_pipeline} 位候选人。"
                ),
                confidence=0.9,
                action_suggestion="建议加快筛选速度，避免候选人积压。",
                created_at=now,
            ))
        elif new_candidates_delta < 0:
            insights.append(AIInsight(
                id=f"insight-{uuid.uuid4().hex[:8]}",
                category="trend",
                title="候选人流入量下降",
                content=(
                    f"本周新增候选人 {this_week.get('new_candidates', 0)} 人，"
                    f"较上周减少 {abs(new_candidates_delta)} 人。"
                    f"需关注招聘渠道效果。"
                ),
                confidence=0.85,
                action_suggestion="建议检查各招聘渠道投放效果，考虑增加新的候选人来源。",
                created_at=now,
            ))
        else:
            insights.append(AIInsight(
                id=f"insight-{uuid.uuid4().hex[:8]}",
                category="trend",
                title="候选人流入稳定",
                content=(
                    f"本周新增候选人 {this_week.get('new_candidates', 0)} 人，"
                    f"与上周持平。当前管线 {total_pipeline} 人。"
                ),
                confidence=0.8,
                action_suggestion=None,
                created_at=now,
            ))

        # 2) Interview volume trend
        iv_delta = (
            this_week.get("interviews", 0) - last_week.get("interviews", 0)
        )
        if this_week.get("interviews", 0) > 0:
            direction = "增加" if iv_delta > 0 else "减少" if iv_delta < 0 else "持平"
            insights.append(AIInsight(
                id=f"insight-{uuid.uuid4().hex[:8]}",
                category="trend",
                title=f"本周面试安排{direction}",
                content=(
                    f"本周安排面试 {this_week.get('interviews', 0)} 场，"
                    f"较上周{direction} {abs(iv_delta)} 场。"
                ),
                confidence=0.85,
                action_suggestion=(
                    "确保面试官时间充裕，提前准备面试评价表。"
                    if iv_delta > 0 else None
                ),
                created_at=now,
            ))

        # 3) Hiring velocity
        hired_this = this_week.get("hired", 0)
        hired_last = last_week.get("hired", 0)
        if hired_this > 0:
            insights.append(AIInsight(
                id=f"insight-{uuid.uuid4().hex[:8]}",
                category="opportunity",
                title="本周有候选人入职",
                content=f"本周成功招聘 {hired_this} 人，上周为 {hired_last} 人。",
                confidence=0.95,
                action_suggestion="及时更新岗位状态，安排入职流程。",
                created_at=now,
            ))

        # 4) Funnel bottleneck detection
        applied = pipeline.get("applied", 0)
        screened = pipeline.get("screened", 0)
        interviewed = pipeline.get("interviewed", 0)
        offered = pipeline.get("offered", 0)

        if applied > 0:
            screen_rate = screened / applied if applied > 0 else 0
            if screen_rate < 0.3 and applied > 10:
                insights.append(AIInsight(
                    id=f"insight-{uuid.uuid4().hex[:8]}",
                    category="risk",
                    title="简历筛选转化率偏低",
                    content=(
                        f"当前有 {applied} 位候选人处于已申请阶段，"
                        f"但仅 {screened} 位通过筛选（转化率 {screen_rate:.1%}）。"
                    ),
                    confidence=0.8,
                    action_suggestion="建议检查职位要求是否过于严格，或加速简历筛选流程。",
                    created_at=now,
                ))

            if interviewed > 0:
                offer_rate = offered / interviewed if interviewed > 0 else 0
                if offer_rate < 0.2 and interviewed > 5:
                    insights.append(AIInsight(
                        id=f"insight-{uuid.uuid4().hex[:8]}",
                        category="risk",
                        title="面试到Offer转化率偏低",
                        content=(
                            f"已完成面试 {interviewed} 人，"
                            f"但仅 {offered} 人进入Offer阶段（转化率 {offer_rate:.1%}）。"
                        ),
                        confidence=0.75,
                        action_suggestion="建议回顾面试标准和候选人匹配度，确保面试流程高效。",
                        created_at=now,
                    ))

        # 5) Open positions without activity
        open_pos = this_week.get("open_positions", 0)
        new_cand = this_week.get("new_candidates", 0)
        if open_pos > 0 and new_cand == 0:
            insights.append(AIInsight(
                id=f"insight-{uuid.uuid4().hex[:8]}",
                category="risk",
                title="在招岗位无新候选人",
                content=f"当前有 {open_pos} 个在招岗位，但本周无新增候选人。",
                confidence=0.7,
                action_suggestion="建议检查岗位发布渠道，考虑主动搜索候选人。",
                created_at=now,
            ))

        # 6) General recommendation
        insights.append(AIInsight(
            id=f"insight-{uuid.uuid4().hex[:8]}",
            category="recommendation",
            title="定期回顾招聘数据",
            content="建议每周回顾招聘漏斗数据和渠道效果，及时调整招聘策略。",
            confidence=0.9,
            action_suggestion="查看本周招聘周报获取详细分析。",
            created_at=now,
        ))

        return insights

    # ── generate_daily_report ────────────────────────────────────

    async def generate_daily_report(
        self, tenant_id: str, target_date: date | None = None
    ) -> ReportResponse:
        """
        Generate a daily recruitment report.

        Includes:
        - Day's data summary
        - Key metric changes
        - Highlights and concerns
        - Action recommendations

        Args:
            tenant_id: Tenant identifier
            target_date: Report date (defaults to today)

        Returns:
            ReportResponse with structured daily report.
        """
        now = _now()
        target = target_date or date.today()

        # Date ranges
        day_start = datetime.combine(
            target, datetime.min.time()
        ).replace(tzinfo=timezone.utc)
        day_end = datetime.combine(
            target, datetime.max.time()
        ).replace(tzinfo=timezone.utc)

        # Previous day for comparison
        prev_date = target - timedelta(days=1)
        prev_start = datetime.combine(
            prev_date, datetime.min.time()
        ).replace(tzinfo=timezone.utc)
        prev_end = datetime.combine(
            prev_date, datetime.max.time()
        ).replace(tzinfo=timezone.utc)

        # Gather metrics
        today_metrics = await self._get_period_metrics(
            tenant_id, day_start, day_end
        )
        yesterday_metrics = await self._get_period_metrics(
            tenant_id, prev_start, prev_end
        )
        pipeline = await self._get_pipeline_counts(tenant_id)

        # Build metrics comparison
        metrics = {
            "today": today_metrics,
            "yesterday": yesterday_metrics,
            "pipeline": pipeline,
            "changes": {
                k: today_metrics.get(k, 0) - yesterday_metrics.get(k, 0)
                for k in (
                    "new_candidates", "interviews", "offers",
                    "hired", "resumes_parsed",
                )
            },
        }

        # Generate highlights and concerns
        highlights: list[str] = []
        concerns: list[str] = []
        recommendations: list[str] = []

        new_cand = today_metrics.get("new_candidates", 0)
        interviews = today_metrics.get("interviews", 0)
        hired = today_metrics.get("hired", 0)
        offers = today_metrics.get("offers", 0)

        if hired > 0:
            highlights.append(f"今日成功招聘 {hired} 人！")
        if new_cand > 5:
            highlights.append(f"新增候选人 {new_cand} 人，招聘渠道效果良好。")
        if interviews > 0:
            highlights.append(f"完成面试 {interviews} 场。")
        if offers > 0:
            highlights.append(f"新增 Offer {offers} 个。")

        if new_cand == 0:
            concerns.append("今日无新增候选人，建议检查招聘渠道。")
        if interviews == 0 and pipeline.get("interviewed", 0) > 0:
            concerns.append("有待面试候选人但今日无面试安排。")

        open_positions = today_metrics.get("open_positions", 0)
        if open_positions > 0:
            recommendations.append(f"关注 {open_positions} 个在招岗位的进展。")
        if pipeline.get("applied", 0) > 10:
            recommendations.append(
                f"有 {pipeline['applied']} 位候选人待筛选，建议安排时间处理。"
            )

        # Try LLM for summary
        system_prompt = (
            "你是一个招聘数据分析师。基于以下数据，生成一份简洁的日报摘要（100字以内）。"
            "包含：今日招聘进展概述、关键变化、需要注意的事项。"
        )
        user_prompt = json.dumps(metrics, ensure_ascii=False, default=str)
        llm_summary = self._call_llm(system_prompt, user_prompt)

        if not llm_summary:
            parts = []
            if new_cand > 0:
                parts.append(f"新增候选人 {new_cand} 人")
            if interviews > 0:
                parts.append(f"面试 {interviews} 场")
            if offers > 0:
                parts.append(f"新增Offer {offers} 个")
            if hired > 0:
                parts.append(f"成功招聘 {hired} 人")
            summary = f"{target.isoformat()} 招聘日报：" + (
                "，".join(parts) + "。" if parts else "今日无显著招聘活动。"
            )
        else:
            summary = llm_summary

        # Ensure minimum highlights
        if not highlights:
            highlights.append("今日无特别亮点。")
        if not concerns:
            concerns.append("暂无明显问题。")

        return ReportResponse(
            report_type="daily",
            title=f"招聘日报 - {target.isoformat()}",
            period=target.isoformat(),
            summary=summary,
            metrics=metrics,
            highlights=highlights,
            concerns=concerns,
            recommendations=recommendations,
            generated_at=now,
        )

    # ── generate_weekly_report ───────────────────────────────────

    async def generate_weekly_report(
        self, tenant_id: str
    ) -> ReportResponse:
        """
        Generate a weekly recruitment report.

        Includes:
        - Weekly data summary with trend analysis
        - Comparison with previous week
        - Highlights and concerns
        - Next week predictions and recommendations

        Args:
            tenant_id: Tenant identifier

        Returns:
            ReportResponse with structured weekly report.
        """
        now = _now()

        # This week boundaries (Monday to Sunday)
        today = now.date()
        this_monday = today - timedelta(days=today.weekday())
        this_week_start = datetime.combine(
            this_monday, datetime.min.time()
        ).replace(tzinfo=timezone.utc)
        this_week_end = now

        # Previous week
        last_monday = this_monday - timedelta(days=7)
        last_week_start = datetime.combine(
            last_monday, datetime.min.time()
        ).replace(tzinfo=timezone.utc)
        last_week_end = this_week_start - timedelta(microseconds=1)

        # Gather metrics
        this_week_metrics = await self._get_period_metrics(
            tenant_id, this_week_start, this_week_end
        )
        last_week_metrics = await self._get_period_metrics(
            tenant_id, last_week_start, last_week_end
        )
        pipeline = await self._get_pipeline_counts(tenant_id)
        source_breakdown = await self._get_source_breakdown(tenant_id)

        # Build metrics comparison
        metrics = {
            "this_week": this_week_metrics,
            "last_week": last_week_metrics,
            "pipeline": pipeline,
            "sources": source_breakdown,
            "week_over_week": {
                k: this_week_metrics.get(k, 0) - last_week_metrics.get(k, 0)
                for k in (
                    "new_candidates", "interviews", "offers",
                    "hired", "resumes_parsed",
                )
            },
        }

        # Analyze trends
        highlights: list[str] = []
        concerns: list[str] = []
        recommendations: list[str] = []

        new_cand = this_week_metrics.get("new_candidates", 0)
        interviews = this_week_metrics.get("interviews", 0)
        offers = this_week_metrics.get("offers", 0)
        hired = this_week_metrics.get("hired", 0)

        # Compare with last week
        cand_delta = new_cand - last_week_metrics.get("new_candidates", 0)
        iv_delta = interviews - last_week_metrics.get("interviews", 0)
        hired_delta = hired - last_week_metrics.get("hired", 0)

        if hired > 0:
            highlights.append(
                f"本周成功招聘 {hired} 人"
                + (f"（较上周{'增加' if hired_delta > 0 else '减少'} "
                   f"{abs(hired_delta)} 人）" if hired_delta != 0 else "。")
            )
        if new_cand > 0:
            highlights.append(
                f"新增候选人 {new_cand} 人"
                + (f"（较上周{'增加' if cand_delta > 0 else '减少'} "
                   f"{abs(cand_delta)} 人）" if cand_delta != 0 else "。")
            )
        if interviews > 0:
            highlights.append(f"完成面试 {interviews} 场。")

        # Funnel analysis
        total_pipeline = sum(
            v for k, v in pipeline.items() if k not in ("hired", "rejected")
        )
        if total_pipeline > 20:
            concerns.append(
                f"当前管线中有 {total_pipeline} 位候选人，建议加快流程推进。"
            )

        applied = pipeline.get("applied", 0)
        if applied > 15:
            concerns.append(
                f"有 {applied} 位候选人待筛选，存在积压风险。"
            )

        open_positions = this_week_metrics.get("open_positions", 0)
        if open_positions > 5:
            concerns.append(
                f"在招岗位 {open_positions} 个，需关注资源分配。"
            )

        # Source analysis
        if source_breakdown:
            top_source = max(source_breakdown, key=lambda x: x["count"])
            recommendations.append(
                f"最高效渠道为「{top_source['source']}」"
                f"（{top_source['count']} 位候选人），建议加大投入。"
            )

        recommendations.append("建议下周回顾本周招聘漏斗，优化低转化率环节。")

        # Try LLM for summary
        system_prompt = (
            "你是一个招聘数据分析师。基于以下周度数据，生成一份周报摘要（200字以内）。"
            "包含：本周招聘进展概述、与上周对比、下周预测和建议。"
        )
        user_prompt = json.dumps(metrics, ensure_ascii=False, default=str)
        llm_summary = self._call_llm(system_prompt, user_prompt)

        if not llm_summary:
            week_label = f"{this_monday.isoformat()} ~ {today.isoformat()}"
            parts = []
            if new_cand > 0:
                parts.append(f"新增候选人 {new_cand} 人")
            if interviews > 0:
                parts.append(f"面试 {interviews} 场")
            if offers > 0:
                parts.append(f"新增Offer {offers} 个")
            if hired > 0:
                parts.append(f"成功招聘 {hired} 人")
            summary = f"招聘周报（{week_label}）：" + (
                "，".join(parts) + "。" if parts else "本周无显著招聘活动。"
            )
            summary += f" 当前管线 {total_pipeline} 人，在招岗位 {open_positions} 个。"
        else:
            summary = llm_summary

        if not highlights:
            highlights.append("本周无特别亮点。")
        if not concerns:
            concerns.append("暂无明显问题。")

        return ReportResponse(
            report_type="weekly",
            title=f"招聘周报 - {this_monday.isoformat()}",
            period=f"{this_monday.isoformat()} ~ {today.isoformat()}",
            summary=summary,
            metrics=metrics,
            highlights=highlights,
            concerns=concerns,
            recommendations=recommendations,
            generated_at=now,
        )

    # ── analyze_funnel_bottleneck ────────────────────────────────

    async def analyze_funnel_bottleneck(
        self, funnel_data: dict[str, Any]
    ) -> list[AIInsight]:
        """
        Analyze funnel data to identify bottlenecks and suggest improvements.

        Examines conversion rates between stages, flags abnormally low
        conversion, and generates actionable recommendations.

        Args:
            funnel_data: Dict with stage counts, e.g.
                {"position": 10, "resume": 50, "match": 30,
                 "interview": 15, "offer": 5, "hired": 2}

        Returns:
            List of AIInsight objects identifying bottlenecks.
        """
        now = _now()
        insights: list[AIInsight] = []

        # Define expected conversion rate ranges (industry benchmarks)
        stage_order = ["position", "resume", "match", "interview", "offer", "hired"]
        stage_labels = {
            "position": "岗位发布",
            "resume": "简历接收",
            "match": "匹配筛选",
            "interview": "面试",
            "offer": "Offer",
            "hired": "入职",
        }
        # Minimum expected conversion rate (stage N / stage N-1)
        min_conversion = {
            ("position", "resume"): 3.0,   # At least 3 resumes per position
            ("resume", "match"): 0.3,       # 30% of resumes pass matching
            ("match", "interview"): 0.4,    # 40% of matches get interviewed
            ("interview", "offer"): 0.2,    # 20% of interviews lead to offer
            ("offer", "hired"): 0.5,        # 50% of offers accepted
        }

        # Analyze each transition
        for i in range(len(stage_order) - 1):
            from_stage = stage_order[i]
            to_stage = stage_order[i + 1]
            from_count = funnel_data.get(from_stage, 0)
            to_count = funnel_data.get(to_stage, 0)

            if from_count == 0:
                continue

            conversion_rate = to_count / from_count
            expected = min_conversion.get((from_stage, to_stage), 0.1)

            if conversion_rate < expected and from_count >= 3:
                # Bottleneck detected
                label_from = stage_labels.get(from_stage, from_stage)
                label_to = stage_labels.get(to_stage, to_stage)

                severity = "high" if conversion_rate < expected * 0.5 else "medium"

                # Generate specific suggestions per transition
                suggestions = {
                    ("position", "resume"): (
                        "建议优化职位描述和薪酬范围，"
                        "增加招聘渠道投放，提高职位曝光度。"
                    ),
                    ("resume", "match"): (
                        "建议优化匹配算法参数，"
                        "或放宽筛选条件以增加合格候选人数量。"
                    ),
                    ("match", "interview"): (
                        "建议缩短面试安排时间，"
                        "增加面试官可用时段，减少候选人流失。"
                    ),
                    ("interview", "offer"): (
                        "建议回顾面试评价标准，"
                        "确保面试流程与岗位需求一致，"
                        "考虑优化面试体验以提高候选人满意度。"
                    ),
                    ("offer", "hired"): (
                        "建议优化薪酬方案的竞争力，"
                        "缩短Offer审批流程，"
                        "加强候选人跟进和沟通。"
                    ),
                }

                action = suggestions.get(
                    (from_stage, to_stage),
                    "建议分析此阶段的详细数据，找出具体原因。"
                )

                insights.append(AIInsight(
                    id=f"bottleneck-{uuid.uuid4().hex[:8]}",
                    category="risk",
                    title=f"{label_from}→{label_to} 转化率偏低",
                    content=(
                        f"从「{label_from}」（{from_count}）到「{label_to}」（{to_count}）"
                        f"的转化率仅为 {conversion_rate:.1%}，"
                        f"低于行业参考值 {expected:.1%}。"
                    ),
                    confidence=0.8 if severity == "high" else 0.7,
                    action_suggestion=action,
                    created_at=now,
                ))

        # Overall funnel health summary
        total_stages = len(stage_order)
        bottleneck_count = len(insights)

        if bottleneck_count == 0:
            insights.append(AIInsight(
                id=f"funnel-ok-{uuid.uuid4().hex[:8]}",
                category="opportunity",
                title="招聘漏斗表现正常",
                content="各阶段转化率均在正常范围内，招聘流程运转良好。",
                confidence=0.85,
                action_suggestion="继续保持当前招聘节奏，定期监控漏斗数据。",
                created_at=now,
            ))
        elif bottleneck_count >= 3:
            insights.append(AIInsight(
                id=f"funnel-alert-{uuid.uuid4().hex[:8]}",
                category="risk",
                title="招聘漏斗存在多处瓶颈",
                content=(
                    f"在 {total_stages - 1} 个转化环节中，"
                    f"有 {bottleneck_count} 个低于预期。"
                    "建议全面审查招聘流程。"
                ),
                confidence=0.9,
                action_suggestion="建议召开招聘复盘会议，逐一分析各环节问题并制定改进计划。",
                created_at=now,
            ))

        # Try LLM enhancement for additional insights
        system_prompt = (
            "你是一个招聘流程分析专家。基于漏斗数据，分析可能的原因并给出改进建议。"
            "请返回 JSON 数组，格式为：\n"
            '[{"category": "recommendation", "title": "...", '
            '"content": "...", "confidence": 0.8, "action_suggestion": "..."}]'
        )
        user_prompt = json.dumps(funnel_data, ensure_ascii=False, default=str)
        llm_response = self._call_llm(system_prompt, user_prompt)

        if llm_response:
            try:
                parsed = json.loads(llm_response)
                for item in parsed[:3]:
                    insights.append(AIInsight(
                        id=f"ai-funnel-{uuid.uuid4().hex[:8]}",
                        category=item.get("category", "recommendation"),
                        title=item.get("title", ""),
                        content=item.get("content", ""),
                        confidence=item.get("confidence", 0.7),
                        action_suggestion=item.get("action_suggestion"),
                        created_at=now,
                    ))
            except (json.JSONDecodeError, KeyError):
                pass  # Rule-based insights are sufficient

        return insights
