"""
Matching Service 扩展 (M4) — 智能匹配全流程编排。

组合 EmbeddingService + RRFSearchEngine + RerankEngine，
实现「岗位→候选人」和「候选人→岗位」的双向智能匹配。

匹配流程:
  1. 向量化: 对查询方（岗位/候选人）生成 Embedding
  2. 混合检索: RRF 融合关键词+向量检索召回候选集
  3. 精排: RerankEngine 基于 LLM 对候选集重新排序
  4. 解释生成: 为每个匹配生成自然语言分析
  5. 持久化: 保存匹配结果和反馈

此模块同时负责 Tool 注册（与 Hermes Agent 集成）。
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.matching import Match, MatchFeedback
from app.models.position import Position
from app.services.embedding_service import EmbeddingService, EmbeddingResult
from app.services.rrf_search import RRFSearchEngine, SearchResult, SearchSource
from app.services.rerank_engine import RerankEngine, RankedCandidate, MatchExplanation

logger = logging.getLogger("hiremind.matching_service_extended")

# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------

@dataclass
class MatchItem:
    """
    单条匹配结果。

    Attributes:
        candidate_id: 候选人 ID（岗位→候选人匹配时使用）
        position_id: 岗位 ID（候选人→岗位匹配时使用）
        score: 最终匹配得分 (0-100)
        rank: 排名 (1-based)
        explanation: 匹配解释
        source_scores: 各阶段得分明细
    """
    candidate_id: str | None = None
    position_id: str | None = None
    score: float = 0.0
    rank: int = 0
    explanation: MatchExplanation | None = None
    source_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class MatchResult:
    """
    匹配结果集。

    Attributes:
        query_type: 查询类型 ("position_to_candidates" | "candidate_to_positions")
        query_id: 查询方实体 ID
        matches: 匹配结果列表
        total_count: 总匹配数
        search_strategy: 使用的搜索策略描述
    """
    query_type: str
    query_id: str
    matches: list[MatchItem] = field(default_factory=list)
    total_count: int = 0
    search_strategy: str = "embedding+rrf+rerank"


@dataclass
class MatchDetail:
    """
    完整的匹配分析报告。

    包含查询方和被匹配方的详细信息，以及完整的匹配分析。
    """
    position_id: str
    candidate_id: str
    overall_score: float = 0.0
    skill_match_score: float = 0.0
    experience_match_score: float = 0.0
    education_match_score: float = 0.0
    semantic_similarity: float = 0.0
    rerank_score: float = 0.0
    strengths: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)
    recommendation: str = "neutral"
    detailed_analysis: str = ""
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    position_info: dict[str, Any] = field(default_factory=dict)
    candidate_info: dict[str, Any] = field(default_factory=dict)
    source_scores: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    analyzed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于 JSON 序列化）。"""
        return {
            "position_id": self.position_id,
            "candidate_id": self.candidate_id,
            "overall_score": self.overall_score,
            "skill_match_score": self.skill_match_score,
            "experience_match_score": self.experience_match_score,
            "education_match_score": self.education_match_score,
            "semantic_similarity": self.semantic_similarity,
            "rerank_score": self.rerank_score,
            "strengths": self.strengths,
            "concerns": self.concerns,
            "recommendation": self.recommendation,
            "detailed_analysis": self.detailed_analysis,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "position_info": self.position_info,
            "candidate_info": self.candidate_info,
            "source_scores": self.source_scores,
            "confidence": self.confidence,
            "analyzed_at": self.analyzed_at,
        }


# ---------------------------------------------------------------------------
# Matching Service 扩展
# ---------------------------------------------------------------------------

class MatchingServiceExtended:
    """
    智能匹配服务扩展 — 组合三引擎的匹配全流程编排。

    三引擎协作:
      1. EmbeddingService: 向量化 + 语义相似度
      2. RRFSearchEngine: 关键词+向量混合检索 + RRF 融合
      3. RerankEngine: LLM 精排 + 匹配解释生成
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._embedding_service = EmbeddingService(db)
        self._rrf_engine = RRFSearchEngine(db)
        self._rerank_engine = RerankEngine()

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    async def match_position_to_candidates(
        self,
        position_id: int | UUID,
        *,
        tenant_id: str | None = None,
        top_k: int = 20,
        keyword_weight: float = 0.4,
        vector_weight: float = 0.6,
    ) -> MatchResult:
        """
        岗位→候选人匹配全流程。

        流程:
          1. 加载岗位信息，生成 JD 向量
          2. 构建搜索查询（关键词 = JD 关键信息）
          3. RRF 混合检索召回候选人
          4. Rerank 精排
          5. 持久化匹配结果

        Args:
            position_id: 岗位 ID。
            tenant_id: 租户 ID（用于过滤）。
            top_k: 返回的最大匹配数。
            keyword_weight: 关键词检索权重。
            vector_weight: 向量检索权重。

        Returns:
            MatchResult 匹配结果集。

        Raises:
            ValueError: 岗位不存在。
        """
        position = await self._load_position(position_id)
        if position is None:
            raise ValueError(f"Position not found: {position_id}")

        effective_tenant_id = tenant_id or position.tenant_id or "default"

        # Step 1: 生成 JD 向量
        logger.info(
            "match_position_to_candidates: position=%s title='%s'",
            position_id, position.title,
        )
        jd_embedding = await self._embedding_service.generate_jd_embedding(position_id)

        # Step 2: 构建搜索关键词
        search_query = self._build_position_search_query(position)

        # Step 3: RRF 混合检索
        filters: dict[str, Any] = {
            "entity_type": "candidate",
            "tenant_id": effective_tenant_id,
        }
        search_results = await self._rrf_engine.hybrid_search(
            query=search_query,
            query_embedding=jd_embedding,
            filters=filters,
            top_k=top_k * 2,  # 多召回一些给精排用
            keyword_weight=keyword_weight,
            vector_weight=vector_weight,
        )

        if not search_results:
            logger.info("match_position_to_candidates: 无检索结果")
            return MatchResult(
                query_type="position_to_candidates",
                query_id=str(position_id),
                total_count=0,
            )

        # Step 4: 加载候选人画像 + Rerank 精排
        candidates_for_rerank = await self._enrich_search_results(
            search_results, "candidate",
        )
        ranked_candidates = await self._rerank_engine.rerank(
            query=self._build_position_description(position),
            candidates=candidates_for_rerank,
            top_k=top_k,
        )

        # Step 5: 构建匹配结果
        match_items: list[MatchItem] = []
        for ranked in ranked_candidates:
            source_scores = {
                "rrf_score": ranked.original_score,
                "rerank_score": ranked.reranked_score,
            }
            if ranked.explanation:
                source_scores["llm_confidence"] = ranked.explanation.confidence

            match_items.append(MatchItem(
                candidate_id=ranked.candidate_id,
                position_id=str(position_id),
                score=ranked.reranked_score,
                rank=ranked.rank,
                explanation=ranked.explanation,
                source_scores=source_scores,
            ))

        # Step 6: 持久化
        await self._persist_match_results(
            position_id=UUID(str(position_id)),
            matches=match_items,
            tenant_id=effective_tenant_id,
            query_type="position_to_candidates",
        )

        result = MatchResult(
            query_type="position_to_candidates",
            query_id=str(position_id),
            matches=match_items,
            total_count=len(match_items),
            search_strategy=f"embedding+rrf(kw={keyword_weight},vec={vector_weight})+rerank",
        )

        logger.info(
            "match_position_to_candidates: position=%s results=%d top_score=%.1f",
            position_id, result.total_count,
            match_items[0].score if match_items else 0,
        )
        return result

    async def match_candidate_to_positions(
        self,
        candidate_id: int | UUID,
        *,
        tenant_id: str | None = None,
        top_k: int = 10,
    ) -> MatchResult:
        """
        候选人→岗位反向匹配全流程。

        流程:
          1. 加载候选人信息，生成画像向量
          2. 构建搜索查询（候选人核心技能）
          3. RRF 混合检索召回岗位
          4. Rerank 精排
          5. 持久化匹配结果

        Args:
            candidate_id: 候选人 ID。
            tenant_id: 租户 ID（用于过滤）。
            top_k: 返回的最大匹配数。

        Returns:
            MatchResult 匹配结果集。

        Raises:
            ValueError: 候选人不存在。
        """
        candidate = await self._load_candidate(candidate_id)
        if candidate is None:
            raise ValueError(f"Candidate not found: {candidate_id}")

        if tenant_id is None:
            tenant_id = candidate.tenant_id

        # Step 1: 生成候选人向量
        logger.info(
            "match_candidate_to_positions: candidate=%s", candidate_id,
        )
        candidate_embedding = await self._embedding_service.generate_candidate_embedding(
            candidate_id,
        )

        # Step 2: 构建搜索关键词（基于候选人技能）
        search_query = self._build_candidate_search_query(candidate)

        # Step 3: RRF 混合检索
        filters: dict[str, Any] = {
            "entity_type": "position",
            "tenant_id": tenant_id,
        }
        search_results = await self._rrf_engine.hybrid_search(
            query=search_query,
            query_embedding=candidate_embedding,
            filters=filters,
            top_k=top_k * 2,
        )

        if not search_results:
            logger.info("match_candidate_to_positions: 无检索结果")
            return MatchResult(
                query_type="candidate_to_positions",
                query_id=str(candidate_id),
                total_count=0,
            )

        # Step 4: 加载岗位信息 + Rerank 精排
        positions_for_rerank = await self._enrich_search_results(
            search_results, "position",
        )
        ranked_positions = await self._rerank_engine.rerank(
            query=self._build_candidate_description(candidate),
            candidates=positions_for_rerank,
            top_k=top_k,
        )

        # Step 5: 构建匹配结果
        match_items: list[MatchItem] = []
        for ranked in ranked_positions:
            source_scores = {
                "rrf_score": ranked.original_score,
                "rerank_score": ranked.reranked_score,
            }
            if ranked.explanation:
                source_scores["llm_confidence"] = ranked.explanation.confidence

            match_items.append(MatchItem(
                candidate_id=str(candidate_id),
                position_id=ranked.candidate_id,  # 此处 candidate_id 实际是 position_id
                score=ranked.reranked_score,
                rank=ranked.rank,
                explanation=ranked.explanation,
                source_scores=source_scores,
            ))

        # Step 6: 持久化
        for item in match_items:
            if item.position_id:
                await self._persist_single_match(
                    position_id=UUID(item.position_id),
                    candidate_id=UUID(str(candidate_id)),
                    score=item.score,
                    source_scores=item.source_scores,
                    tenant_id=tenant_id,
                )

        result = MatchResult(
            query_type="candidate_to_positions",
            query_id=str(candidate_id),
            matches=match_items,
            total_count=len(match_items),
            search_strategy="embedding+rrf+rerank",
        )

        logger.info(
            "match_candidate_to_positions: candidate=%s results=%d top_score=%.1f",
            candidate_id, result.total_count,
            match_items[0].score if match_items else 0,
        )
        return result

    async def get_match_detail(
        self,
        position_id: int | UUID,
        candidate_id: int | UUID,
    ) -> MatchDetail:
        """
        获取匹配详情。

        返回完整的匹配分析报告，包含:
          - 各维度得分（技能、经验、教育、语义相似度、精排分）
          - 优劣势分析
          - 匹配/缺失技能
          - 岗位和候选人信息摘要

        Args:
            position_id: 岗位 ID。
            candidate_id: 候选人 ID。

        Returns:
            MatchDetail 完整匹配分析报告。

        Raises:
            ValueError: 岗位或候选人不存在。
        """
        position = await self._load_position(position_id)
        if position is None:
            raise ValueError(f"Position not found: {position_id}")

        candidate = await self._load_candidate(candidate_id)
        if candidate is None:
            raise ValueError(f"Candidate not found: {candidate_id}")

        # 并行计算各维度
        position_embedding = await self._embedding_service.generate_jd_embedding(position_id)
        candidate_embedding = await self._embedding_service.generate_candidate_embedding(candidate_id)
        semantic_similarity = await self._embedding_service.get_similarity(
            position_embedding, candidate_embedding,
        )

        # 技能匹配分析
        profile = candidate.profile or {}
        cand_skills = self._extract_skill_names(profile)
        pos_skills = self._extract_position_skills(position)
        matched_skills, missing_skills, skill_score = self._calculate_skill_match(
            pos_skills, cand_skills,
        )

        # 经验匹配
        experience_score = self._calculate_experience_match(profile, position)

        # 教育匹配
        education_score = self._calculate_education_match(profile, position)

        # Rerank 生成详细解释
        position_info = self._build_position_dict(position)
        candidate_info = self._build_candidate_dict(candidate)
        explanation = await self._rerank_engine.generate_match_explanation(
            query=position_info,
            candidate={
                "candidate_id": str(candidate_id),
                "profile": profile,
                "score": semantic_similarity,
            },
        )

        # 综合得分
        overall_score = (
            skill_score * 0.35
            + experience_score * 0.20
            + education_score * 0.10
            + semantic_similarity * 100 * 0.20
            + explanation.overall_score * 0.15
        )
        overall_score = min(100.0, max(0.0, overall_score))

        # 尝试从已有的 Match 记录加载
        rerank_score = 0.0
        match_record = await self._load_match_record(position_id, candidate_id)
        if match_record:
            rerank_score = match_record.overall_score or 0.0

        detail = MatchDetail(
            position_id=str(position_id),
            candidate_id=str(candidate_id),
            overall_score=round(overall_score, 2),
            skill_match_score=round(skill_score, 2),
            experience_match_score=round(experience_score, 2),
            education_match_score=round(education_score, 2),
            semantic_similarity=round(semantic_similarity, 4),
            rerank_score=round(rerank_score, 2),
            strengths=explanation.strengths,
            concerns=explanation.concerns,
            recommendation=explanation.recommendation,
            detailed_analysis="",
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            position_info=position_info,
            candidate_info=candidate_info,
            source_scores={
                "skill": skill_score,
                "experience": experience_score,
                "education": education_score,
                "semantic": semantic_similarity,
                "rerank": rerank_score,
                "llm_overall": explanation.overall_score,
            },
            confidence=explanation.confidence,
            analyzed_at=datetime.utcnow().isoformat(),
        )

        logger.info(
            "get_match_detail: position=%s candidate=%s overall=%.1f",
            position_id, candidate_id, overall_score,
        )
        return detail

    async def collect_feedback(
        self,
        position_id: int | UUID,
        candidate_id: int | UUID,
        feedback: dict[str, Any],
    ) -> None:
        """
        收集匹配反馈。

        用户可以对匹配结果给出反馈（好评/差评/准确度评分等），
        用于后续优化匹配算法和模型微调。

        Args:
            position_id: 岗位 ID。
            candidate_id: 候选人 ID。
            feedback: 反馈信息，包含:
                      - feedback_type: "positive" | "negative" | "neutral"
                      - reason: 反馈原因（可选）
                      - ai_accuracy_score: 1-5 准确度评分（可选）
                      - user_id: 用户 ID
                      - tenant_id: 租户 ID
        """
        feedback_type = feedback.get("feedback_type", "neutral")
        reason = feedback.get("reason")
        ai_accuracy_score = feedback.get("ai_accuracy_score")
        user_id = feedback.get("user_id")
        tenant_id = feedback.get("tenant_id", "default")

        # 查找已有的 Match 记录
        match_record = await self._load_match_record(position_id, candidate_id)
        if match_record is None:
            logger.warning(
                "collect_feedback: 未找到匹配记录 position=%s candidate=%s",
                position_id, candidate_id,
            )
            return

        # 创建反馈记录
        match_feedback = MatchFeedback(
            tenant_id=tenant_id,
            match_id=match_record.id,
            user_id=UUID(str(user_id)) if user_id else UUID("00000000-0000-0000-0000-000000000000"),
            feedback_type=feedback_type,
            reason=reason,
            ai_accuracy_score=ai_accuracy_score,
        )
        self.db.add(match_feedback)

        # 更新 Match 的 feedback 字段
        existing_feedback = match_record.candidate_feedback or {}
        feedback_entries = existing_feedback.get("entries", [])
        feedback_entries.append({
            "type": feedback_type,
            "reason": reason,
            "accuracy_score": ai_accuracy_score,
            "timestamp": datetime.utcnow().isoformat(),
        })
        match_record.candidate_feedback = {
            "entries": feedback_entries,
            "latest_type": feedback_type,
            "count": len(feedback_entries),
        }

        await self.db.flush()

        logger.info(
            "collect_feedback: position=%s candidate=%s type=%s",
            position_id, candidate_id, feedback_type,
        )

    # ------------------------------------------------------------------
    # Tool 注册（与 Hermes Agent 集成）
    # ------------------------------------------------------------------

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """
        返回可注册到 Hermes Agent 的 Tool 定义列表。

        每个工具定义遵循 OpenAI Function Calling 格式。
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "hr_match_position_to_candidates",
                    "description": "为指定岗位智能匹配最合适的候选人列表",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "position_id": {
                                "type": "string",
                                "description": "岗位 UUID",
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "返回的最大匹配数量",
                                "default": 20,
                            },
                        },
                        "required": ["position_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "hr_match_candidate_to_positions",
                    "description": "为指定候选人推荐最匹配的岗位列表",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "candidate_id": {
                                "type": "string",
                                "description": "候选人 UUID",
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "返回的最大匹配数量",
                                "default": 10,
                            },
                        },
                        "required": ["candidate_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "hr_get_match_detail",
                    "description": "获取指定岗位与候选人之间的详细匹配分析报告",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "position_id": {
                                "type": "string",
                                "description": "岗位 UUID",
                            },
                            "candidate_id": {
                                "type": "string",
                                "description": "候选人 UUID",
                            },
                        },
                        "required": ["position_id", "candidate_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "hr_collect_match_feedback",
                    "description": "收集用户对匹配结果的反馈",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "position_id": {
                                "type": "string",
                                "description": "岗位 UUID",
                            },
                            "candidate_id": {
                                "type": "string",
                                "description": "候选人 UUID",
                            },
                            "feedback_type": {
                                "type": "string",
                                "enum": ["positive", "negative", "neutral"],
                                "description": "反馈类型",
                            },
                            "reason": {
                                "type": "string",
                                "description": "反馈原因",
                            },
                        },
                        "required": ["position_id", "candidate_id", "feedback_type"],
                    },
                },
            },
        ]

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        执行 Tool 调用。

        由 Hermes Agent 调用，根据 tool_name 分发到对应的方法。

        Args:
            tool_name: 工具名称。
            arguments: 工具参数。

        Returns:
            工具执行结果。
        """
        logger.info("execute_tool: tool=%s args=%s", tool_name, list(arguments.keys()))

        if tool_name == "hr_match_position_to_candidates":
            return await self.match_position_to_candidates(
                position_id=arguments["position_id"],
                top_k=arguments.get("top_k", 20),
            )

        elif tool_name == "hr_match_candidate_to_positions":
            return await self.match_candidate_to_positions(
                candidate_id=arguments["candidate_id"],
                top_k=arguments.get("top_k", 10),
            )

        elif tool_name == "hr_get_match_detail":
            return await self.get_match_detail(
                position_id=arguments["position_id"],
                candidate_id=arguments["candidate_id"],
            )

        elif tool_name == "hr_collect_match_feedback":
            await self.collect_feedback(
                position_id=arguments["position_id"],
                candidate_id=arguments["candidate_id"],
                feedback={
                    "feedback_type": arguments["feedback_type"],
                    "reason": arguments.get("reason"),
                    "user_id": arguments.get("user_id"),
                    "tenant_id": arguments.get("tenant_id"),
                },
            )
            return {"status": "ok"}

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    # ------------------------------------------------------------------
    # 内部方法 — 数据加载
    # ------------------------------------------------------------------

    async def _load_position(self, position_id: int | UUID) -> Position | None:
        """加载岗位记录。"""
        pid = UUID(str(position_id))
        stmt = select(Position).where(Position.id == pid)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _load_candidate(self, candidate_id: int | UUID) -> Candidate | None:
        """加载候选人记录。"""
        cid = UUID(str(candidate_id))
        stmt = select(Candidate).where(Candidate.id == cid)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _load_match_record(
        self,
        position_id: int | UUID,
        candidate_id: int | UUID,
    ) -> Match | None:
        """加载已有的 Match 记录。"""
        stmt = select(Match).where(
            Match.position_id == UUID(str(position_id)),
            Match.candidate_id == UUID(str(candidate_id)),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # 内部方法 — 搜索查询构建
    # ------------------------------------------------------------------

    def _build_position_search_query(self, position: Position) -> str:
        """构建岗位搜索查询文本。"""
        parts: list[str] = []
        if position.title:
            parts.append(position.title)
        if position.required_skills:
            if isinstance(position.required_skills, list):
                skill_names = [
                    s.get("skill", s) if isinstance(s, dict) else str(s)
                    for s in position.required_skills
                ]
                parts.extend(skill_names)
        if position.description:
            # 截取描述的关键部分
            parts.append(position.description[:500])
        return " ".join(parts)

    def _build_candidate_search_query(self, candidate: Candidate) -> str:
        """构建候选人搜索查询文本。"""
        profile = candidate.profile or {}
        parts: list[str] = []

        # 技能
        skills = profile.get("skills", [])
        if isinstance(sills := skills, list):
            for s in skills:
                if isinstance(s, dict):
                    parts.append(s.get("name", ""))
                else:
                    parts.append(str(s))
        elif isinstance(skills, dict):
            parts.extend(skills.keys())

        # 当前职位
        basic = profile.get("basic_info", {})
        if isinstance(basic, dict):
            title = basic.get("current_title", "")
            if title:
                parts.append(title)

        return " ".join(parts)

    def _build_position_description(self, position: Position) -> str:
        """构建完整的岗位描述（给 LLM 使用）。"""
        parts: list[str] = []
        if position.title:
            parts.append(f"职位名称: {position.title}")
        if position.description:
            parts.append(f"职位描述: {position.description}")
        if position.requirements:
            parts.append(f"任职要求: {position.requirements}")
        if position.required_skills:
            parts.append(f"必备技能: {json.dumps(position.required_skills, ensure_ascii=False)}")
        if position.required_exp_min is not None:
            parts.append(f"最低经验要求: {position.required_exp_min} 年")
        if position.education_requirement:
            parts.append(f"学历要求: {position.education_requirement}")
        if position.location:
            parts.append(f"工作地点: {position.location}")
        return "\n".join(parts)

    def _build_candidate_description(self, candidate: Candidate) -> str:
        """构建完整的候选人描述（给 LLM 使用）。"""
        profile = candidate.profile or {}
        parts: list[str] = []

        basic = profile.get("basic_info", {})
        if isinstance(basic, dict):
            parts.append(f"姓名: {basic.get('name', '未知')}")
            parts.append(f"当前职位: {basic.get('current_title', '未知')}")
            parts.append(f"当前公司: {basic.get('current_company', '未知')}")
            parts.append(f"工作年限: {basic.get('years_of_experience', '未知')}")

        skills = profile.get("skills", [])
        if skills:
            if isinstance(skills, list):
                skill_names = [
                    s.get("name", s) if isinstance(s, dict) else str(s)
                    for s in skills
                ]
                parts.append(f"技能: {', '.join(skill_names)}")
            elif isinstance(skills, dict):
                parts.append(f"技能: {', '.join(skills.keys())}")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # 内部方法 — 搜索结果增强
    # ------------------------------------------------------------------

    async def _enrich_search_results(
        self,
        search_results: list[SearchResult],
        entity_type: str,
    ) -> list[dict[str, Any]]:
        """
        为搜索结果加载完整实体信息。

        Args:
            search_results: RRF 检索结果。
            entity_type: 实体类型。

        Returns:
            带有完整 profile 的字典列表（给 Rerank 使用）。
        """
        enriched: list[dict[str, Any]] = []

        for sr in search_results:
            entity_id = sr.entity_id
            profile_data: dict[str, Any] = {}

            try:
                entity_uuid = UUID(entity_id)
                if entity_type == "candidate":
                    stmt = select(Candidate).where(Candidate.id == entity_uuid)
                else:
                    stmt = select(Position).where(Position.id == entity_uuid)
                result = await self.db.execute(stmt)
                entity = result.scalar_one_or_none()

                if entity is None:
                    continue

                if entity_type == "candidate":
                    profile_data = entity.profile or {}
                else:
                    profile_data = {
                        "title": entity.title,
                        "description": entity.description,
                        "requirements": entity.requirements,
                        "required_skills": entity.required_skills,
                        "location": entity.location,
                    }
            except Exception as exc:
                logger.warning(
                    "_enrich_search_results: 加载 %s/%s 失败: %s",
                    entity_type, entity_id, exc,
                )
                continue

            enriched.append({
                "candidate_id": entity_id,
                "score": sr.score,
                "profile": profile_data,
            })

        return enriched

    # ------------------------------------------------------------------
    # 内部方法 — 匹配计算
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_skill_names(profile: dict[str, Any]) -> list[str]:
        """从候选人 profile 中提取技能名称列表。"""
        skills = profile.get("skills", [])
        if isinstance(skills, list):
            return [
                s.get("name", s) if isinstance(s, dict) else str(s)
                for s in skills
            ]
        if isinstance(skills, dict):
            return list(skills.keys())
        return []

    @staticmethod
    def _extract_position_skills(position: Position) -> list[str]:
        """从岗位中提取技能名称列表。"""
        required_skills = position.required_skills or []
        result: list[str] = []
        for s in required_skills:
            if isinstance(s, dict):
                result.append(s.get("skill", s.get("name", "")))
            else:
                result.append(str(s))
        return result

    @staticmethod
    def _calculate_skill_match(
        position_skills: list[str],
        candidate_skills: list[str],
    ) -> tuple[list[str], list[str], float]:
        """
        计算技能匹配度。

        Returns:
            (matched_skills, missing_skills, score)
        """
        if not position_skills:
            return [], [], 50.0

        cand_lower = [s.lower() for s in candidate_skills]
        matched = [s for s in position_skills if s.lower() in cand_lower]
        missing = [s for s in position_skills if s.lower() not in cand_lower]

        if position_skills:
            score = (len(matched) / len(position_skills)) * 100
        else:
            score = 50.0

        return matched, missing, round(score, 2)

    @staticmethod
    def _calculate_experience_match(profile: dict[str, Any], position: Position) -> float:
        """计算经验匹配度 (0-100)。"""
        basic = profile.get("basic_info", {})
        years = basic.get("years_of_experience")

        if years is None:
            return 40.0

        try:
            years = float(years)
        except (ValueError, TypeError):
            return 40.0

        exp_min = position.required_exp_min
        exp_max = position.required_exp_max

        if exp_min is None and exp_max is None:
            return 50.0

        score = 50.0
        if exp_min is not None:
            if years >= exp_min:
                score += 25.0
            else:
                ratio = years / exp_min if exp_min > 0 else 0
                score += ratio * 25.0

        if exp_max is not None:
            if years <= exp_max:
                score += 25.0
            else:
                overshoot = years - exp_max
                score += max(0, 25.0 - overshoot * 5)

        return min(100.0, max(0.0, round(score, 2)))

    @staticmethod
    def _calculate_education_match(profile: dict[str, Any], position: Position) -> float:
        """计算教育匹配度 (0-100)。"""
        education = profile.get("education", [])
        if not education:
            return 40.0
        return 60.0

    # ------------------------------------------------------------------
    # 内部方法 — 辅助构建
    # ------------------------------------------------------------------

    @staticmethod
    def _build_position_dict(position: Position) -> dict[str, Any]:
        """构建岗位信息字典。"""
        return {
            "id": str(position.id),
            "title": position.title,
            "description": position.description,
            "requirements": position.requirements,
            "required_skills": position.required_skills,
            "required_exp_min": position.required_exp_min,
            "required_exp_max": position.required_exp_max,
            "education_requirement": position.education_requirement,
            "location": position.location,
            "employment_type": position.employment_type,
            "salary_min": float(position.salary_min) if position.salary_min else None,
            "salary_max": float(position.salary_max) if position.salary_max else None,
        }

    @staticmethod
    def _build_candidate_dict(candidate: Candidate) -> dict[str, Any]:
        """构建候选人信息字典。"""
        profile = candidate.profile or {}
        return {
            "id": str(candidate.id),
            "profile": profile,
            "status": candidate.status,
            "credibility_score": candidate.credibility_score,
            "inference_data": candidate.inference_data,
        }

    # ------------------------------------------------------------------
    # 内部方法 — 持久化
    # ------------------------------------------------------------------

    async def _persist_match_results(
        self,
        position_id: UUID,
        matches: list[MatchItem],
        tenant_id: str,
        query_type: str,
    ) -> None:
        """批量持久化匹配结果。"""
        for item in matches:
            if not item.candidate_id:
                continue
            await self._persist_single_match(
                position_id=position_id,
                candidate_id=UUID(item.candidate_id),
                score=item.score,
                source_scores=item.source_scores,
                tenant_id=tenant_id,
            )
        await self.db.flush()

    async def _persist_single_match(
        self,
        position_id: UUID,
        candidate_id: UUID,
        score: float,
        source_scores: dict[str, float],
        tenant_id: str,
    ) -> None:
        """持久化单条匹配结果（UPSERT）。"""
        score_breakdown = {
            "rrf_score": source_scores.get("rrf_score"),
            "rerank_score": source_scores.get("rerank_score"),
            "llm_confidence": source_scores.get("llm_confidence"),
        }
        match_details = {
            "source": "m4_intelligent_matching",
            "search_strategy": "embedding+rrf+rerank",
        }

        stmt = pg_insert(Match).values(
            position_id=position_id,
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            status="pending",
            overall_score=score,
            score_breakdown=score_breakdown,
            match_details=match_details,
            initiated_by="system",
        ).on_conflict_do_update(
            index_elements=["position_id", "candidate_id"],
            set_={
                "status": "pending",
                "overall_score": score,
                "score_breakdown": score_breakdown,
                "match_details": match_details,
            },
        )
        await self.db.execute(stmt)
