"""
Offer AI Service (Offer AI 服务).

Provides AI-powered capabilities for offer management:
  - suggest_salary(): AI salary suggestion based on position, candidate,
    and internal compensation data.
  - get_compensation_benchmark(): Calculate internal percentile benchmarks
    and fairness score.
  - generate_offer_letter(): AI-generated offer letter via template + LLM.
  - get_negotiation_advice(): Generate negotiation strategy advice.

All LLM calls use mock/placeholder responses for now — the interface is
complete and ready to be wired to a real LLM provider.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import quantiles
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.offer import Offer
from app.models.offer_template import OfferTemplate
from app.models.position import Position

logger = logging.getLogger("hiremind.services.offer_ai")


# ---------------------------------------------------------------------------
# Data classes for return types
# ---------------------------------------------------------------------------


@dataclass
class SalarySuggestionResult:
    """AI-generated salary suggestion."""

    position_id: UUID
    candidate_id: UUID
    suggested_base: float
    suggested_bonus: float | None
    suggested_equity: str | None
    total_compensation: float
    confidence: float  # 0-1
    reasoning: str
    market_position: str  # below_p50 / p50_p75 / p75_p90 / above_p90
    risk_factors: list[str]
    negotiation_strategy: str


@dataclass
class CompensationBenchmarkResult:
    """Internal compensation benchmark analysis."""

    offer_id: UUID
    position_title: str
    candidate_name: str
    offered_total: float
    internal_p50: float
    internal_p75: float
    internal_p90: float
    market_p50: float | None
    market_p75: float | None
    fairness_score: float  # 0-100
    recommendation: str  # below_market / at_market / above_market


@dataclass
class OfferLetterResult:
    """AI-generated offer letter."""

    offer_id: UUID
    template_id: UUID | None
    rendered_content: str
    ai_enhanced: bool
    generated_at: datetime


@dataclass
class NegotiationAdviceResult:
    """Negotiation strategy advice."""

    offer_id: UUID
    candidate_name: str
    current_package: float
    advice: str
    key_negotiation_points: list[str]
    risk_assessment: str
    recommended_actions: list[str]
    alternative_packages: list[dict]
    timeline_suggestion: str


# ---------------------------------------------------------------------------
# OfferAIService
# ---------------------------------------------------------------------------


class OfferAIService:
    """AI-powered offer management service.

    Provides salary suggestions, compensation benchmarking, offer letter
    generation, and negotiation advice.  All LLM-dependent methods use
    deterministic placeholder logic for now; swap with real LLM calls
    when the AI provider is configured.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Helper: compute annual total compensation from an offer row
    # ------------------------------------------------------------------

    @staticmethod
    def _annual_total(offer: Offer) -> float:
        """Estimate annual total from offer fields."""
        base = (offer.base_salary or 0) * 12
        bonus = (offer.base_salary or 0) * (offer.annual_bonus_months or 0)
        sign_on = (offer.sign_on_bonus or 0)
        # Equity is hard to value — ignore for benchmarking
        return float(base + bonus + sign_on)

    # ------------------------------------------------------------------
    # Salary Suggestion
    # ------------------------------------------------------------------

    async def suggest_salary(
        self,
        position_id: UUID,
        candidate_id: UUID,
        tenant_id: str,
    ) -> SalarySuggestionResult:
        """Generate an AI salary suggestion.

        Analyses the position salary range, candidate experience, and
        internal historical offers to produce a recommended package.

        Currently uses mock logic — to be replaced with LLM-powered analysis.
        """
        # Load position
        pos_stmt = select(Position).where(
            Position.id == position_id,
            Position.tenant_id == tenant_id,
        )
        position = (await self.db.execute(pos_stmt)).scalar_one_or_none()
        if position is None:
            raise ValueError("Position not found")

        # Load candidate
        cand_stmt = select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id,
        )
        candidate = (await self.db.execute(cand_stmt)).scalar_one_or_none()
        if candidate is None:
            raise ValueError("Candidate not found")

        # Position salary band
        salary_min = float(position.salary_min or 0)
        salary_max = float(position.salary_max or 0)
        salary_mid = (salary_min + salary_max) / 2 if salary_max > 0 else salary_min

        # Internal historical offers for this position's department
        history_stmt = select(Offer.base_salary).where(
            Offer.tenant_id == tenant_id,
            Offer.position_id == position_id,
            Offer.base_salary.isnot(None),
        )
        history_result = (await self.db.execute(history_stmt)).scalars().all()
        history_list = [float(s) for s in history_result if s is not None]

        # Compute percentiles from history (or fall back to position range)
        if len(history_list) >= 3:
            pcts = quantiles(history_list, n=4)
            p25, p50, p75 = pcts[0], pcts[1], pcts[2]
        else:
            p50 = salary_mid
            p25 = salary_min
            p75 = salary_max

        # Candidate experience (from resume data if available)
        experience_years = 0
        if hasattr(candidate, "resume_data") and candidate.resume_data:
            experience_years = candidate.resume_data.get("experience_years", 0)

        # --- Mock AI Logic ---
        # Base suggestion: position midpoint adjusted by experience
        exp_factor = min(experience_years / 10.0, 1.0)  # 0-1
        suggested_base = round(p50 * (0.9 + 0.2 * exp_factor), -2)
        suggested_bonus = round(suggested_base * (1 + random.uniform(0, 2)) / 12, 1)
        suggested_equity = None
        if suggested_base > p75:
            suggested_equity = "5000-10000 options / 4 years vesting"

        total_comp = suggested_base * 12 + suggested_bonus * suggested_base

        # Market position determination
        if suggested_base < p25:
            market_position = "below_p50"
        elif suggested_base < p50:
            market_position = "below_p50"
        elif suggested_base < p75:
            market_position = "p50_p75"
        elif suggested_base < (p75 * 1.2):
            market_position = "p75_p90"
        else:
            market_position = "above_p90"

        # Risk factors (mock)
        risk_factors: list[str] = []
        if suggested_base > salary_max:
            risk_factors.append("超出岗位薪资上限")
        if suggested_base < salary_min:
            risk_factors.append("低于岗位薪资下限，可能影响候选人接受度")
        if experience_years < 3 and suggested_base > p50:
            risk_factors.append("经验年限较短但薪资高于P50")
        if not history_list:
            risk_factors.append("无内部历史Offer数据参考")

        # Confidence (mock: based on data richness)
        confidence = min(0.5 + 0.1 * len(history_list), 0.95)
        if not history_list:
            confidence = 0.4

        # Negotiation strategy (mock)
        if market_position in ("below_p50",):
            strategy = "建议适当提高薪资至市场P50水平以提高候选人接受概率"
        elif market_position == "p50_p75":
            strategy = "薪资处于合理区间，可通过bonus/equity增强吸引力"
        else:
            strategy = "薪资处于较高水平，注意内部公平性; 可强调长期激励"

        # Reasoning (mock)
        reasoning = (
            f"基于岗位「{position.title}」薪资范围({salary_min}-{salary_max})，"
            f"内部历史Offer P50={p50:.0f}，候选人经验{experience_years}年，"
            f"建议base={suggested_base:.0f}/月，总包≈{total_comp:.0f}/年。"
            f"市场定位: {market_position}，置信度: {confidence:.0%}。"
        )

        return SalarySuggestionResult(
            position_id=position_id,
            candidate_id=candidate_id,
            suggested_base=suggested_base,
            suggested_bonus=suggested_bonus,
            suggested_equity=suggested_equity,
            total_compensation=total_comp,
            confidence=confidence,
            reasoning=reasoning,
            market_position=market_position,
            risk_factors=risk_factors,
            negotiation_strategy=strategy,
        )

    # ------------------------------------------------------------------
    # Compensation Benchmark
    # ------------------------------------------------------------------

    async def get_compensation_benchmark(
        self,
        offer_id: UUID,
        tenant_id: str,
    ) -> CompensationBenchmarkResult:
        """Calculate internal percentile benchmarks and a fairness score.

        Compares the given offer's total package against all historical
        offers in the same tenant for similar positions.
        """
        # Load offer
        offer_stmt = select(Offer).where(
            Offer.id == offer_id,
            Offer.tenant_id == tenant_id,
        )
        offer = (await self.db.execute(offer_stmt)).scalar_one_or_none()
        if offer is None:
            raise ValueError("Offer not found")

        # Gather all historical total compensations in the same tenant
        # for the same position (or all if position is null)
        filters = [
            Offer.tenant_id == tenant_id,
            Offer.base_salary.isnot(None),
            Offer.id != offer_id,  # Exclude the offer itself
        ]
        if offer.position_id:
            filters.append(Offer.position_id == offer.position_id)

        hist_stmt = select(Offer).where(*filters)
        hist_offers = (await self.db.execute(hist_stmt)).scalars().all()
        hist_totals = [self._annual_total(o) for o in hist_offers]

        offered_total = self._annual_total(offer)

        # Compute percentiles
        if len(hist_totals) >= 3:
            pcts = quantiles(hist_totals, n=20)
            p50 = pcts[9]   # 50th percentile
            p75 = pcts[14]  # 75th percentile
            p90 = pcts[17]  # 90th percentile
        elif len(hist_totals) >= 1:
            sorted_vals = sorted(hist_totals)
            p50 = sorted_vals[len(sorted_vals) // 2]
            p75 = sorted_vals[-1]
            p90 = sorted_vals[-1]
        else:
            # No internal data — use the offer itself as baseline
            p50 = offered_total * 0.9
            p75 = offered_total
            p90 = offered_total * 1.1

        # Market data (placeholder — would come from external data source)
        market_p50 = None
        market_p75 = None

        # Fairness score: how close is the offer to internal P50
        if p50 > 0:
            deviation = abs(offered_total - p50) / p50
            fairness_score = max(0, min(100, round(100 - deviation * 100, 1)))
        else:
            fairness_score = 50.0

        # Recommendation
        if offered_total < p50 * 0.9:
            recommendation = "below_market"
        elif offered_total > p75 * 1.1:
            recommendation = "above_market"
        else:
            recommendation = "at_market"

        # Position title
        position_title = ""
        if offer.position_id:
            pos_stmt = select(Position).where(Position.id == offer.position_id)
            position = (await self.db.execute(pos_stmt)).scalar_one_or_none()
            if position:
                position_title = position.title

        # Candidate name
        cand_stmt = select(Candidate).where(Candidate.id == offer.candidate_id)
        candidate = (await self.db.execute(cand_stmt)).scalar_one_or_none()
        candidate_name = candidate.name if candidate else "Unknown"

        return CompensationBenchmarkResult(
            offer_id=offer_id,
            position_title=position_title,
            candidate_name=candidate_name,
            offered_total=offered_total,
            internal_p50=round(p50, 2),
            internal_p75=round(p75, 2),
            internal_p90=round(p90, 2),
            market_p50=market_p50,
            market_p75=market_p75,
            fairness_score=fairness_score,
            recommendation=recommendation,
        )

    # ------------------------------------------------------------------
    # Generate Offer Letter (template + AI enhancement)
    # ------------------------------------------------------------------

    async def generate_offer_letter(
        self,
        offer_id: UUID,
        template_id: UUID | None,
        tenant_id: str,
    ) -> OfferLetterResult:
        """Generate an offer letter using a template with variable substitution.

        Optionally polishes the letter with LLM (currently placeholder).
        """
        # Load offer with relationships
        offer_stmt = select(Offer).where(
            Offer.id == offer_id,
            Offer.tenant_id == tenant_id,
        )
        offer = (await self.db.execute(offer_stmt)).scalar_one_or_none()
        if offer is None:
            raise ValueError("Offer not found")

        # Load template
        if template_id is not None:
            tpl_stmt = select(OfferTemplate).where(
                OfferTemplate.id == template_id,
                OfferTemplate.tenant_id == tenant_id,
            )
        else:
            tpl_stmt = (
                select(OfferTemplate)
                .where(
                    OfferTemplate.tenant_id == tenant_id,
                    OfferTemplate.is_default == True,  # noqa: E712
                )
                .limit(1)
            )
        template = (await self.db.execute(tpl_stmt)).scalar_one_or_none()
        if template is None:
            raise ValueError("Offer template not found")

        # Gather candidate info
        cand_stmt = select(Candidate).where(Candidate.id == offer.candidate_id)
        candidate = (await self.db.execute(cand_stmt)).scalar_one_or_none()

        # Gather position info
        position_title = ""
        department_name = ""
        if offer.position_id:
            pos_stmt = select(Position).where(Position.id == offer.position_id)
            position = (await self.db.execute(pos_stmt)).scalar_one_or_none()
            if position:
                position_title = position.title

        # Build variable map
        import re

        variables = {
            "candidate_name": candidate.name if candidate else "候选人",
            "position_title": position_title,
            "department_name": department_name,
            "base_salary": f"{offer.base_salary or 0:,.0f}",
            "annual_bonus_months": str(offer.annual_bonus_months or ""),
            "sign_on_bonus": f"{offer.sign_on_bonus or 0:,.0f}",
            "equity": offer.equity or "无",
            "benefits_summary": offer.benefits_summary or "详见员工手册",
            "proposed_start_date": str(offer.proposed_start_date or "待定"),
            "probation_months": str(offer.probation_months or "3"),
            "work_location": offer.work_location or "待定",
            "employment_type": offer.employment_type or "全职",
            "company_name": "公司",
            "offer_date": datetime.now(timezone.utc).strftime("%Y年%m月%d日"),
        }

        # Substitute {{variable}} placeholders
        content = template.content
        for var_name, var_value in variables.items():
            content = content.replace("{{" + var_name + "}}", var_value)

        # Clean unreplaced
        content = re.sub(r"\{\{(\w+)\}\}", r"[待填: \1]", content)

        # --- LLM Enhancement (placeholder) ---
        # In production, we would send the rendered letter to LLM for polishing
        ai_enhanced = False
        # Example placeholder enhancement:
        #   result = await ai_client.polish_offer_letter(content)
        #   content = result.polished_content
        #   ai_enhanced = True

        logger.info(
            "Generated offer letter: offer=%s, template=%s, ai_enhanced=%s",
            offer_id, template_id, ai_enhanced,
        )

        return OfferLetterResult(
            offer_id=offer_id,
            template_id=template_id,
            rendered_content=content,
            ai_enhanced=ai_enhanced,
            generated_at=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # Negotiation Advice
    # ------------------------------------------------------------------

    async def get_negotiation_advice(
        self,
        offer_id: UUID,
        tenant_id: str,
    ) -> NegotiationAdviceResult:
        """Generate negotiation strategy advice for an offer.

        Analyses the candidate profile, current offer, internal benchmarks,
        and (placeholder) market data to produce actionable negotiation advice.
        """
        # Load offer
        offer_stmt = select(Offer).where(
            Offer.id == offer_id,
            Offer.tenant_id == tenant_id,
        )
        offer = (await self.db.execute(offer_stmt)).scalar_one_or_none()
        if offer is None:
            raise ValueError("Offer not found")

        current_package = self._annual_total(offer)

        # Candidate info
        cand_stmt = select(Candidate).where(Candidate.id == offer.candidate_id)
        candidate = (await self.db.execute(cand_stmt)).scalar_one_or_none()
        candidate_name = candidate.name if candidate else "Unknown"

        # Position info
        position_title = ""
        salary_min = 0.0
        salary_max = 0.0
        if offer.position_id:
            pos_stmt = select(Position).where(Position.id == offer.position_id)
            position = (await self.db.execute(pos_stmt)).scalar_one_or_none()
            if position:
                position_title = position.title
                salary_min = float(position.salary_min or 0)
                salary_max = float(position.salary_max or 0)

        # Internal benchmarks for context
        filters = [
            Offer.tenant_id == tenant_id,
            Offer.base_salary.isnot(None),
        ]
        if offer.position_id:
            filters.append(Offer.position_id == offer.position_id)

        hist_stmt = select(Offer).where(*filters)
        hist_offers = (await self.db.execute(hist_stmt)).scalars().all()
        hist_totals = [self._annual_total(o) for o in hist_offers]

        if len(hist_totals) >= 3:
            pcts = quantiles(hist_totals, n=4)
            p50 = pcts[1]
        elif hist_totals:
            p50 = sorted(hist_totals)[len(hist_totals) // 2]
        else:
            p50 = current_package

        # --- Mock Negotiation Advice ---
        if current_package < p50 * 0.9:
            advice = (
                f"当前Offer总包({current_package:,.0f})低于内部P50({p50:,.0f})。"
                f"建议适当提高base或增加sign-on bonus以提高竞争力。"
            )
            key_points = [
                "提高base salary至P50水平",
                "增加sign-on bonus作为过渡补偿",
                "强调长期发展机会和equity计划",
                "考虑flexible work等非薪资福利",
            ]
            risk = "薪资偏低可能导致候选人拒绝或入职后短期离职"
            actions = [
                "与候选人了解其期望薪资",
                "准备2-3个备选方案",
                "明确final offer的deadline",
            ]
        elif current_package > p50 * 1.1:
            advice = (
                f"当前Offer总包({current_package:,.0f})高于内部P50({p50:,.0f})。"
                f"建议确认内部公平性，准备justify理由。"
            )
            key_points = [
                "确认offer在岗位薪资范围内",
                "准备同级别岗位薪资对比说明",
                "评估对内部团队薪资公平性的影响",
                "考虑分期兑现方式降低一次性成本",
            ]
            risk = "高薪可能引起内部公平性问题"
            actions = [
                "与HRBP确认内部公平性评估",
                "准备高管审批材料",
                "设定绩效对赌条件",
            ]
        else:
            advice = (
                f"当前Offer总包({current_package:,.0f})在合理范围内(P50={p50:,.0f})。"
                f"建议通过非薪资福利增强整体吸引力。"
            )
            key_points = [
                "强调公司文化和团队氛围",
                "展示职业发展路径",
                "提供flexible working安排",
                "考虑additional PTO或learning budget",
            ]
            risk = "市场竞争激烈，需关注候选人其他offer"
            actions = [
                "了解候选人其他机会",
                "加快offer流程以抢占先机",
                "安排team见面以增强吸引力",
            ]

        # Alternative packages (mock)
        base_salary = offer.base_salary or 0
        alternative_packages = [
            {
                "name": "方案A: 稳健型",
                "base_salary": base_salary,
                "bonus_months": round(base_salary * 2 / 12, 1),
                "total": current_package,
            },
            {
                "name": "方案B: 激进型",
                "base_salary": round(base_salary * 1.1, -2),
                "bonus_months": round(base_salary * 3 / 12, 1),
                "total": round(current_package * 1.15, -2),
            },
            {
                "name": "方案C: 平衡型",
                "base_salary": round(base_salary * 1.05, -2),
                "bonus_months": round(base_salary * 1.5 / 12, 1),
                "sign_on": round(base_salary * 1, -2),
                "total": round(current_package * 1.08, -2),
            },
        ]

        return NegotiationAdviceResult(
            offer_id=offer_id,
            candidate_name=candidate_name,
            current_package=current_package,
            advice=advice,
            key_negotiation_points=key_points,
            risk_assessment=risk,
            recommended_actions=actions,
            alternative_packages=alternative_packages,
            timeline_suggestion="建议在5个工作日内完成谈判，避免候选人流失",
        )
