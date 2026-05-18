"""
向量化服务 (M4) — 岗位+候选人 Embedding。

为岗位描述（JD）和候选人画像生成向量表示，用于后续的语义检索和匹配。
底层使用 sentence-transformers / OpenAI Embedding API / Mock 占位实现，
上层接口保持稳定，后续可无缝切换。

核心能力:
  - 文本向量化：单条 / 批量
  - JD 向量化：从 DB 读取岗位描述，组合关键信息后生成向量
  - 候选人画像向量化：聚合技能、经历等多维信息后生成向量
  - 向量存储：持久化到 PostgreSQL（pgvector 扩展）
  - 相似度计算：余弦相似度
"""

from __future__ import annotations

import json
import logging
import math
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.position import Position

logger = logging.getLogger("hiremind.embedding_service")

# ---------------------------------------------------------------------------
# 常量 & 数据结构
# ---------------------------------------------------------------------------

# 默认向量维度（sentence-transformers paraphrase-multilingual-MiniLM-L12-v2）
DEFAULT_EMBEDDING_DIMENSION = 384

# 向量存储表名
EMBEDDING_TABLE_NAME = "entity_embeddings"


@dataclass
class EmbeddingResult:
    """
    向量化结果。

    Attributes:
        entity_type: 实体类型 ("position" | "candidate")
        entity_id: 实体 ID
        vector: 浮点向量
        metadata: 附加元数据（维度、模型、生成时间等）
    """
    entity_type: str
    entity_id: str
    vector: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 向量化服务
# ---------------------------------------------------------------------------

class EmbeddingService:
    """
    向量化服务 — 岗位+候选人 Embedding。

    两层实现:
      1. Mock/Rule 层: 基于 TF-IDF 或哈希的简易向量化（无需 GPU/API）
      2. AI 层: sentence-transformers 或 OpenAI Embedding API

    当前以 Mock 层为主，接口完整，后续可替换底层实现。
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._dimension = DEFAULT_EMBEDDING_DIMENSION

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    async def generate_text_embedding(self, text: str) -> list[float]:
        """
        生成文本向量。

        当前使用 Mock 实现（基于哈希的确定性伪向量），
        后续可替换为 sentence-transformers 或 OpenAI Embedding API。

        Args:
            text: 待向量化的文本。

        Returns:
            浮点向量列表，维度为 DEFAULT_EMBEDDING_DIMENSION。
        """
        if not text or not text.strip():
            logger.warning("generate_text_embedding: 空文本，返回零向量")
            return [0.0] * self._dimension

        try:
            # --- Mock 实现：基于哈希的确定性伪向量 ---
            vector = self._mock_embedding(text)
            logger.debug("generate_text_embedding: text_len=%d dim=%d", len(text), len(vector))
            return vector

            # --- TODO: sentence-transformers 实现 ---
            # from sentence_transformers import SentenceTransformer
            # model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            # return model.encode(text).tolist()

            # --- TODO: OpenAI Embedding API 实现 ---
            # import httpx
            # resp = await httpx.AsyncClient().post(
            #     "https://api.openai.com/v1/embeddings",
            #     json={"model": "text-embedding-3-small", "input": text},
            #     headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            # )
            # return resp.json()["data"][0]["embedding"]

        except Exception as exc:
            logger.error("generate_text_embedding 失败: %s", exc)
            return [0.0] * self._dimension

    async def generate_jd_embedding(self, position_id: int | UUID) -> list[float]:
        """
        岗位描述向量化。

        从 DB 读取岗位信息，组合以下文本后生成向量:
          - 标题
          - 职位描述 (description)
          - 岗位要求 (requirements)
          - 必备技能 (required_skills)
          - JD 原文 (jd_text)

        Args:
            position_id: 岗位 ID（UUID）。

        Returns:
            岗位的向量表示。

        Raises:
            ValueError: 岗位不存在。
        """
        position = await self._load_position(position_id)
        if position is None:
            raise ValueError(f"Position not found: {position_id}")

        # 组合 JD 文本
        parts: list[str] = []
        if position.title:
            parts.append(f"职位: {position.title}")
        if position.description:
            parts.append(f"描述: {position.description}")
        if position.requirements:
            parts.append(f"要求: {position.requirements}")
        if position.required_skills:
            skills_text = json.dumps(
                position.required_skills, ensure_ascii=False
            )
            parts.append(f"必备技能: {skills_text}")
        if position.jd_text:
            parts.append(f"JD原文: {position.jd_text}")

        combined_text = "\n".join(parts)
        if not combined_text.strip():
            logger.warning("generate_jd_embedding: 岗位 %s 无有效文本", position_id)
            return [0.0] * self._dimension

        vector = await self.generate_text_embedding(combined_text)

        # 自动存储
        await self.store_embedding(
            entity_type="position",
            entity_id=str(position_id),
            embedding=vector,
        )

        logger.info(
            "generate_jd_embedding: position=%s text_len=%d dim=%d",
            position_id, len(combined_text), len(vector),
        )
        return vector

    async def generate_candidate_embedding(self, candidate_id: int | UUID) -> list[float]:
        """
        候选人画像向量化。

        从 DB 读取候选人信息，聚合以下维度后生成向量:
          - 基本信息摘要
          - 技能列表
          - 工作经历摘要
          - 教育背景
          - 推断技能（inference_data）

        Args:
            candidate_id: 候选人 ID（UUID）。

        Returns:
            候选人的向量表示。

        Raises:
            ValueError: 候选人不存在。
        """
        candidate = await self._load_candidate(candidate_id)
        if candidate is None:
            raise ValueError(f"Candidate not found: {candidate_id}")

        profile = candidate.profile or {}
        parts: list[str] = []

        # 基本信息摘要
        basic_info = profile.get("basic_info", {})
        if isinstance(basic_info, dict):
            name = basic_info.get("name", "")
            title = basic_info.get("current_title", "")
            if name:
                parts.append(f"姓名: {name}")
            if title:
                parts.append(f"当前职位: {title}")

        # 技能列表
        skills = profile.get("skills", [])
        if skills:
            if isinstance(skills, dict):
                skills = list(skills.keys())
            skill_names = [
                s.get("name", s) if isinstance(s, dict) else str(s)
                for s in skills
            ]
            parts.append(f"技能: {', '.join(skill_names)}")

        # 工作经历摘要
        work_experience: list[dict[str, Any]] = profile.get("work_experience") or []
        for exp in work_experience[:5]:  # 最多取 5 段
            company = exp.get("company", "")
            title = exp.get("title") or exp.get("position", "")
            desc = exp.get("description", "")
            parts.append(f"工作: {company} {title} {desc}")

        # 教育背景
        education: list[dict[str, Any]] = profile.get("education") or []
        for edu in education[:3]:
            school = edu.get("school", "")
            degree = edu.get("degree", "")
            major = edu.get("major", "")
            parts.append(f"教育: {school} {degree} {major}")

        # 推断技能
        inference_data = candidate.inference_data or {}
        inferred_skills = inference_data.get("inferred_skills") or []
        if inferred_skills:
            inferred_names = [s.get("name", "") for s in inferred_skills if s.get("name")]
            if inferred_names:
                parts.append(f"推断技能: {', '.join(inferred_names)}")

        combined_text = "\n".join(parts)
        if not combined_text.strip():
            logger.warning("generate_candidate_embedding: 候选人 %s 无有效文本", candidate_id)
            return [0.0] * self._dimension

        vector = await self.generate_text_embedding(combined_text)

        # 自动存储
        await self.store_embedding(
            entity_type="candidate",
            entity_id=str(candidate_id),
            embedding=vector,
        )

        logger.info(
            "generate_candidate_embedding: candidate=%s text_len=%d dim=%d",
            candidate_id, len(combined_text), len(vector),
        )
        return vector

    async def batch_generate_embeddings(self, items: list[str]) -> list[list[float]]:
        """
        批量向量化。

        对多条文本并行生成向量，提升吞吐量。

        Args:
            items: 待向量化的文本列表。

        Returns:
            向量列表，顺序与输入一致。
        """
        if not items:
            return []

        import asyncio

        tasks = [self.generate_text_embedding(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        vectors: list[list[float]] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    "batch_generate_embeddings: 第 %d 条失败: %s", i, result
                )
                vectors.append([0.0] * self._dimension)
            else:
                vectors.append(result)

        logger.info(
            "batch_generate_embeddings: items=%d success=%d",
            len(items),
            sum(1 for v in vectors if any(x != 0.0 for x in v)),
        )
        return vectors

    async def store_embedding(
        self,
        entity_type: str,
        entity_id: str,
        embedding: list[float],
    ) -> None:
        """
        存储向量到 DB。

        使用 UPSERT 语义：如果 (entity_type, entity_id) 已存在则更新。

        Args:
            entity_type: 实体类型 ("position" | "candidate")。
            entity_id: 实体 ID。
            embedding: 浮点向量。
        """
        if not embedding:
            logger.warning("store_embedding: 空向量，跳过存储")
            return

        # 将向量转换为 PostgreSQL 向量格式字符串
        vector_str = "[" + ",".join(str(v) for v in embedding) + "]"

        try:
            upsert_sql = text(f"""
                INSERT INTO {EMBEDDING_TABLE_NAME}
                    (entity_type, entity_id, embedding, dimension, model_name, updated_at)
                VALUES
                    (:entity_type, :entity_id, :embedding::vector, :dimension, :model_name, NOW())
                ON CONFLICT (entity_type, entity_id)
                DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    dimension = EXCLUDED.dimension,
                    model_name = EXCLUDED.model_name,
                    updated_at = NOW()
            """)
            await self.db.execute(
                upsert_sql,
                {
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "embedding": vector_str,
                    "dimension": len(embedding),
                    "model_name": "mock-v1",
                },
            )
            await self.db.flush()

            logger.debug(
                "store_embedding: %s/%s dim=%d", entity_type, entity_id, len(embedding),
            )
        except Exception as exc:
            # 表可能尚未创建（pgvector 扩展未启用），降级为日志
            logger.warning(
                "store_embedding 失败 (表 %s 可能不存在): %s",
                EMBEDDING_TABLE_NAME, exc,
            )

    async def get_similarity(
        self,
        embedding_a: list[float],
        embedding_b: list[float],
    ) -> float:
        """
        计算两个向量的余弦相似度。

        公式: cos(A, B) = (A · B) / (||A|| * ||B||)

        Args:
            embedding_a: 向量 A。
            embedding_b: 向量 B。

        Returns:
            余弦相似度，范围 [-1, 1]。若任一向量为零向量则返回 0.0。
        """
        if not embedding_a or not embedding_b:
            return 0.0
        if len(embedding_a) != len(embedding_b):
            logger.warning(
                "get_similarity: 向量维度不匹配 (%d vs %d)",
                len(embedding_a), len(embedding_b),
            )
            return 0.0

        # 点积
        dot_product = sum(a * b for a, b in zip(embedding_a, embedding_b))
        # 模长
        norm_a = math.sqrt(sum(a * a for a in embedding_a))
        norm_b = math.sqrt(sum(b * b for b in embedding_b))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        similarity = dot_product / (norm_a * norm_b)
        return round(similarity, 6)

    async def get_stored_embedding(
        self,
        entity_type: str,
        entity_id: str,
    ) -> list[float] | None:
        """
        从 DB 获取已存储的向量。

        Args:
            entity_type: 实体类型。
            entity_id: 实体 ID。

        Returns:
            向量列表，若不存在返回 None。
        """
        try:
            stmt = text(f"""
                SELECT embedding FROM {EMBEDDING_TABLE_NAME}
                WHERE entity_type = :entity_type AND entity_id = :entity_id
            """)
            result = await self.db.execute(
                stmt,
                {"entity_type": entity_type, "entity_id": entity_id},
            )
            row = result.fetchone()
            if row is None:
                return None
            # pgvector 返回的格式通常是字符串 "[0.1,0.2,...]"
            raw = row[0]
            if isinstance(raw, str):
                return [float(x) for x in raw.strip("[]").split(",")]
            if isinstance(raw, list):
                return raw
            return None
        except Exception as exc:
            logger.warning("get_stored_embedding 失败: %s", exc)
            return None

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _mock_embedding(self, text: str) -> list[float]:
        """
        Mock 向量化：基于哈希的确定性伪向量。

        使用多轮哈希生成固定维度的向量，保证相同文本产生相同向量。
        通过归一化使向量模拟单位向量的特性。

        Args:
            text: 输入文本。

        Returns:
            伪随机但确定性的浮点向量。
        """
        dimension = self._dimension
        vector = [0.0] * dimension

        # 使用文本的多个 N-gram 生成哈希来填充向量
        text_lower = text.lower()
        for i in range(dimension):
            # 组合文本和索引生成不同的哈希种子
            seed = f"{text_lower}|chunk{i}|dim{dimension}"
            hash_val = hashlib.sha256(seed.encode()).hexdigest()
            # 取前 8 个十六进制字符转为浮点数
            int_val = int(hash_val[:8], 16)
            vector[i] = (int_val / 0xFFFFFFFF) - 0.5  # 范围约 [-0.5, 0.5]

        # 归一化为单位向量
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

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
