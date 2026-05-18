"""
MemoryService — 记忆系统核心服务。

提供记忆的 CRUD、语义搜索、关联查询、过期清理、统计等功能。
所有方法均为 async，接收 SQLAlchemy AsyncSession。

核心能力:
  - 记忆 CRUD: 创建/读取/更新/删除
  - 列表查询: 按类型/分类/标签筛选 + 分页
  - 语义搜索: 基于 embedding 余弦相似度
  - 关联查询: 获取记忆的关联记忆
  - 过期清理: 批量软删除过期记忆
  - 统计: 按类型/分类/来源分布统计
  - 访问计数: 自增访问次数
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.models.memory_relation import MemoryRelation
from app.schemas.memory import (
    MemoryCreate,
    MemoryStatsResponse,
    MemoryUpdate,
)

logger = logging.getLogger("hiremind.services.memory_service")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryService:
    """记忆系统核心服务 — 提供记忆的全生命周期管理。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Create ──────────────────────────────────────────────────

    async def create_memory(
        self,
        data: MemoryCreate,
        tenant_id: str,
    ) -> Memory:
        """
        创建新记忆。

        Args:
            data: 创建请求数据。
            tenant_id: 租户 ID。

        Returns:
            创建的 Memory 实例。
        """
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
            embedding=data.embedding,
            is_active=True,
        )
        self.db.add(memory)
        await self.db.flush()

        logger.info(
            "create_memory: id=%s type=%s category=%s tenant=%s",
            memory.id, memory.memory_type, memory.category, tenant_id,
        )
        return memory

    # ── Read ────────────────────────────────────────────────────

    async def get_memory(self, memory_id: UUID) -> Memory | None:
        """
        获取单条记忆。

        Args:
            memory_id: 记忆 UUID。

        Returns:
            Memory 实例或 None。
        """
        stmt = select(Memory).where(Memory.id == memory_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_memories(
        self,
        tenant_id: str,
        *,
        memory_type: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        source: str | None = None,
        is_active: bool | None = True,
        min_confidence: float | None = None,
        min_importance: float | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Memory], int]:
        """
        列表查询记忆（支持多维度筛选 + 分页）。

        Args:
            tenant_id: 租户 ID。
            memory_type: 按类型筛选。
            category: 按分类筛选。
            tags: 按标签筛选（包含任一标签）。
            source: 按来源筛选。
            is_active: 按激活状态筛选。
            min_confidence: 最低置信度。
            min_importance: 最低重要性。
            offset: 分页偏移。
            limit: 每页数量。

        Returns:
            (记忆列表, 总数)
        """
        # Build base conditions
        conditions = [Memory.tenant_id == tenant_id]
        if memory_type is not None:
            conditions.append(Memory.memory_type == memory_type)
        if category is not None:
            conditions.append(Memory.category == category)
        if source is not None:
            conditions.append(Memory.source == source)
        if is_active is not None:
            conditions.append(Memory.is_active == is_active)
        if min_confidence is not None:
            conditions.append(Memory.confidence >= min_confidence)
        if min_importance is not None:
            conditions.append(Memory.importance >= min_importance)

        # Tag filter: JSONB contains any of the given tags
        if tags:
            # Use JSONB overlap operator or simple containment
            conditions.append(Memory.tags.bool_op("?|")(tags))

        where_clause = and_(*conditions)

        # Count
        count_stmt = select(func.count()).select_from(Memory).where(where_clause)
        total = await self.db.scalar(count_stmt) or 0

        # Fetch
        stmt = (
            select(Memory)
            .where(where_clause)
            .order_by(Memory.importance.desc(), Memory.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    # ── Update ──────────────────────────────────────────────────

    async def update_memory(
        self,
        memory_id: UUID,
        data: MemoryUpdate,
    ) -> Memory | None:
        """
        更新记忆。

        Args:
            memory_id: 记忆 UUID。
            data: 更新数据（仅非 None 字段会被更新）。

        Returns:
            更新后的 Memory 实例或 None。
        """
        memory = await self.get_memory(memory_id)
        if memory is None:
            return None

        update_fields = data.model_dump(
            exclude_none=True,
            by_alias=False,
        )
        # Handle metadata_ field (aliased as metadata in schema)
        if "metadata_" in update_fields:
            memory.metadata_ = update_fields.pop("metadata_")

        for field_name, value in update_fields.items():
            if hasattr(memory, field_name):
                setattr(memory, field_name, value)

        await self.db.flush()
        logger.info("update_memory: id=%s fields=%s", memory_id, list(update_fields.keys()))
        return memory

    # ── Delete ──────────────────────────────────────────────────

    async def delete_memory(self, memory_id: UUID) -> bool:
        """
        删除记忆（硬删除）。

        Args:
            memory_id: 记忆 UUID。

        Returns:
            是否成功删除。
        """
        memory = await self.get_memory(memory_id)
        if memory is None:
            return False

        await self.db.delete(memory)
        await self.db.flush()
        logger.info("delete_memory: id=%s", memory_id)
        return True

    # ── Semantic Search ─────────────────────────────────────────

    async def search_memories(
        self,
        query_embedding: list[float],
        tenant_id: str,
        *,
        top_k: int = 10,
        memory_type: str | None = None,
        category: str | None = None,
        min_confidence: float = 0.0,
        min_importance: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        语义搜索记忆（基于 embedding 余弦相似度）。

        当记忆包含 embedding 字段时，计算查询向量与记忆向量的
        余弦相似度，返回 Top-K 结果。

        Args:
            query_embedding: 查询向量。
            tenant_id: 租户 ID。
            top_k: 返回前 K 个。
            memory_type: 按类型筛选。
            category: 按分类筛选。
            min_confidence: 最低置信度。
            min_importance: 最低重要性。

        Returns:
            排序后的记忆列表，每项包含 memory + similarity。
        """
        # Build conditions
        conditions = [
            Memory.tenant_id == tenant_id,
            Memory.is_active == True,  # noqa: E712
            Memory.embedding.isnot(None),
        ]
        if memory_type:
            conditions.append(Memory.memory_type == memory_type)
        if category:
            conditions.append(Memory.category == category)
        if min_confidence > 0:
            conditions.append(Memory.confidence >= min_confidence)
        if min_importance > 0:
            conditions.append(Memory.importance >= min_importance)

        stmt = select(Memory).where(and_(*conditions))
        result = await self.db.execute(stmt)
        memories = list(result.scalars().all())

        # Compute cosine similarity
        scored: list[dict[str, Any]] = []
        for mem in memories:
            emb = mem.embedding
            if not emb or not isinstance(emb, list):
                continue
            sim = _cosine_similarity(query_embedding, emb)
            scored.append({
                "memory": mem,
                "similarity": sim,
            })

        # Sort by similarity descending
        scored.sort(key=lambda x: x["similarity"], reverse=True)

        return scored[:top_k]

    # ── Related Memories ────────────────────────────────────────

    async def get_related_memories(
        self,
        memory_id: UUID,
        tenant_id: str,
        *,
        relation_type: str | None = None,
        limit: int = 20,
    ) -> list[MemoryRelation]:
        """
        获取关联记忆。

        查询以指定记忆为源或目标的关联关系。

        Args:
            memory_id: 记忆 UUID。
            tenant_id: 租户 ID。
            relation_type: 按关系类型筛选。
            limit: 最大返回数。

        Returns:
            关联关系列表。
        """
        conditions = [
            MemoryRelation.tenant_id == tenant_id,
            (MemoryRelation.source_memory_id == memory_id)
            | (MemoryRelation.target_memory_id == memory_id),
        ]
        if relation_type:
            conditions.append(MemoryRelation.relation_type == relation_type)

        stmt = (
            select(MemoryRelation)
            .where(and_(*conditions))
            .order_by(MemoryRelation.strength.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── Expire Memories ─────────────────────────────────────────

    async def expire_memories(self, tenant_id: str) -> int:
        """
        过期清理 — 将过期记忆标记为非活跃。

        Args:
            tenant_id: 租户 ID。

        Returns:
            清理的记忆数量。
        """
        now = _now()
        stmt = (
            update(Memory)
            .where(
                Memory.tenant_id == tenant_id,
                Memory.is_active == True,  # noqa: E712
                Memory.expires_at.isnot(None),
                Memory.expires_at < now,
            )
            .values(is_active=False)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()

        expired_count = result.rowcount  # type: ignore[union-attr]
        if expired_count > 0:
            logger.info("expire_memories: tenant=%s expired=%d", tenant_id, expired_count)
        return expired_count

    # ── Statistics ──────────────────────────────────────────────

    async def get_memory_stats(self, tenant_id: str) -> MemoryStatsResponse:
        """
        获取记忆统计（按类型/分类/来源分布）。

        Args:
            tenant_id: 租户 ID。

        Returns:
            统计结果。
        """
        # Total & active
        total_result = await self.db.scalar(
            select(func.count()).select_from(Memory).where(
                Memory.tenant_id == tenant_id,
            )
        )
        active_result = await self.db.scalar(
            select(func.count()).select_from(Memory).where(
                Memory.tenant_id == tenant_id,
                Memory.is_active == True,  # noqa: E712
            )
        )

        # By type
        type_rows = (await self.db.execute(
            select(Memory.memory_type, func.count().label("count")).where(
                Memory.tenant_id == tenant_id,
                Memory.is_active == True,  # noqa: E712
            ).group_by(Memory.memory_type)
        )).all()
        by_type = {row.memory_type: row.count for row in type_rows}

        # By category
        category_rows = (await self.db.execute(
            select(Memory.category, func.count().label("count")).where(
                Memory.tenant_id == tenant_id,
                Memory.is_active == True,  # noqa: E712
            ).group_by(Memory.category)
        )).all()
        by_category = {row.category: row.count for row in category_rows}

        # By source
        source_rows = (await self.db.execute(
            select(Memory.source, func.count().label("count")).where(
                Memory.tenant_id == tenant_id,
                Memory.is_active == True,  # noqa: E712
            ).group_by(Memory.source)
        )).all()
        by_source = {row.source: row.count for row in source_rows}

        # Average confidence & importance
        avg_result = (await self.db.execute(
            select(
                func.avg(Memory.confidence).label("avg_conf"),
                func.avg(Memory.importance).label("avg_imp"),
            ).where(
                Memory.tenant_id == tenant_id,
                Memory.is_active == True,  # noqa: E712
            )
        )).one()

        return MemoryStatsResponse(
            total=total_result or 0,
            active=active_result or 0,
            by_type=by_type,
            by_category=by_category,
            by_source=by_source,
            avg_confidence=round(float(avg_result.avg_conf or 0.0), 3),
            avg_importance=round(float(avg_result.avg_imp or 0.0), 3),
        )

    # ── Increment Access ────────────────────────────────────────

    async def increment_access(self, memory_id: UUID) -> None:
        """
        访问计数 +1 并更新 last_accessed_at。

        Args:
            memory_id: 记忆 UUID。
        """
        stmt = (
            update(Memory)
            .where(Memory.id == memory_id)
            .values(
                access_count=Memory.access_count + 1,
                last_accessed_at=_now(),
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()


# ── Utility Functions ──────────────────────────────────────────────

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度。"""
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
