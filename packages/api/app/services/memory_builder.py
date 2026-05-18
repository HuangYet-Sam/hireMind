"""
MemoryBuilder — 记忆构建引擎。

从 HR 操作日志中提取偏好、模式和决策记录，构建记忆库。
支持冷启动（7天历史分析）和增量学习。

核心能力:
  - extract_from_interaction: 从交互日志提取记忆
  - build_initial_memories: 7天冷启动（目标>50条）
  - learn_preference: 从单次决策学习偏好
  - detect_patterns: 检测招聘模式
  - consolidate_memories: 记忆合并与去重
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.interview import InterviewFeedback
from app.models.matching import Match, MatchFeedback
from app.models.memory import Memory
from app.models.offer import Offer
from app.models.position import Position
from app.schemas.memory import MemoryCreate

logger = logging.getLogger("hiremind.services.memory_builder")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryBuilder:
    """记忆构建引擎 — 从操作日志和历史数据中提取记忆。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ══════════════════════════════════════════════════════════════
    # 1. 从交互日志提取记忆
    # ══════════════════════════════════════════════════════════════

    async def extract_from_interaction(
        self,
        interaction_log: dict[str, Any],
        tenant_id: str,
    ) -> list[Memory]:
        """
        从 HR 操作日志提取记忆。

        解析操作日志，识别筛选决策、面试反馈、Offer 决策等，
        提取偏好（偏好某类候选人/薪资范围/技能权重）。

        Args:
            interaction_log: 操作日志字典，包含:
                - action: 操作类型 (screen_accept/screen_reject/interview_feedback/offer_send 等)
                - entity_id: 操作实体 ID
                - entity_type: 实体类型 (candidate/position/interview/offer)
                - data: 操作附加数据
                - user_id: 操作用户 ID
                - timestamp: 操作时间
            tenant_id: 租户 ID。

        Returns:
            提取到的记忆列表。
        """
        extracted: list[Memory] = []
        action = interaction_log.get("action", "")
        entity_type = interaction_log.get("entity_type", "")
        data = interaction_log.get("data", {})

        # 筛选决策 → 偏好记忆
        if action in ("screen_accept", "screen_reject"):
            memory = await self._extract_screening_memory(
                interaction_log, tenant_id,
            )
            if memory:
                extracted.append(memory)

        # 面试反馈 → 决策记忆 + 偏好
        elif action == "interview_feedback" and entity_type == "interview":
            memories = await self._extract_interview_memories(
                interaction_log, tenant_id,
            )
            extracted.extend(memories)

        # Offer 决策 → 偏好记忆
        elif action in ("offer_send", "offer_adjust", "offer_revoke"):
            memory = await self._extract_offer_memory(
                interaction_log, tenant_id,
            )
            if memory:
                extracted.append(memory)

        # 候选人推进/回退 → 决策模式
        elif action in ("advance_stage", "reject_candidate"):
            memory = await self._extract_stage_decision_memory(
                interaction_log, tenant_id,
            )
            if memory:
                extracted.append(memory)

        logger.info(
            "extract_from_interaction: action=%s extracted=%d tenant=%s",
            action, len(extracted), tenant_id,
        )
        return extracted

    # ══════════════════════════════════════════════════════════════
    # 2. 7天冷启动
    # ══════════════════════════════════════════════════════════════

    async def build_initial_memories(
        self,
        tenant_id: str,
        days: int = 7,
    ) -> dict[str, Any]:
        """
        7天冷启动 — 扫描最近 N 天所有操作日志，批量提取偏好和模式。

        目标: 生成 >50 条初始记忆。

        Args:
            tenant_id: 租户 ID。
            days: 回溯天数（默认 7）。

        Returns:
            构建结果统计。
        """
        start_time = time.time()
        total_extracted = 0
        new_count = 0
        updated_count = 0
        categories: dict[str, int] = {}

        cutoff = _now() - timedelta(days=days)

        # 1. 从筛选决策提取
        screen_memories = await self._extract_screening_history(
            tenant_id, cutoff,
        )
        for mem_data in screen_memories:
            created = await self._upsert_memory(mem_data, tenant_id)
            if created:
                new_count += 1
            else:
                updated_count += 1
            total_extracted += 1
            cat = mem_data.category
            categories[cat] = categories.get(cat, 0) + 1

        # 2. 从面试反馈提取
        interview_memories = await self._extract_interview_history(
            tenant_id, cutoff,
        )
        for mem_data in interview_memories:
            created = await self._upsert_memory(mem_data, tenant_id)
            if created:
                new_count += 1
            else:
                updated_count += 1
            total_extracted += 1
            cat = mem_data.category
            categories[cat] = categories.get(cat, 0) + 1

        # 3. 从 Offer 历史提取
        offer_memories = await self._extract_offer_history(
            tenant_id, cutoff,
        )
        for mem_data in offer_memories:
            created = await self._upsert_memory(mem_data, tenant_id)
            if created:
                new_count += 1
            else:
                updated_count += 1
            total_extracted += 1
            cat = mem_data.category
            categories[cat] = categories.get(cat, 0) + 1

        # 4. 检测招聘模式
        pattern_memories = await self.detect_patterns(tenant_id)
        for mem in pattern_memories:
            total_extracted += 1
            new_count += 1
            cat = mem.category
            categories[cat] = categories.get(cat, 0) + 1

        # 5. 生成基础事实记忆
        fact_memories = await self._extract_tenant_facts(tenant_id)
        for mem_data in fact_memories:
            created = await self._upsert_memory(mem_data, tenant_id)
            if created:
                new_count += 1
            else:
                updated_count += 1
            total_extracted += 1
            cat = mem_data.category
            categories[cat] = categories.get(cat, 0) + 1

        duration = time.time() - start_time
        logger.info(
            "build_initial_memories: tenant=%s total=%d new=%d updated=%d duration=%.1fs",
            tenant_id, total_extracted, new_count, updated_count, duration,
        )

        return {
            "total_extracted": total_extracted,
            "new_memories": new_count,
            "updated_memories": updated_count,
            "categories": categories,
            "duration_seconds": round(duration, 2),
        }

    # ══════════════════════════════════════════════════════════════
    # 3. 从单次决策学习偏好
    # ══════════════════════════════════════════════════════════════

    async def learn_preference(
        self,
        tenant_id: str,
        decision_data: dict[str, Any],
    ) -> Memory | None:
        """
        从单次决策学习偏好。

        分析 HR 的单次决策（通过/拒绝/调薪），提取偏好信息并
        更新或创建对应记忆。

        Args:
            tenant_id: 租户 ID。
            decision_data: 决策数据，包含:
                - decision_type: 决策类型 (accept/reject/adjust)
                - candidate_id: 候选人 ID
                - position_id: 岗位 ID
                - reason: 决策原因
                - salary: 薪资信息
                - skills: 技能评估
                - score: 评分

        Returns:
            创建或更新的 Memory 实例。
        """
        decision_type = decision_data.get("decision_type", "")
        reason = decision_data.get("reason", "")
        candidate_id = decision_data.get("candidate_id", "")
        position_id = decision_data.get("position_id", "")
        salary = decision_data.get("salary")
        skills = decision_data.get("skills", [])

        if not decision_type:
            return None

        content_parts: list[str] = []
        tags: list[str] = []

        # 分析薪资偏好
        if salary:
            content_parts.append(f"薪资相关决策: {salary}")
            tags.append("salary")

        # 分析技能偏好
        if skills:
            preferred_skills = [s for s in skills if isinstance(s, dict) and s.get("preferred")]
            if preferred_skills:
                skill_names = [s.get("name", "") for s in preferred_skills]
                content_parts.append(f"偏好技能: {', '.join(skill_names)}")
                tags.extend(skill_names)

        # 分析决策原因
        if reason:
            content_parts.append(f"决策原因: {reason}")

        if not content_parts:
            return None

        content = " | ".join(content_parts)
        confidence = 0.6 if decision_type == "accept" else 0.4
        importance = 0.7 if decision_type == "accept" else 0.5

        mem_data = MemoryCreate(
            memory_type="preference",
            category="recruitment",
            content=content,
            source="interaction",
            source_id=candidate_id or position_id,
            confidence=confidence,
            importance=importance,
            tags=tags,
            metadata_={
                "decision_type": decision_type,
                "candidate_id": candidate_id,
                "position_id": position_id,
            },
        )

        memory = Memory(
            tenant_id=tenant_id,
            **mem_data.model_dump(exclude_none=True, by_alias=False),
        )
        self.db.add(memory)
        await self.db.flush()

        logger.info(
            "learn_preference: tenant=%s type=%s candidate=%s",
            tenant_id, decision_type, candidate_id,
        )
        return memory

    # ══════════════════════════════════════════════════════════════
    # 4. 检测招聘模式
    # ══════════════════════════════════════════════════════════════

    async def detect_patterns(
        self,
        tenant_id: str,
    ) -> list[Memory]:
        """
        检测招聘模式（常用筛选条件、偏好渠道、决策模式）。

        扫描候选人数据，统计常见特征和决策趋势。

        Args:
            tenant_id: 租户 ID。

        Returns:
            检测到的模式记忆列表。
        """
        patterns: list[Memory] = []

        # 1. 统计通过的候选人常见技能
        skill_pattern = await self._detect_skill_pattern(tenant_id)
        if skill_pattern:
            patterns.append(skill_pattern)

        # 2. 统计薪资范围偏好
        salary_pattern = await self._detect_salary_pattern(tenant_id)
        if salary_pattern:
            patterns.append(salary_pattern)

        # 3. 统计学历偏好
        edu_pattern = await self._detect_education_pattern(tenant_id)
        if edu_pattern:
            patterns.append(edu_pattern)

        # 4. 统计招聘漏斗转化模式
        funnel_pattern = await self._detect_funnel_pattern(tenant_id)
        if funnel_pattern:
            patterns.append(funnel_pattern)

        # 持久化
        for p in patterns:
            self.db.add(p)
        if patterns:
            await self.db.flush()

        logger.info("detect_patterns: tenant=%s patterns=%d", tenant_id, len(patterns))
        return patterns

    # ══════════════════════════════════════════════════════════════
    # 5. 记忆合并
    # ══════════════════════════════════════════════════════════════

    async def consolidate_memories(
        self,
        tenant_id: str,
    ) -> dict[str, int]:
        """
        记忆合并 — 相似记忆合并、矛盾记忆更新。

        策略:
          1. 查找同类型、同分类的记忆
          2. 对内容相似度高的记忆进行合并
          3. 对矛盾的记忆保留最新的，标记旧的为非活跃
          4. 低于置信度阈值的弱记忆降级

        Args:
            tenant_id: 租户 ID。

        Returns:
            合并统计 {merged, contradicted, expired}.
        """
        stats = {"merged": 0, "contradicted": 0, "expired": 0}

        # 获取所有活跃记忆，按类型分组
        stmt = select(Memory).where(
            Memory.tenant_id == tenant_id,
            Memory.is_active == True,  # noqa: E712
        ).order_by(Memory.created_at.asc())
        result = await self.db.execute(stmt)
        all_memories = list(result.scalars().all())

        # 按类型+分类分组
        groups: dict[str, list[Memory]] = {}
        for mem in all_memories:
            key = f"{mem.memory_type}:{mem.category}"
            groups.setdefault(key, []).append(mem)

        # 在每组内检测相似和矛盾
        for group_key, memories in groups.items():
            for i, mem_a in enumerate(memories):
                if not mem_a.is_active:
                    continue
                for mem_b in memories[i + 1:]:
                    if not mem_b.is_active:
                        continue

                    similarity = self._text_similarity(
                        mem_a.content, mem_b.content,
                    )

                    if similarity > 0.85:
                        # 高度相似 → 合并（保留更重要的）
                        if mem_a.importance >= mem_b.importance:
                            mem_b.is_active = False
                            mem_a.confidence = max(mem_a.confidence, mem_b.confidence)
                        else:
                            mem_a.is_active = False
                            mem_b.confidence = max(mem_a.confidence, mem_b.confidence)
                        stats["merged"] += 1

                    elif similarity > 0.5 and self._is_contradictory(
                        mem_a.content, mem_b.content,
                    ):
                        # 可能为矛盾 → 保留最新
                        older = mem_a if mem_a.created_at < mem_b.created_at else mem_b
                        older.is_active = False
                        stats["contradicted"] += 1

        # 低置信度记忆降级
        for mem in all_memories:
            if mem.is_active and mem.confidence < 0.2 and mem.access_count == 0:
                mem.is_active = False
                stats["expired"] += 1

        await self.db.flush()
        logger.info(
            "consolidate_memories: tenant=%s stats=%s", tenant_id, stats,
        )
        return stats

    # ── 内部方法 ────────────────────────────────────────────────

    async def _extract_screening_memory(
        self,
        log: dict[str, Any],
        tenant_id: str,
    ) -> Memory | None:
        """从筛选决策提取记忆。"""
        data = log.get("data", {})
        action = log.get("action", "")
        candidate_id = data.get("candidate_id")
        reason = data.get("reason", "")
        position_id = data.get("position_id")

        if not candidate_id:
            return None

        content = (
            f"筛选{'通过' if 'accept' in action else '拒绝'}: "
            f"候选人 {candidate_id}"
        )
        if reason:
            content += f" — 原因: {reason}"
        if position_id:
            content += f" | 岗位: {position_id}"

        return Memory(
            tenant_id=tenant_id,
            memory_type="decision",
            category="candidate",
            content=content,
            source="interaction",
            source_id=candidate_id,
            confidence=0.7,
            importance=0.6,
            tags=["screening", "accept" if "accept" in action else "reject"],
            metadata_={"action": action, "position_id": position_id},
        )

    async def _extract_interview_memories(
        self,
        log: dict[str, Any],
        tenant_id: str,
    ) -> list[Memory]:
        """从面试反馈提取记忆。"""
        memories: list[Memory] = []
        data = log.get("data", {})
        interview_id = data.get("interview_id")
        score = data.get("score")
        feedback = data.get("feedback", "")
        candidate_id = data.get("candidate_id")

        if not interview_id:
            return memories

        # 决策记忆
        content = f"面试反馈: 面试 {interview_id}"
        if score is not None:
            content += f" | 评分: {score}"
        if feedback:
            content += f" | 反馈: {feedback[:200]}"
        if candidate_id:
            content += f" | 候选人: {candidate_id}"

        memories.append(Memory(
            tenant_id=tenant_id,
            memory_type="decision",
            category="interview",
            content=content,
            source="interaction",
            source_id=interview_id,
            confidence=0.8 if score else 0.5,
            importance=0.7,
            tags=["interview", "feedback"],
            metadata_={"interview_id": interview_id, "score": score},
        ))

        # 评分偏好记忆
        if score and score >= 4:
            memories.append(Memory(
                tenant_id=tenant_id,
                memory_type="preference",
                category="interview",
                content=f"高分面试偏好: 评分 {score}/5 — {feedback[:100]}",
                source="ai_inferred",
                source_id=interview_id,
                confidence=0.6,
                importance=0.5,
                tags=["interview", "high_score", "preference"],
            ))

        return memories

    async def _extract_offer_memory(
        self,
        log: dict[str, Any],
        tenant_id: str,
    ) -> Memory | None:
        """从 Offer 决策提取记忆。"""
        data = log.get("data", {})
        action = log.get("action", "")
        offer_id = data.get("offer_id")
        salary = data.get("salary")
        candidate_id = data.get("candidate_id")
        position_id = data.get("position_id")

        if not offer_id:
            return None

        content = f"Offer {action}: {offer_id}"
        if salary:
            content += f" | 薪资: {salary}"
        if candidate_id:
            content += f" | 候选人: {candidate_id}"
        if position_id:
            content += f" | 岗位: {position_id}"

        return Memory(
            tenant_id=tenant_id,
            memory_type="decision",
            category="offer",
            content=content,
            source="interaction",
            source_id=offer_id,
            confidence=0.8,
            importance=0.8,
            tags=["offer", action],
            metadata_={"salary": salary, "position_id": position_id},
        )

    async def _extract_stage_decision_memory(
        self,
        log: dict[str, Any],
        tenant_id: str,
    ) -> Memory | None:
        """从候选人推进/回退提取决策模式。"""
        data = log.get("data", {})
        action = log.get("action", "")
        candidate_id = data.get("candidate_id")
        from_stage = data.get("from_stage", "")
        to_stage = data.get("to_stage", "")
        reason = data.get("reason", "")

        if not candidate_id:
            return None

        content = f"候选人 {candidate_id}: {from_stage} → {to_stage}"
        if reason:
            content += f" — {reason}"

        return Memory(
            tenant_id=tenant_id,
            memory_type="decision",
            category="recruitment",
            content=content,
            source="log",
            source_id=candidate_id,
            confidence=0.5,
            importance=0.4,
            tags=["stage_change", action],
        )

    # ── 批量历史提取 ────────────────────────────────────────────

    async def _extract_screening_history(
        self, tenant_id: str, cutoff: datetime,
    ) -> list[MemoryCreate]:
        """从候选人筛选历史批量提取记忆。"""
        memories: list[MemoryCreate] = []

        # 获取最近 N 天的候选人记录
        candidates = (await self.db.execute(
            select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
                Candidate.updated_at >= cutoff,
            ).limit(200)
        )).scalars().all()

        for c in candidates:
            stage = c.stage or "applied"
            if stage in ("screened", "interviewed", "offered", "hired"):
                memories.append(MemoryCreate(
                    memory_type="decision",
                    category="candidate",
                    content=f"筛选通过: 候选人 {c.name or c.id}，当前阶段 {stage}",
                    source="log",
                    source_id=str(c.id),
                    confidence=0.6,
                    importance=0.5,
                    tags=["screening", "pass", stage],
                ))
            elif stage == "rejected":
                memories.append(MemoryCreate(
                    memory_type="decision",
                    category="candidate",
                    content=f"筛选拒绝: 候选人 {c.name or c.id}",
                    source="log",
                    source_id=str(c.id),
                    confidence=0.5,
                    importance=0.4,
                    tags=["screening", "reject"],
                ))

        return memories

    async def _extract_interview_history(
        self, tenant_id: str, cutoff: datetime,
    ) -> list[MemoryCreate]:
        """从面试历史批量提取记忆。"""
        memories: list[MemoryCreate] = []

        interviews = (await self.db.execute(
            select(Interview).where(
                Interview.tenant_id == tenant_id,
                Interview.status == "completed",
                Interview.updated_at >= cutoff,
                Interview.overall_score.isnot(None),
            ).limit(100)
        )).scalars().all()

        for iv in interviews:
            score = iv.overall_score or 0
            memories.append(MemoryCreate(
                memory_type="decision",
                category="interview",
                content=(
                    f"面试完成: 候选人 {iv.candidate_id} "
                    f"第{iv.round_number}轮 评分 {score}"
                ),
                source="log",
                source_id=str(iv.id),
                confidence=0.7,
                importance=0.6,
                tags=["interview", "feedback", f"round_{iv.round_number}"],
                metadata_={
                    "interview_type": iv.interview_type,
                    "score": score,
                },
            ))

        return memories

    async def _extract_offer_history(
        self, tenant_id: str, cutoff: datetime,
    ) -> list[MemoryCreate]:
        """从 Offer 历史批量提取记忆。"""
        memories: list[MemoryCreate] = []

        offers = (await self.db.execute(
            select(Offer).where(
                Offer.tenant_id == tenant_id,
                Offer.created_at >= cutoff,
            ).limit(100)
        )).scalars().all()

        for offer in offers:
            content = f"Offer: 候选人 {offer.candidate_id} 状态 {offer.status}"
            if offer.base_salary:
                content += f" | 基础薪资: {offer.base_salary}"

            memories.append(MemoryCreate(
                memory_type="decision",
                category="offer",
                content=content,
                source="log",
                source_id=str(offer.id),
                confidence=0.8,
                importance=0.7,
                tags=["offer", offer.status],
                metadata_={
                    "base_salary": offer.base_salary,
                    "position_id": str(offer.position_id) if offer.position_id else None,
                },
            ))

        return memories

    async def _extract_tenant_facts(
        self, tenant_id: str,
    ) -> list[MemoryCreate]:
        """提取租户基础事实记忆。"""
        facts: list[MemoryCreate] = []

        # 统计岗位分布
        position_count = await self.db.scalar(
            select(func.count()).select_from(Position).where(
                Position.tenant_id == tenant_id,
                Position.status == "open",
            )
        ) or 0

        facts.append(MemoryCreate(
            memory_type="fact",
            category="team",
            content=f"当前在招岗位数: {position_count}",
            source="system",
            confidence=1.0,
            importance=0.3,
            tags=["position_count", "fact"],
        ))

        # 统计候选人分布
        candidate_count = await self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
            )
        ) or 0

        facts.append(MemoryCreate(
            memory_type="fact",
            category="team",
            content=f"当前活跃候选人数: {candidate_count}",
            source="system",
            confidence=1.0,
            importance=0.3,
            tags=["candidate_count", "fact"],
        ))

        return facts

    # ── 模式检测 ────────────────────────────────────────────────

    async def _detect_skill_pattern(
        self, tenant_id: str,
    ) -> Memory | None:
        """检测技能偏好模式。"""
        # 统计被推进到面试阶段的候选人的技能
        advanced = (await self.db.execute(
            select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
                Candidate.stage.in_(["interviewed", "offered", "hired"]),
            ).limit(100)
        )).scalars().all()

        if not advanced:
            return None

        # 从候选人 profile 中提取技能频率
        skill_freq: dict[str, int] = {}
        for c in advanced:
            profile = c.profile or {}
            skills = profile.get("skills", [])
            for skill in skills:
                if isinstance(skill, dict):
                    name = skill.get("name", "").strip()
                elif isinstance(skill, str):
                    name = skill.strip()
                else:
                    continue
                if name:
                    skill_freq[name] = skill_freq.get(name, 0) + 1

        if not skill_freq:
            return None

        top_skills = sorted(skill_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        content = (
            f"高频通过技能: {', '.join(f'{name}({count})' for name, count in top_skills)}"
        )

        return Memory(
            tenant_id=tenant_id,
            memory_type="pattern",
            category="candidate",
            content=content,
            source="ai_inferred",
            confidence=0.6,
            importance=0.7,
            tags=["skill_pattern", "frequent_skills"],
        )

    async def _detect_salary_pattern(
        self, tenant_id: str,
    ) -> Memory | None:
        """检测薪资偏好模式。"""
        # 从已发送的 Offer 中统计薪资范围
        offers = (await self.db.execute(
            select(Offer).where(
                Offer.tenant_id == tenant_id,
                Offer.status.in_(["accepted", "sent"]),
                Offer.base_salary.isnot(None),
            ).limit(50)
        )).scalars().all()

        if not offers:
            return None

        salaries = [
            float(o.base_salary) for o in offers
            if o.base_salary is not None
        ]
        if not salaries:
            return None

        avg_salary = sum(salaries) / len(salaries)
        min_salary = min(salaries)
        max_salary = max(salaries)

        content = (
            f"薪资偏好范围: {min_salary:.0f}-{max_salary:.0f}/月, "
            f"均值 {avg_salary:.0f}/月 (基于 {len(salaries)} 个 Offer)"
        )

        return Memory(
            tenant_id=tenant_id,
            memory_type="pattern",
            category="offer",
            content=content,
            source="ai_inferred",
            confidence=0.7,
            importance=0.8,
            tags=["salary_pattern", "compensation"],
        )

    async def _detect_education_pattern(
        self, tenant_id: str,
    ) -> Memory | None:
        """检测学历偏好模式。"""
        hired = (await self.db.execute(
            select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.stage == "hired",
            ).limit(50)
        )).scalars().all()

        if not hired:
            return None

        edu_freq: dict[str, int] = {}
        for c in hired:
            profile = c.profile or {}
            edu_list = profile.get("education", [])
            for edu in edu_list:
                if isinstance(edu, dict):
                    degree = edu.get("degree", "").strip()
                    if degree:
                        edu_freq[degree] = edu_freq.get(degree, 0) + 1

        if not edu_freq:
            return None

        content = (
            f"录用学历分布: {', '.join(f'{d}({c})' for d, c in edu_freq.items())}"
        )

        return Memory(
            tenant_id=tenant_id,
            memory_type="pattern",
            category="candidate",
            content=content,
            source="ai_inferred",
            confidence=0.5,
            importance=0.5,
            tags=["education_pattern"],
        )

    async def _detect_funnel_pattern(
        self, tenant_id: str,
    ) -> Memory | None:
        """检测漏斗转化模式。"""
        rows = (await self.db.execute(
            select(Candidate.stage, func.count().label("count")).where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
            ).group_by(Candidate.stage)
        )).all()

        if not rows:
            return None

        stage_counts = {row.stage: row.count for row in rows}
        stages = ["applied", "screened", "interviewed", "offered", "hired"]
        distribution = " → ".join(
            f"{s}:{stage_counts.get(s, 0)}" for s in stages
        )

        return Memory(
            tenant_id=tenant_id,
            memory_type="pattern",
            category="recruitment",
            content=f"招聘漏斗分布: {distribution}",
            source="system",
            confidence=0.9,
            importance=0.6,
            tags=["funnel", "pipeline"],
        )

    # ── Upsert Helper ───────────────────────────────────────────

    async def _upsert_memory(
        self,
        data: MemoryCreate,
        tenant_id: str,
    ) -> bool:
        """
        创建记忆（如已存在相似内容则更新置信度）。

        Returns:
            True 表示新创建，False 表示更新已有。
        """
        # 检查是否存在相似记忆（简化: 按 source + source_id 查重）
        existing = None
        if data.source_id:
            existing = (await self.db.execute(
                select(Memory).where(
                    Memory.tenant_id == tenant_id,
                    Memory.source_id == data.source_id,
                    Memory.memory_type == data.memory_type,
                    Memory.is_active == True,  # noqa: E712
                ).limit(1)
            )).scalar_one_or_none()

        if existing:
            # 更新置信度
            existing.confidence = max(existing.confidence, data.confidence)
            existing.importance = max(existing.importance, data.importance)
            await self.db.flush()
            return False

        memory = Memory(
            tenant_id=tenant_id,
            memory_type=data.memory_type,
            category=data.category,
            content=data.content,
            source=data.source,
            source_id=data.source_id,
            confidence=data.confidence,
            importance=data.importance,
            expires_at=data.expires_at,
            tags=data.tags or [],
            metadata_=data.metadata_ or {},
        )
        self.db.add(memory)
        await self.db.flush()
        return True

    # ── Text Similarity (simplified) ────────────────────────────

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        """
        简化的文本相似度（基于 Jaccard 词集合相似度）。

        生产环境应替换为基于 embedding 的语义相似度。
        """
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0

    @staticmethod
    def _is_contradictory(a: str, b: str) -> bool:
        """
        简化的矛盾检测（基于否定词匹配）。

        检测是否一个包含"通过/接受/偏好"而另一个包含"拒绝/否/不"。
        """
        positive = {"通过", "接受", "偏好", "推荐", "高分", "优秀"}
        negative = {"拒绝", "不", "否", "低分", "淘汰", "不符合"}

        a_words = set(a)
        b_words = set(b)
        a_has_pos = bool(a_words & positive)
        a_has_neg = bool(a_words & negative)
        b_has_pos = bool(b_words & positive)
        b_has_neg = bool(b_words & negative)

        return (a_has_pos and b_has_neg) or (a_has_neg and b_has_pos)
