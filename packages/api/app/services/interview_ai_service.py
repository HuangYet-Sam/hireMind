"""
Interview AI Service (面试 AI 服务).

Provides AI-powered capabilities for interview management:
  - generate_briefing(): Generate an interview briefing based on position-candidate gap analysis.
  - generate_questions(): Generate interview questions grouped by competency dimension.
  - recommend_timeslots(): Recommend available time slots avoiding conflicts.
  - analyze_feedback(): AI-powered analysis of interviewer feedback.

All LLM calls use mock/placeholder responses for now — the interface is complete
and ready to be wired to a real LLM provider.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.models.interview import Interview, InterviewFeedback
from app.models.position import Position

logger = logging.getLogger("hiremind.services.interview_ai")


# ---------------------------------------------------------------------------
# Data classes for return types
# ---------------------------------------------------------------------------


@dataclass
class BriefingResult:
    """AI-generated interview briefing (考察清单)."""

    interview_id: UUID
    position_requirements: list[str]
    candidate_strengths: list[str]
    candidate_gaps: list[str]
    verification_points: list[str]
    focus_areas: list[str]
    suggested_questions: list[str]


@dataclass
class QuestionItem:
    """A single interview question with follow-ups and evaluation criteria."""

    question: str
    follow_ups: list[str]
    evaluation_criteria: list[str]


@dataclass
class QuestionGroup:
    """Questions grouped by competency dimension."""

    dimension: str
    difficulty: str  # easy / medium / hard
    questions: list[QuestionItem]


@dataclass
class QuestionsResult:
    """AI-generated interview questions result."""

    interview_id: UUID
    question_groups: list[QuestionGroup]
    total_questions: int


@dataclass
class TimeSlot:
    """A recommended time slot."""

    start: datetime
    end: datetime
    score: float
    reason: str
    conflicts: list[str]


@dataclass
class TimeSlotRecommendationResult:
    """Result of time slot recommendation."""

    position_id: UUID | None
    candidate_id: UUID
    recommended_slots: list[TimeSlot]
    duration_minutes: int


@dataclass
class FeedbackAnalysisResult:
    """AI analysis of interview feedback."""

    interview_id: UUID
    overall_score: float
    score_breakdown: dict[str, float]
    strengths: list[str]
    concerns: list[str]
    recommendation: str  # strong_yes / yes / no / strong_no
    recommendation_reason: str
    improvement_suggestions: list[str]
    candidate_fit_score: float


# ---------------------------------------------------------------------------
# InterviewAIService
# ---------------------------------------------------------------------------

# Default competency dimensions for question generation
_DEFAULT_DIMENSIONS = [
    ("技术深度", "hard"),
    ("系统设计", "hard"),
    ("问题解决", "medium"),
    ("沟通协作", "medium"),
    ("项目经验", "easy"),
    ("学习能力", "easy"),
]

# Default round type → dimension mapping
_ROUND_TYPE_DIMENSIONS: dict[str, list[tuple[str, str]]] = {
    "technical": [
        ("编程能力", "hard"),
        ("系统设计", "hard"),
        ("算法与数据结构", "hard"),
        ("技术问题解决", "medium"),
    ],
    "behavioral": [
        ("团队协作", "medium"),
        ("沟通表达", "medium"),
        ("冲突处理", "medium"),
        ("自我驱动", "easy"),
    ],
    "hr": [
        ("职业规划", "easy"),
        ("文化契合", "medium"),
        ("稳定性", "easy"),
        ("薪资期望", "easy"),
    ],
    "final": [
        ("综合判断力", "hard"),
        ("战略思维", "hard"),
        ("领导力", "medium"),
    ],
}


class InterviewAIService:
    """Async service providing AI-powered interview capabilities.

    Each method follows the pattern:
      1. Load required data from DB (interview, candidate, position, feedback).
      2. Build a prompt context from the data.
      3. Call LLM (currently mock/placeholder).
      4. Parse and return structured results.

    All methods are async and accept ``tenant_id`` for tenant isolation.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_interview_context(
        self,
        interview_id: UUID,
        tenant_id: str,
    ) -> tuple[Interview, Candidate | None, Position | None]:
        """Load an interview with its candidate and position.

        Args:
            interview_id: Interview UUID.
            tenant_id: Tenant scope.

        Returns:
            Tuple of (interview, candidate, position).
            candidate/position may be None if not found.

        Raises:
            ValueError: If interview not found.
        """
        stmt = (
            select(Interview)
            .where(Interview.id == interview_id, Interview.tenant_id == tenant_id)
            .options(selectinload(Interview.candidate))
            .options(selectinload(Interview.position))
        )
        interview = (await self.db.execute(stmt)).scalar_one_or_none()
        if interview is None:
            raise ValueError(f"Interview {interview_id} not found")

        candidate = interview.candidate
        position = interview.position
        return interview, candidate, position

    async def _load_feedbacks(
        self,
        interview_id: UUID,
    ) -> list[InterviewFeedback]:
        """Load all feedback entries for an interview.

        Args:
            interview_id: Interview UUID.

        Returns:
            List of InterviewFeedback objects.
        """
        stmt = select(InterviewFeedback).where(
            InterviewFeedback.interview_id == interview_id
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_scheduled_slots(
        self,
        interviewer_ids: list[str],
        date_from: datetime,
        date_to: datetime,
        tenant_id: str,
    ) -> list[dict]:
        """Get existing scheduled interview slots for given interviewers.

        Args:
            interviewer_ids: List of interviewer user IDs.
            date_from: Range start.
            date_to: Range end.
            tenant_id: Tenant scope.

        Returns:
            List of dicts with start/end times of existing interviews.
        """
        if not interviewer_ids:
            return []

        stmt = (
            select(Interview)
            .where(
                Interview.tenant_id == tenant_id,
                Interview.scheduled_at >= date_from,
                Interview.scheduled_at <= date_to,
                Interview.status.in_(["scheduled", "in_progress"]),
            )
        )
        result = await self.db.execute(stmt)
        interviews = list(result.scalars().all())

        slots: list[dict] = []
        for iv in interviews:
            iv_ids = iv.interviewer_ids or []
            # Check overlap with any of the target interviewer_ids
            if set(iv_ids) & set(interviewer_ids):
                end_time = (
                    iv.scheduled_at + timedelta(minutes=iv.duration_minutes)
                    if iv.scheduled_at
                    else None
                )
                if iv.scheduled_at and end_time:
                    slots.append({
                        "start": iv.scheduled_at,
                        "end": end_time,
                        "interviewer_ids": iv_ids,
                    })
        return slots

    def _has_conflict(
        self,
        slot_start: datetime,
        slot_end: datetime,
        existing_slots: list[dict],
        buffer_minutes: int = 15,
    ) -> list[str]:
        """Check if a proposed slot conflicts with existing slots.

        Args:
            slot_start: Proposed start time.
            slot_end: Proposed end time.
            existing_slots: List of existing slot dicts with start/end.
            buffer_minutes: Buffer before/after existing slots.

        Returns:
            List of conflict descriptions (empty if no conflicts).
        """
        conflicts: list[str] = []
        buffer = timedelta(minutes=buffer_minutes)

        for es in existing_slots:
            es_start = es["start"] - buffer
            es_end = es["end"] + buffer
            if slot_start < es_end and slot_end > es_start:
                conflicts.append(
                    f"Conflict with existing interview at {es['start'].isoformat()}"
                    f" – {es['end'].isoformat()} (interviewers: {es['interviewer_ids']})"
                )
        return conflicts

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_briefing(
        self,
        interview_id: UUID,
        tenant_id: str,
    ) -> BriefingResult:
        """Generate an AI-powered interview briefing (考察清单).

        Analyzes the gap between position requirements and the candidate's
        profile to produce a structured briefing with:
          - Key position requirements
          - Candidate strengths relative to the position
          - Identified gaps that need verification
          - Focus areas and suggested questions

        Currently uses mock/placeholder logic. When a real LLM is wired in,
        replace the mock section with an actual prompt + parse.

        Args:
            interview_id: Interview UUID to generate briefing for.
            tenant_id: Tenant scope identifier.

        Returns:
            BriefingResult dataclass with structured briefing data.

        Raises:
            ValueError: If interview, candidate, or position not found.
        """
        logger.info("Generating briefing for interview %s (tenant=%s)", interview_id, tenant_id)

        interview, candidate, position = await self._load_interview_context(
            interview_id, tenant_id
        )

        if position is None:
            raise ValueError(f"Position not found for interview {interview_id}")
        if candidate is None:
            raise ValueError(f"Candidate not found for interview {interview_id}")

        # ---- Build context from position + candidate ----
        position_reqs: list[str] = []
        if hasattr(position, "requirements") and position.requirements:
            if isinstance(position.requirements, list):
                position_reqs = [str(r) for r in position.requirements]
            elif isinstance(position.requirements, dict):
                position_reqs = list(position.requirements.values())

        # Fallback to description-based requirements
        if not position_reqs and hasattr(position, "description") and position.description:
            position_reqs = [f"岗位描述中的要求（参见：{position.title}）"]

        if not position_reqs:
            position_reqs = ["综合能力评估"]

        # Extract candidate skills
        candidate_skills: list[str] = []
        candidate_profile = getattr(candidate, "profile", None) or {}
        if isinstance(candidate_profile, dict):
            skill_cloud = candidate_profile.get("skill_cloud", [])
            if isinstance(skill_cloud, list):
                candidate_skills = [
                    s.get("name", str(s)) if isinstance(s, dict) else str(s)
                    for s in skill_cloud
                ]

        # ---- Mock LLM call — replace with real LLM prompt ----
        logger.debug(
            "Briefing context: position_reqs=%d, candidate_skills=%d",
            len(position_reqs),
            len(candidate_skills),
        )

        # Generate mock strengths, gaps, and focus areas
        strengths = candidate_skills[:5] if candidate_skills else ["沟通能力强", "学习意愿高"]
        gaps = [
            req for req in position_reqs[:3]
            if not any(skill.lower() in req.lower() for skill in candidate_skills)
        ] or ["需要进一步验证技术深度"]

        verification_points = [
            f"验证 {gap} 的实际掌握程度" for gap in gaps[:4]
        ]

        focus_areas = gaps[:3] if gaps else ["综合能力评估"]

        suggested_questions = [
            f"请描述您在 {area} 方面的具体项目经验" for area in focus_areas
        ] + [
            "您如何应对项目中遇到的技术挑战？",
            "请举一个您与团队协作解决问题的例子。",
        ]

        result = BriefingResult(
            interview_id=interview_id,
            position_requirements=position_reqs[:8],
            candidate_strengths=strengths,
            candidate_gaps=gaps,
            verification_points=verification_points,
            focus_areas=focus_areas,
            suggested_questions=suggested_questions[:10],
        )

        logger.info(
            "Briefing generated: %d requirements, %d strengths, %d gaps, %d questions",
            len(result.position_requirements),
            len(result.candidate_strengths),
            len(result.candidate_gaps),
            len(result.suggested_questions),
        )
        return result

    async def generate_questions(
        self,
        interview_id: UUID,
        tenant_id: str,
    ) -> QuestionsResult:
        """Generate AI-powered interview questions grouped by competency dimension.

        For each relevant competency dimension, generates 2-3 questions with:
          - The main question
          - Follow-up probing questions
          - Evaluation criteria for scoring answers

        The dimensions are determined by the interview_type (technical, behavioral,
        hr, final) and the position requirements.

        Currently uses mock/placeholder logic. When a real LLM is wired in,
        replace the mock section with an actual prompt + parse.

        Args:
            interview_id: Interview UUID to generate questions for.
            tenant_id: Tenant scope identifier.

        Returns:
            QuestionsResult dataclass with grouped questions and total count.

        Raises:
            ValueError: If interview not found.
        """
        logger.info("Generating questions for interview %s (tenant=%s)", interview_id, tenant_id)

        interview, candidate, position = await self._load_interview_context(
            interview_id, tenant_id
        )

        interview_type = interview.interview_type or "technical"

        # Select dimensions based on interview type
        dimensions = _ROUND_TYPE_DIMENSIONS.get(interview_type, _DEFAULT_DIMENSIONS)

        # ---- Mock LLM call — replace with real LLM prompt ----
        logger.debug(
            "Question context: type=%s, dimensions=%d", interview_type, len(dimensions)
        )

        # Build position title for question context
        position_title = getattr(position, "title", None) or "该岗位"
        candidate_name = getattr(candidate, "name_encrypted", None) or "候选人"

        question_groups: list[QuestionGroup] = []
        total = 0

        mock_questions_pool: dict[str, list[QuestionItem]] = {
            "编程能力": [
                QuestionItem(
                    question=f"请描述您如何设计一个高性能的{position_title}后端服务？",
                    follow_ups=["如何处理并发？", "如何保证数据一致性？"],
                    evaluation_criteria=["架构清晰度", "技术选型合理性", "性能意识"],
                ),
                QuestionItem(
                    question="请解释您最熟悉的设计模式，并举例说明在什么场景下使用？",
                    follow_ups=["为什么选择这个模式而非其他？", "有没有过度设计的风险？"],
                    evaluation_criteria=["理解深度", "应用能力", "权衡意识"],
                ),
            ],
            "系统设计": [
                QuestionItem(
                    question=f"如果让您设计一个支持百万级用户的{position_title}系统，您会如何架构？",
                    follow_ups=["数据库如何分片？", "缓存策略是什么？", "如何处理热点问题？"],
                    evaluation_criteria=["扩展性思维", "技术广度", "trade-off分析"],
                ),
                QuestionItem(
                    question="请描述一个您设计过的最有挑战的系统，您解决了什么核心问题？",
                    follow_ups=["如果有更多资源，您会如何改进？", "最大的技术风险是什么？"],
                    evaluation_criteria=["实际经验", "问题识别能力", "持续改进意识"],
                ),
            ],
            "算法与数据结构": [
                QuestionItem(
                    question="给定一个大数据集，如何在有限内存中找到 Top-K 元素？",
                    follow_ups=["时间复杂度是多少？", "如果数据是流式的呢？"],
                    evaluation_criteria=["算法基础", "复杂度分析", "实际应用能力"],
                ),
            ],
            "技术问题解决": [
                QuestionItem(
                    question="描述一次您排查和解决线上性能问题的经历。",
                    follow_ups=["用了什么工具？", "根因是什么？", "如何防止再发生？"],
                    evaluation_criteria=["排查方法论", "工具熟练度", "预防意识"],
                ),
                QuestionItem(
                    question="如何在团队中推动技术方案的落地？请举例说明。",
                    follow_ups=["遇到反对意见怎么办？", "如何衡量效果？"],
                    evaluation_criteria=["影响力", "方法论", "结果导向"],
                ),
            ],
            "团队协作": [
                QuestionItem(
                    question="请描述一次您与团队成员意见不合的经历，您是如何处理的？",
                    follow_ups=["最终结果如何？", "您从中学到了什么？"],
                    evaluation_criteria=["沟通能力", "冲突解决", "反思能力"],
                ),
            ],
            "沟通表达": [
                QuestionItem(
                    question="如何向非技术背景的产品经理解释一个复杂的技术方案？",
                    follow_ups=["如何处理对方的疑问？", "如何确认对方理解了？"],
                    evaluation_criteria=["表达清晰度", "换位思考", "沟通策略"],
                ),
            ],
            "冲突处理": [
                QuestionItem(
                    question="当项目deadline临近但需求发生变更时，您会怎么做？",
                    follow_ups=["如何与stakeholder沟通？", "如何调整优先级？"],
                    evaluation_criteria=["应变能力", "优先级管理", "沟通策略"],
                ),
            ],
            "自我驱动": [
                QuestionItem(
                    question="您最近学习了什么新技术？是如何学习的？",
                    follow_ups=["如何应用到工作中？", "学习过程中遇到了什么困难？"],
                    evaluation_criteria=["学习能力", "自驱力", "应用能力"],
                ),
            ],
            "职业规划": [
                QuestionItem(
                    question=f"您未来3年的职业规划是什么？{position_title}这个岗位如何帮助您实现？",
                    follow_ups=["为什么选择这个方向？", "您认为自己还需要提升什么？"],
                    evaluation_criteria=["目标清晰度", "岗位匹配度", "自我认知"],
                ),
            ],
            "文化契合": [
                QuestionItem(
                    question="您理想中的团队文化是什么样的？",
                    follow_ups=["为什么看重这些方面？", "您如何融入一个新团队？"],
                    evaluation_criteria=["价值观匹配", "适应能力", "团队意识"],
                ),
            ],
            "稳定性": [
                QuestionItem(
                    question="您为什么考虑离开现在的公司？",
                    follow_ups=["对新公司有什么期望？", "多久能入职？"],
                    evaluation_criteria=["动机合理性", "期望匹配度", "入职意愿"],
                ),
            ],
            "薪资期望": [
                QuestionItem(
                    question="您的薪资期望范围是多少？",
                    follow_ups=["这个范围的依据是什么？", "除薪资外还看重什么？"],
                    evaluation_criteria=["合理性", "灵活性", "综合考量"],
                ),
            ],
            "综合判断力": [
                QuestionItem(
                    question=f"综合前面所有讨论，您认为自己最大的优势和需要提升的地方分别是什么？",
                    follow_ups=["如果入职，前30天您计划做什么？", "您有什么想问我们的？"],
                    evaluation_criteria=["自我认知", "规划能力", "真实性"],
                ),
            ],
            "战略思维": [
                QuestionItem(
                    question=f"从行业趋势来看，您认为{position_title}这个领域未来会有什么变化？",
                    follow_ups=["如何应对这些变化？", "您如何看待AI对这个岗位的影响？"],
                    evaluation_criteria=["行业洞察", "前瞻性", "学习能力"],
                ),
            ],
            "领导力": [
                QuestionItem(
                    question="请描述一次您带领团队完成挑战性目标的经历。",
                    follow_ups=["如何激励团队？", "如何处理表现不佳的成员？"],
                    evaluation_criteria=["领导风格", "团队管理", "目标达成"],
                ),
            ],
        }

        for dim_name, difficulty in dimensions:
            # Use pre-built mock questions if available, else generate generic ones
            items = mock_questions_pool.get(dim_name, [
                QuestionItem(
                    question=f"请谈谈您在{dim_name}方面的经验和理解？",
                    follow_ups=["能举个具体的例子吗？", "您是如何持续提升这方面能力的？"],
                    evaluation_criteria=[f"{dim_name}理解深度", "实际经验", "表达能力"],
                ),
                QuestionItem(
                    question=f"在{dim_name}方面，您遇到过最大的挑战是什么？如何解决的？",
                    follow_ups=["如果重来一次会怎么改进？", "有什么经验教训？"],
                    evaluation_criteria=["问题分析", "解决思路", "反思能力"],
                ),
            ])

            # Limit to 2-3 questions per dimension
            selected = items[:min(3, len(items))]
            total += len(selected)

            question_groups.append(QuestionGroup(
                dimension=dim_name,
                difficulty=difficulty,
                questions=selected,
            ))

        result = QuestionsResult(
            interview_id=interview_id,
            question_groups=question_groups,
            total_questions=total,
        )

        logger.info(
            "Questions generated: %d groups, %d total questions for type=%s",
            len(question_groups),
            total,
            interview_type,
        )
        return result

    async def recommend_timeslots(
        self,
        position_id: UUID | None,
        candidate_id: UUID,
        duration_minutes: int,
        tenant_id: str,
        *,
        num_slots: int = 5,
        interviewer_ids: list[str] | None = None,
        days_ahead: int = 14,
    ) -> TimeSlotRecommendationResult:
        """Recommend available time slots for scheduling an interview.

        Considers:
          - Existing interview schedules to avoid conflicts
          - Interviewer availability (if provided)
          - Working hours (9:00–18:00 weekdays)
          - Buffer time between interviews (15 minutes)

        Currently uses rule-based logic. Can be enhanced with LLM for
        smarter suggestions (e.g., considering interviewer preferences).

        Args:
            position_id: Position UUID (optional, for context).
            candidate_id: Candidate UUID.
            duration_minutes: Required interview duration.
            tenant_id: Tenant scope.
            num_slots: Number of slots to recommend (default 5).
            interviewer_ids: Optional interviewer IDs to check conflicts for.
            days_ahead: How many days ahead to search (default 14).

        Returns:
            TimeSlotRecommendationResult with ranked recommended slots.

        Raises:
            ValueError: If candidate not found.
        """
        logger.info(
            "Recommending timeslots: candidate=%s, position=%s, duration=%dmin, tenant=%s",
            candidate_id,
            position_id,
            duration_minutes,
            tenant_id,
        )

        # Validate candidate exists
        stmt = select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id,
        )
        candidate = (await self.db.execute(stmt)).scalar_one_or_none()
        if candidate is None:
            raise ValueError(f"Candidate {candidate_id} not found")

        # Get existing scheduled slots for interviewers
        now = datetime.now(timezone.utc)
        search_start = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        search_end = search_start + timedelta(days=days_ahead)

        iv_ids = interviewer_ids or []
        existing_slots = await self._get_scheduled_slots(
            iv_ids, search_start, search_end, tenant_id
        )

        logger.debug("Found %d existing slots to check conflicts against", len(existing_slots))

        # Generate candidate time slots (working hours, weekdays only)
        recommended: list[TimeSlot] = []
        current_day = search_start

        while current_day < search_end and len(recommended) < num_slots * 3:
            # Skip weekends
            if current_day.weekday() >= 5:
                current_day += timedelta(days=1)
                continue

            # Generate slots throughout the day (9:00–18:00)
            for hour in range(9, 18):
                slot_start = current_day.replace(hour=hour, minute=0, second=0, microsecond=0)
                slot_end = slot_start + timedelta(minutes=duration_minutes)

                # Don't suggest past slots
                if slot_start < now:
                    continue

                # Check end time doesn't go past 18:30
                if slot_end.hour > 18 or (slot_end.hour == 18 and slot_end.minute > 30):
                    continue

                # Check conflicts
                conflicts = self._has_conflict(slot_start, slot_end, existing_slots)

                # Score: base 70, penalty for conflicts, bonus for preferred times
                score = 70.0
                if conflicts:
                    score -= 50.0  # Heavy penalty for conflicts
                if 10 <= hour <= 11 or 14 <= hour <= 16:
                    score += 15.0  # Preferred interview hours
                if hour == 12 or hour == 13:
                    score -= 20.0  # Lunch time penalty
                # Add slight randomness for variety
                score += random.uniform(-5, 5)

                reason = (
                    f"工作日{current_day.strftime('%m月%d日')} {hour}:00"
                    f"–{slot_end.strftime('%H:%M')}"
                )
                if not conflicts:
                    reason += "，无时间冲突"
                else:
                    reason += f"，存在{len(conflicts)}个冲突"

                recommended.append(TimeSlot(
                    start=slot_start,
                    end=slot_end,
                    score=round(score, 1),
                    reason=reason,
                    conflicts=conflicts,
                ))

            current_day += timedelta(days=1)

        # Sort by score descending, take top N
        recommended.sort(key=lambda s: s.score, reverse=True)
        top_slots = recommended[:num_slots]

        result = TimeSlotRecommendationResult(
            position_id=position_id,
            candidate_id=candidate_id,
            recommended_slots=top_slots,
            duration_minutes=duration_minutes,
        )

        logger.info(
            "Recommended %d timeslots (top score=%.1f)",
            len(top_slots),
            top_slots[0].score if top_slots else 0,
        )
        return result

    async def analyze_feedback(
        self,
        interview_id: UUID,
        tenant_id: str,
    ) -> FeedbackAnalysisResult:
        """Perform AI-powered analysis of interview feedback.

        Reads all interviewer feedback for an interview, then generates:
          - Overall score (weighted average)
          - Per-dimension score breakdown
          - Strengths and concerns
          - Hire recommendation (strong_yes/yes/no/strong_no)
          - Improvement suggestions for the candidate
          - Position fit score (0-100)

        Currently uses mock/placeholder logic. When a real LLM is wired in,
        replace the mock section with an actual prompt + parse.

        Args:
            interview_id: Interview UUID to analyze.
            tenant_id: Tenant scope identifier.

        Returns:
            FeedbackAnalysisResult dataclass with structured analysis.

        Raises:
            ValueError: If interview not found or no feedback available.
        """
        logger.info("Analyzing feedback for interview %s (tenant=%s)", interview_id, tenant_id)

        interview, candidate, position = await self._load_interview_context(
            interview_id, tenant_id
        )

        feedbacks = await self._load_feedbacks(interview_id)
        if not feedbacks:
            raise ValueError(f"No feedback found for interview {interview_id}")

        logger.debug("Found %d feedback entries to analyze", len(feedbacks))

        # ---- Aggregate scores ----
        scores = [f.score for f in feedbacks]
        overall_score = round(sum(scores) / len(scores), 2) if scores else 0.0

        # Build per-skill breakdown from skill_ratings
        skill_scores: dict[str, list[float]] = {}
        for fb in feedbacks:
            if fb.skill_ratings and isinstance(fb.skill_ratings, dict):
                for skill, rating in fb.skill_ratings.items():
                    skill_scores.setdefault(skill, []).append(float(rating))

        score_breakdown: dict[str, float] = {}
        for skill, vals in skill_scores.items():
            score_breakdown[skill] = round(sum(vals) / len(vals), 2)

        # If no skill breakdown, create mock dimensions
        if not score_breakdown:
            score_breakdown = {
                "技术能力": round(overall_score * 1.05, 2),
                "沟通表达": round(overall_score * 0.95, 2),
                "问题解决": round(overall_score * 1.0, 2),
                "团队协作": round(overall_score * 0.98, 2),
            }

        # ---- Collect strengths and concerns from feedback ----
        all_strengths: list[str] = []
        all_concerns: list[str] = []

        for fb in feedbacks:
            if fb.strengths:
                all_strengths.extend(
                    [s.strip() for s in fb.strengths.split(",") if s.strip()]
                )
            if fb.weaknesses:
                all_concerns.extend(
                    [w.strip() for w in fb.weaknesses.split(",") if w.strip()]
                )

        # ---- Mock LLM analysis — replace with real LLM call ----
        # Determine recommendation based on score
        if overall_score >= 8.0:
            recommendation = "strong_yes"
        elif overall_score >= 6.5:
            recommendation = "yes"
        elif overall_score >= 4.0:
            recommendation = "no"
        else:
            recommendation = "strong_no"

        # Generate mock analysis text
        recommendation_reason = (
            f"综合 {len(feedbacks)} 位面试官反馈，平均分 {overall_score}/10。"
        )
        if overall_score >= 8.0:
            recommendation_reason += "候选人表现优秀，强烈建议通过。"
        elif overall_score >= 6.5:
            recommendation_reason += "候选人表现良好，建议通过但可进一步考察部分领域。"
        elif overall_score >= 4.0:
            recommendation_reason += "候选人表现一般，建议谨慎考虑。"
        else:
            recommendation_reason += "候选人表现低于预期，建议不通过。"

        # Deduplicate and limit
        strengths = list(dict.fromkeys(all_strengths))[:6] or ["面试中表现积极", "沟通清晰"]
        concerns = list(dict.fromkeys(all_concerns))[:6] or ["部分领域需要进一步验证"]

        improvement_suggestions = [
            f"针对 {concern} 进行专项提升" for concern in concerns[:4]
        ]
        if not improvement_suggestions:
            improvement_suggestions = ["继续保持现有优势，关注行业动态"]

        # Calculate fit score (0-100) based on overall score
        candidate_fit_score = round(min(overall_score * 10, 100), 1)

        result = FeedbackAnalysisResult(
            interview_id=interview_id,
            overall_score=overall_score,
            score_breakdown=score_breakdown,
            strengths=strengths,
            concerns=concerns,
            recommendation=recommendation,
            recommendation_reason=recommendation_reason,
            improvement_suggestions=improvement_suggestions,
            candidate_fit_score=candidate_fit_score,
        )

        logger.info(
            "Feedback analysis complete: score=%.2f, recommendation=%s, fit=%.1f",
            result.overall_score,
            result.recommendation,
            result.candidate_fit_score,
        )
        return result
