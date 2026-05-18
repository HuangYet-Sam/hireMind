"""
Rerank 层 + 匹配解释生成 (M4)。

对初筛结果进行基于 LLM 的精排（rerank），并为每个匹配生成自然语言解释。
精排层位于检索层（RRF）之上，利用 LLM 的语义理解能力对候选列表重新排序。

核心能力:
  - LLM 精排: 通过精心设计的 Prompt 让 LLM 对候选进行打分和排序
  - 匹配解释生成: 为每个匹配结果生成可读的优劣势分析
  - 批量精排: 支持一次性对多个候选进行精排
  - 置信度评估: 对每次精排结果给出模型置信度
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("hiremind.rerank_engine")

# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------

@dataclass
class MatchExplanation:
    """
    匹配解释。

    Attributes:
        candidate_id: 候选人 ID
        overall_score: 综合评分 (0-100)
        strengths: 匹配优势列表
        concerns: 关注点/风险列表
        recommendation: 推荐建议 (strongly_recommend / recommend / neutral / not_recommend)
        confidence: 模型置信度 (0-1)
    """
    candidate_id: str
    overall_score: float
    strengths: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)
    recommendation: str = "neutral"
    confidence: float = 0.5


@dataclass
class RankedCandidate:
    """
    精排后的候选人。

    Attributes:
        candidate_id: 候选人 ID
        original_score: 初筛得分（RRF 融合分）
        reranked_score: 精排得分 (0-100)
        rank: 精排后排名 (1-based)
        explanation: 匹配解释
    """
    candidate_id: str
    original_score: float
    reranked_score: float
    rank: int = 0
    explanation: MatchExplanation | None = None


# ---------------------------------------------------------------------------
# Prompt 模板
# ---------------------------------------------------------------------------

RERANK_SYSTEM_PROMPT = """你是一名资深猎头和人才评估专家。你的任务是对候选人与岗位的匹配度进行精确评估。

你需要：
1. 对每个候选人给出 0-100 的匹配度评分
2. 列出匹配优势（strengths）
3. 列出关注点和风险（concerns）
4. 给出推荐等级：strongly_recommend / recommend / neutral / not_recommend
5. 给出评估置信度 (0-1)

评估维度：
- 技能匹配度 (40%): 候选人技能与岗位要求的匹配程度
- 经验相关性 (25%): 工作经历与岗位的相关性
- 教育背景 (10%): 教育水平与岗位要求的匹配
- 发展潜力 (15%): 候选人的成长空间和学习能力
- 综合适配度 (10%): 文化契合、薪资期望等软性因素

返回严格的 JSON 格式，不要包含任何其他文本。"""

RERANK_USER_PROMPT_TEMPLATE = """请评估以下 {count} 位候选人与岗位的匹配度。

## 岗位信息
{position_info}

## 候选人列表
{candidates_info}

请返回以下 JSON 格式:
{{
  "rankings": [
    {{
      "candidate_id": "候选人ID",
      "overall_score": 85,
      "strengths": ["优势1", "优势2", "优势3"],
      "concerns": ["关注点1", "关注点2"],
      "recommendation": "recommend",
      "confidence": 0.85
    }}
  ]
}}

要求:
1. 每个候选人的 strengths 至少 1 条，最多 5 条
2. 每个候选人的 concerns 至少 1 条，最多 5 条
3. overall_score 范围 0-100，整数
4. confidence 范围 0-1，保留两位小数
5. 按 overall_score 从高到低排列
6. 返回纯 JSON，不要 markdown 代码块"""

EXPLANATION_SYSTEM_PROMPT = """你是一名资深猎头，擅长撰写候选人匹配分析报告。

你需要生成一份简洁、专业的匹配分析，包含：
1. 整体匹配评价
2. 匹配优势分析
3. 风险和关注点
4. 推荐建议

返回严格的 JSON 格式。"""

EXPLANATION_USER_PROMPT_TEMPLATE = """请为以下候选人-岗位匹配生成详细分析报告。

## 岗位信息
{position_info}

## 候选人信息
{candidate_info}

## 初筛评分
{initial_score}

请返回以下 JSON 格式:
{{
  "overall_score": 82,
  "strengths": [
    "优势1：详细说明",
    "优势2：详细说明"
  ],
  "concerns": [
    "关注点1：详细说明",
    "关注点2：详细说明"
  ],
  "recommendation": "recommend",
  "confidence": 0.85,
  "detailed_analysis": "一段完整的匹配分析文字（200字以内）"
}}"""


# ---------------------------------------------------------------------------
# Rerank 引擎
# ---------------------------------------------------------------------------

class RerankEngine:
    """
    Rerank 层 + 匹配解释生成。

    利用 LLM 对初筛结果进行精排:
      1. 将岗位信息和候选人列表发给 LLM
      2. LLM 对每个候选人进行多维度评分
      3. 解析 LLM 响应，生成 RankedCandidate 和 MatchExplanation
      4. 若 LLM 不可用，降级为基于初筛得分的简单排序
    """

    def __init__(self) -> None:
        # RerankEngine 不直接依赖 DB，只需要 AI Client
        pass

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    async def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        *,
        top_k: int = 10,
    ) -> list[RankedCandidate]:
        """
        基于 LLM 的精排。

        将岗位描述（query）和候选人列表发送给 LLM，
        由 LLM 进行多维度评估并排序。

        Args:
            query: 岗位描述或搜索查询文本。
            candidates: 候选人列表，每个字典应包含:
                        - candidate_id: 候选人 ID
                        - score: 初筛得分
                        - profile: 候选人画像（可选）
            top_k: 返回的最大结果数。

        Returns:
            精排后的候选人列表，按 reranked_score 降序排列。
        """
        if not candidates:
            return []

        # 截取 top_k * 2 的候选（给 LLM 更多选择空间）
        candidates_to_rank = candidates[:top_k * 2]

        try:
            # 尝试 LLM 精排
            ranked = await self._llm_rerank(query, candidates_to_rank)
            if ranked:
                # 设置最终排名
                for i, item in enumerate(ranked[:top_k]):
                    item.rank = i + 1
                return ranked[:top_k]
        except Exception as exc:
            logger.warning("LLM 精排失败，降级为简单排序: %s", exc)

        # 降级：基于初筛得分的简单排序
        return self._fallback_rerank(candidates_to_rank, top_k)

    async def generate_match_explanation(
        self,
        query: dict[str, Any],
        candidate: dict[str, Any],
    ) -> MatchExplanation:
        """
        生成匹配解释。

        为单个候选人-岗位匹配生成详细的自然语言分析报告。

        Args:
            query: 岗位信息字典（title, description, required_skills 等）。
            candidate: 候选人信息字典（candidate_id, profile, score 等）。

        Returns:
            MatchExplanation 匹配解释对象。
        """
        candidate_id = str(candidate.get("candidate_id", "unknown"))

        try:
            explanation = await self._llm_generate_explanation(query, candidate)
            if explanation is not None:
                return explanation
        except Exception as exc:
            logger.warning(
                "generate_match_explanation LLM 失败: candidate=%s error=%s",
                candidate_id, exc,
            )

        # 降级：基于规则的简单解释
        return self._fallback_explanation(candidate_id, query, candidate)

    async def batch_rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
    ) -> list[RankedCandidate]:
        """
        批量精排。

        对全部候选人不做截断，一次性发给 LLM 精排。
        注意：候选人数量过多时可能导致 Token 超限，
        建议先通过 RRF 检索缩减到合理数量（≤50）。

        Args:
            query: 岗位描述或搜索查询文本。
            candidates: 候选人列表。

        Returns:
            精排后的完整候选人列表。
        """
        if not candidates:
            return []

        # 如果候选数量过多，分批处理
        batch_size = 20
        if len(candidates) > batch_size:
            return await self._batch_rerank_chunked(query, candidates, batch_size)

        try:
            ranked = await self._llm_rerank(query, candidates)
            if ranked:
                for i, item in enumerate(ranked):
                    item.rank = i + 1
                return ranked
        except Exception as exc:
            logger.warning("batch_rerank LLM 失败: %s", exc)

        return self._fallback_rerank(candidates, len(candidates))

    # ------------------------------------------------------------------
    # LLM 调用
    # ------------------------------------------------------------------

    async def _llm_rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
    ) -> list[RankedCandidate] | None:
        """
        通过 LLM 执行精排。

        Returns:
            精排结果列表，或 None（LLM 不可用时）。
        """
        from app.services.ai_client import ai_client

        # 构建候选人信息文本
        candidates_info_parts: list[str] = []
        for idx, cand in enumerate(candidates):
            candidate_id = cand.get("candidate_id", f"unknown_{idx}")
            profile = cand.get("profile", {})
            score = cand.get("score", 0)

            # 提取关键信息
            skills = profile.get("skills", []) if isinstance(profile, dict) else []
            work_exp = profile.get("work_experience", []) if isinstance(profile, dict) else []
            education = profile.get("education", []) if isinstance(profile, dict) else []
            basic = profile.get("basic_info", {}) if isinstance(profile, dict) else {}

            cand_text = f"""### 候选人 {idx + 1} (ID: {candidate_id})
- 初筛得分: {score}
- 当前职位: {basic.get('current_title', '未知')} @ {basic.get('current_company', '未知')}
- 工作年限: {basic.get('years_of_experience', '未知')}
- 技能: {json.dumps(skills, ensure_ascii=False) if skills else '未知'}
- 工作经历: {json.dumps(work_exp[:3], ensure_ascii=False) if work_exp else '未知'}
- 教育背景: {json.dumps(education[:2], ensure_ascii=False) if education else '未知'}"""
            candidates_info_parts.append(cand_text)

        candidates_info = "\n\n".join(candidates_info_parts)

        user_prompt = RERANK_USER_PROMPT_TEMPLATE.format(
            count=len(candidates),
            position_info=query,
            candidates_info=candidates_info,
        )

        messages = [
            {"role": "system", "content": RERANK_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        response = await ai_client.chat_completion(
            messages,
            response_format={"type": "json_object"},
            max_tokens=4096,
            temperature=0.1,
        )

        if not response:
            return None

        return self._parse_rerank_response(response, candidates)

    async def _llm_generate_explanation(
        self,
        query: dict[str, Any],
        candidate: dict[str, Any],
    ) -> MatchExplanation | None:
        """通过 LLM 生成匹配解释。"""
        from app.services.ai_client import ai_client

        candidate_id = str(candidate.get("candidate_id", "unknown"))
        initial_score = candidate.get("score", 0)
        profile = candidate.get("profile", {})

        user_prompt = EXPLANATION_USER_PROMPT_TEMPLATE.format(
            position_info=json.dumps(query, ensure_ascii=False, indent=2),
            candidate_info=json.dumps(
                {"candidate_id": candidate_id, "profile": profile},
                ensure_ascii=False, indent=2,
            ),
            initial_score=initial_score,
        )

        messages = [
            {"role": "system", "content": EXPLANATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        response = await ai_client.chat_completion(
            messages,
            response_format={"type": "json_object"},
            max_tokens=1024,
            temperature=0.1,
        )

        if not response:
            return None

        content = response
        if isinstance(content, dict):
            data = content
        else:
            try:
                data = json.loads(str(content))
            except (json.JSONDecodeError, TypeError):
                return None

        return MatchExplanation(
            candidate_id=candidate_id,
            overall_score=float(data.get("overall_score", 0)),
            strengths=data.get("strengths", []),
            concerns=data.get("concerns", []),
            recommendation=data.get("recommendation", "neutral"),
            confidence=float(data.get("confidence", 0.5)),
        )

    # ------------------------------------------------------------------
    # 响应解析
    # ------------------------------------------------------------------

    def _parse_rerank_response(
        self,
        response: dict[str, Any],
        original_candidates: list[dict[str, Any]],
    ) -> list[RankedCandidate]:
        """
        解析 LLM 精排响应。

        Args:
            response: LLM 返回的 JSON 响应。
            original_candidates: 原始候选人列表（用于获取 original_score）。

        Returns:
            RankedCandidate 列表。
        """
        content = response
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                logger.warning("_parse_rerank_response: 响应非有效 JSON")
                return []

        # 响应可能是 {"content": "{...}"} 格式
        if "content" in content and isinstance(content["content"], str):
            try:
                content = json.loads(content["content"])
            except (json.JSONDecodeError, TypeError):
                pass

        rankings = content.get("rankings", [])
        if not rankings:
            logger.warning("_parse_rerank_response: 响应中无 rankings")
            return []

        # 构建原始得分的查找表
        original_scores: dict[str, float] = {}
        for cand in original_candidates:
            cid = str(cand.get("candidate_id", ""))
            original_scores[cid] = float(cand.get("score", 0))

        results: list[RankedCandidate] = []
        for item in rankings:
            candidate_id = str(item.get("candidate_id", ""))
            if not candidate_id:
                continue

            overall_score = float(item.get("overall_score", 0))
            confidence = float(item.get("confidence", 0.5))
            # 限制范围
            overall_score = max(0.0, min(100.0, overall_score))
            confidence = max(0.0, min(1.0, confidence))

            explanation = MatchExplanation(
                candidate_id=candidate_id,
                overall_score=overall_score,
                strengths=item.get("strengths", []),
                concerns=item.get("concerns", []),
                recommendation=item.get("recommendation", "neutral"),
                confidence=confidence,
            )

            results.append(RankedCandidate(
                candidate_id=candidate_id,
                original_score=original_scores.get(candidate_id, 0.0),
                reranked_score=overall_score,
                rank=0,  # 后续设置
                explanation=explanation,
            ))

        # 按 reranked_score 降序排列
        results.sort(key=lambda r: r.reranked_score, reverse=True)
        return results

    # ------------------------------------------------------------------
    # 降级方案
    # ------------------------------------------------------------------

    def _fallback_rerank(
        self,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> list[RankedCandidate]:
        """
        降级精排：基于初筛得分的简单排序。

        当 LLM 不可用时使用，直接按初筛得分排序。
        """
        sorted_candidates = sorted(
            candidates,
            key=lambda c: float(c.get("score", 0)),
            reverse=True,
        )

        results: list[RankedCandidate] = []
        for i, cand in enumerate(sorted_candidates[:top_k]):
            candidate_id = str(cand.get("candidate_id", ""))
            original_score = float(cand.get("score", 0))
            # 将 0-1 的初筛分映射到 0-100
            reranked_score = original_score * 100 if original_score <= 1.0 else original_score

            explanation = MatchExplanation(
                candidate_id=candidate_id,
                overall_score=reranked_score,
                strengths=["基于初筛得分的自动排序"],
                concerns=["LLM 不可用，未进行深度评估"],
                recommendation="neutral",
                confidence=0.3,
            )

            results.append(RankedCandidate(
                candidate_id=candidate_id,
                original_score=original_score,
                reranked_score=reranked_score,
                rank=i + 1,
                explanation=explanation,
            ))

        logger.info("_fallback_rerank: candidates=%d top_k=%d", len(candidates), top_k)
        return results

    def _fallback_explanation(
        self,
        candidate_id: str,
        query: dict[str, Any],
        candidate: dict[str, Any],
    ) -> MatchExplanation:
        """降级匹配解释：基于规则生成简单解释。"""
        score = float(candidate.get("score", 0))
        # 将 0-1 映射到 0-100
        overall = score * 100 if score <= 1.0 else score

        strengths: list[str] = []
        concerns: list[str] = []

        # 简单的规则生成
        profile = candidate.get("profile", {})
        if isinstance(profile, dict):
            skills = profile.get("skills", [])
            if skills:
                if isinstance(skills, list):
                    strengths.append(f"具备 {len(skills)} 项相关技能")
                elif isinstance(skills, dict):
                    strengths.append(f"具备 {len(skills)} 项相关技能")

            work_exp = profile.get("work_experience", [])
            if work_exp:
                strengths.append(f"有 {len(work_exp)} 段工作经历")

        if overall >= 70:
            recommendation = "recommend"
        elif overall >= 50:
            recommendation = "neutral"
        else:
            recommendation = "not_recommend"

        if not concerns:
            concerns.append("LLM 不可用，未能进行深度评估")

        return MatchExplanation(
            candidate_id=candidate_id,
            overall_score=overall,
            strengths=strengths,
            concerns=concerns,
            recommendation=recommendation,
            confidence=0.3,
        )

    # ------------------------------------------------------------------
    # 批量处理
    # ------------------------------------------------------------------

    async def _batch_rerank_chunked(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        batch_size: int,
    ) -> list[RankedCandidate]:
        """
        分批精排：将大量候选分成多个批次，分别精排后合并。

        Args:
            query: 岗位描述。
            candidates: 候选人列表。
            batch_size: 每批的大小。

        Returns:
            合并后的精排结果。
        """
        import asyncio

        batches: list[list[dict[str, Any]]] = []
        for i in range(0, len(candidates), batch_size):
            batches.append(candidates[i:i + batch_size])

        logger.info(
            "_batch_rerank_chunked: total=%d batches=%d batch_size=%d",
            len(candidates), len(batches), batch_size,
        )

        tasks = [self._llm_rerank(query, batch) for batch in batches]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        all_ranked: list[RankedCandidate] = []
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                logger.warning("批次精排失败: %s", batch_result)
                continue
            if batch_result:
                all_ranked.extend(batch_result)

        # 全局排序
        all_ranked.sort(key=lambda r: r.reranked_score, reverse=True)

        # 重新设置排名
        for i, item in enumerate(all_ranked):
            item.rank = i + 1

        return all_ranked
