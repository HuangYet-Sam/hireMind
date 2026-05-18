"""
RRF (Reciprocal Rank Fusion) 混合检索引擎 (M4)。

结合关键词检索（PostgreSQL tsvector）和向量检索（pgvector），
通过 RRF 融合算法合并两种检索结果，实现语义+关键词双路召回。

核心能力:
  - 关键词检索: 基于 PostgreSQL tsvector 全文搜索
  - 向量检索: 基于 pgvector 的 L2/余弦距离近邻搜索
  - RRF 融合: Reciprocal Rank Fusion 算法合并多路排序
  - 权重调节: 支持自定义关键词/向量权重
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("hiremind.rrf_search")

# ---------------------------------------------------------------------------
# 常量 & 数据结构
# ---------------------------------------------------------------------------

# RRF 默认常数 k（避免除零，同时对高排名结果给予更高权重）
DEFAULT_RRF_K = 60

# 默认权重
DEFAULT_KEYWORD_WEIGHT = 0.4
DEFAULT_VECTOR_WEIGHT = 0.6


class SearchSource(str, Enum):
    """检索来源标识。"""
    KEYWORD = "keyword"
    VECTOR = "vector"
    FUSION = "fusion"


@dataclass
class SearchResult:
    """
    单条检索结果。

    Attributes:
        entity_id: 实体 ID（候选人/岗位 UUID）
        entity_type: 实体类型 ("candidate" | "position")
        score: 相关性得分（归一化到 0-1）
        rank: 在当前检索结果中的排名（1-based）
        source: 检索来源
        metadata: 附加元数据
    """
    entity_id: str
    entity_type: str
    score: float
    rank: int = 0
    source: SearchSource = SearchSource.FUSION
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# RRF 混合检索引擎
# ---------------------------------------------------------------------------

class RRFSearchEngine:
    """
    RRF (Reciprocal Rank Fusion) 混合检索引擎。

    两路检索:
      1. 关键词检索 (keyword_search): PostgreSQL tsvector 全文搜索
      2. 向量检索 (vector_search): pgvector 语义相似度搜索

    融合策略: RRF 公式 score = Σ (1 / (k + rank_i))
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    async def keyword_search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        *,
        top_k: int = 50,
    ) -> list[SearchResult]:
        """
        关键词检索。

        使用 PostgreSQL tsvector 全文搜索，匹配字段:
          - 候选人: profile 中的技能、工作经历描述
          - 岗位: title, description, required_skills

        Args:
            query: 搜索关键词。
            filters: 过滤条件（entity_type, tenant_id, status 等）。
            top_k: 返回的最大结果数。

        Returns:
            按相关性降序排列的检索结果列表。
        """
        if not query or not query.strip():
            logger.warning("keyword_search: 空查询")
            return []

        filters = filters or {}
        entity_type = filters.get("entity_type", "candidate")
        tenant_id = filters.get("tenant_id")

        try:
            results = await self._execute_keyword_search(
                query=query,
                entity_type=entity_type,
                tenant_id=tenant_id,
                top_k=top_k,
            )

            # 设置排名
            for i, result in enumerate(results):
                result.rank = i + 1
                result.source = SearchSource.KEYWORD

            logger.info(
                "keyword_search: query='%s' entity_type=%s results=%d",
                query[:50], entity_type, len(results),
            )
            return results

        except Exception as exc:
            logger.error("keyword_search 失败: %s", exc)
            return []

    async def vector_search(
        self,
        query_embedding: list[float],
        *,
        entity_type: str = "candidate",
        top_k: int = 50,
    ) -> list[SearchResult]:
        """
        向量检索。

        使用 pgvector 进行余弦距离近邻搜索，返回语义最相似的实体。

        Args:
            query_embedding: 查询向量。
            entity_type: 限制搜索的实体类型。
            top_k: 返回的最大结果数。

        Returns:
            按相似度降序排列的检索结果列表。
        """
        if not query_embedding:
            logger.warning("vector_search: 空向量")
            return []

        try:
            vector_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

            # pgvector 余弦距离搜索 (<=> 为余弦距离操作符)
            sql = text("""
                SELECT
                    entity_id,
                    entity_type,
                    1 - (embedding <=> :query_vec::vector) AS cosine_similarity
                FROM entity_embeddings
                WHERE entity_type = :entity_type
                ORDER BY embedding <=> :query_vec::vector
                LIMIT :top_k
            """)
            result = await self.db.execute(
                sql,
                {
                    "query_vec": vector_str,
                    "entity_type": entity_type,
                    "top_k": top_k,
                },
            )
            rows = result.fetchall()

            results: list[SearchResult] = []
            for i, row in enumerate(rows):
                similarity = float(row[2]) if row[2] is not None else 0.0
                # 归一化到 [0, 1]
                normalized_score = max(0.0, min(1.0, (similarity + 1.0) / 2.0))
                results.append(SearchResult(
                    entity_id=str(row[0]),
                    entity_type=str(row[1]),
                    score=normalized_score,
                    rank=i + 1,
                    source=SearchSource.VECTOR,
                    metadata={"raw_similarity": similarity},
                ))

            logger.info(
                "vector_search: entity_type=%s top_k=%d results=%d",
                entity_type, top_k, len(results),
            )
            return results

        except Exception as exc:
            logger.error("vector_search 失败 (pgvector 可能未启用): %s", exc)
            return []

    def rrf_fusion(
        self,
        rankings: list[list[SearchResult]],
        *,
        k: int = DEFAULT_RRF_K,
        weights: list[float] | None = None,
    ) -> list[SearchResult]:
        """
        RRF (Reciprocal Rank Fusion) 融合算法。

        对多路检索结果进行融合，公式:
            score(entity) = Σ weight_i * (1 / (k + rank_i(entity)))

        Args:
            rankings: 多路排序结果列表，每个元素是一个排序列表。
            k: RRF 常数（默认 60），值越大则排名差异的影响越小。
            weights: 各路检索的权重列表（与 rankings 一一对应）。
                     默认为等权重。

        Returns:
            融合后的排序结果，按 RRF 得分降序排列。
        """
        if not rankings:
            return []

        # 设置默认等权重
        if weights is None:
            weights = [1.0 / len(rankings)] * len(rankings)
        elif len(weights) != len(rankings):
            logger.warning(
                "rrf_fusion: weights 数量 (%d) 与 rankings 数量 (%d) 不匹配，使用等权重",
                len(weights), len(rankings),
            )
            weights = [1.0 / len(rankings)] * len(rankings)

        # 归一化权重
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]

        # 收集所有实体 ID
        entity_scores: dict[str, dict[str, Any]] = {}

        for ranking_idx, ranking in enumerate(rankings):
            weight = weights[ranking_idx]
            for result in ranking:
                key = result.entity_id
                if key not in entity_scores:
                    entity_scores[key] = {
                        "entity_id": result.entity_id,
                        "entity_type": result.entity_type,
                        "rrf_score": 0.0,
                        "source_scores": {},
                        "metadata": {},
                    }
                # RRF 得分累加
                rrf_contribution = weight * (1.0 / (k + result.rank))
                entity_scores[key]["rrf_score"] += rrf_contribution
                entity_scores[key]["source_scores"][result.source.value] = result.score
                # 保留每路的 metadata
                entity_scores[key]["metadata"].update(result.metadata)

        # 按 RRF 得分降序排列
        sorted_entities = sorted(
            entity_scores.values(),
            key=lambda e: e["rrf_score"],
            reverse=True,
        )

        # 构造融合结果
        results: list[SearchResult] = []
        for i, entity_data in enumerate(sorted_entities):
            results.append(SearchResult(
                entity_id=entity_data["entity_id"],
                entity_type=entity_data["entity_type"],
                score=entity_data["rrf_score"],
                rank=i + 1,
                source=SearchSource.FUSION,
                metadata={
                    "source_scores": entity_data["source_scores"],
                    "rrf_k": k,
                    "weights": weights,
                    **entity_data["metadata"],
                },
            ))

        logger.info(
            "rrf_fusion: rankings=%d k=%d merged=%d",
            len(rankings), k, len(results),
        )
        return results

    async def hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        filters: dict[str, Any] | None = None,
        *,
        top_k: int = 20,
        keyword_weight: float = DEFAULT_KEYWORD_WEIGHT,
        vector_weight: float = DEFAULT_VECTOR_WEIGHT,
        rrf_k: int = DEFAULT_RRF_K,
    ) -> list[SearchResult]:
        """
        混合检索入口。

        并行执行关键词检索和向量检索，然后通过 RRF 融合合并结果。

        Args:
            query: 搜索关键词文本。
            query_embedding: 查询的向量表示。
            filters: 过滤条件。
            top_k: 最终返回的最大结果数。
            keyword_weight: 关键词检索权重（默认 0.4）。
            vector_weight: 向量检索权重（默认 0.6）。
            rrf_k: RRF 融合常数。

        Returns:
            融合后的排序结果，截取 top_k 条。
        """
        filters = filters or {}

        import asyncio

        # 并行执行两路检索
        keyword_task = self.keyword_search(query, filters, top_k=top_k * 2)
        vector_task = self.vector_search(
            query_embedding,
            entity_type=filters.get("entity_type", "candidate"),
            top_k=top_k * 2,
        )
        keyword_results, vector_results = await asyncio.gather(
            keyword_task, vector_task,
        )

        logger.info(
            "hybrid_search: keyword=%d vector=%d weights=(%.1f, %.1f)",
            len(keyword_results), len(vector_results),
            keyword_weight, vector_weight,
        )

        # RRF 融合
        rankings: list[list[SearchResult]] = []
        weights: list[float] = []

        if keyword_results:
            rankings.append(keyword_results)
            weights.append(keyword_weight)

        if vector_results:
            rankings.append(vector_results)
            weights.append(vector_weight)

        if not rankings:
            return []

        # 归一化权重（确保两路都有时总和为 1）
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]

        fused = self.rrf_fusion(rankings, k=rrf_k, weights=weights)

        # 截取 top_k
        return fused[:top_k]

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    async def _execute_keyword_search(
        self,
        query: str,
        entity_type: str,
        tenant_id: str | None,
        top_k: int,
    ) -> list[SearchResult]:
        """
        执行关键词检索的具体 SQL。

        根据 entity_type 选择不同的表和搜索字段。
        """
        # 构建搜索向量（tsquery）
        # 简单实现：将空格替换为 &（AND）操作符
        ts_query = " & ".join(
            word.strip()
            for word in query.split()
            if word.strip()
        )

        results: list[SearchResult] = []

        if entity_type == "candidate":
            sql = text("""
                SELECT
                    c.id,
                    ts_rank_cd(
                        to_tsvector('simple',
                            COALESCE(c.profile::text, '') || ' ' ||
                            COALESCE(c.summary, '')
                        ),
                        to_tsquery('simple', :ts_query)
                    ) AS rank_score
                FROM candidates c
                WHERE
                    c.status = 'active'
                    AND (:tenant_id IS NULL OR c.tenant_id = :tenant_id)
                    AND to_tsvector('simple',
                        COALESCE(c.profile::text, '') || ' ' ||
                        COALESCE(c.summary, '')
                    ) @@ to_tsquery('simple', :ts_query)
                ORDER BY rank_score DESC
                LIMIT :top_k
            """)
            rows = await self.db.execute(
                sql,
                {"ts_query": ts_query, "tenant_id": tenant_id, "top_k": top_k},
            )
            for row in rows.fetchall():
                score = float(row[1]) if row[1] is not None else 0.0
                # 归一化 ts_rank_cd 输出（通常在 0-1 范围，但可能超出）
                normalized = min(1.0, score)
                results.append(SearchResult(
                    entity_id=str(row[0]),
                    entity_type="candidate",
                    score=normalized,
                    source=SearchSource.KEYWORD,
                ))

        elif entity_type == "position":
            sql = text("""
                SELECT
                    p.id,
                    ts_rank_cd(
                        to_tsvector('simple',
                            COALESCE(p.title, '') || ' ' ||
                            COALESCE(p.description, '') || ' ' ||
                            COALESCE(p.requirements, '') || ' ' ||
                            COALESCE(p.required_skills::text, '') || ' ' ||
                            COALESCE(p.jd_text, '')
                        ),
                        to_tsquery('simple', :ts_query)
                    ) AS rank_score
                FROM positions p
                WHERE
                    p.status = 'open'
                    AND (:tenant_id IS NULL OR p.tenant_id = :tenant_id)
                    AND to_tsvector('simple',
                        COALESCE(p.title, '') || ' ' ||
                        COALESCE(p.description, '') || ' ' ||
                        COALESCE(p.requirements, '') || ' ' ||
                        COALESCE(p.required_skills::text, '') || ' ' ||
                        COALESCE(p.jd_text, '')
                    ) @@ to_tsquery('simple', :ts_query)
                ORDER BY rank_score DESC
                LIMIT :top_k
            """)
            rows = await self.db.execute(
                sql,
                {"ts_query": ts_query, "tenant_id": tenant_id, "top_k": top_k},
            )
            for row in rows.fetchall():
                score = float(row[1]) if row[1] is not None else 0.0
                normalized = min(1.0, score)
                results.append(SearchResult(
                    entity_id=str(row[0]),
                    entity_type="position",
                    score=normalized,
                    source=SearchSource.KEYWORD,
                ))

        return results
