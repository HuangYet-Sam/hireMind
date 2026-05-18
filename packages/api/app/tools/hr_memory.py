"""
HR Memory Agent Tool.

Exposes memory management capabilities as Agent Tools
via the ``@AiCapability`` decorator.

Registered capabilities:
  - ``hr_memory_create``      — Create a memory record
  - ``hr_memory_search``      — Semantic search memories
  - ``hr_memory_update``      — Update a memory record
  - ``hr_memory_delete``      — Delete a memory record
  - ``hr_memory_stats``       — Get memory statistics
"""

from __future__ import annotations

import logging
from typing import Any

from app.decorators.ai_capability import AiCapability

logger = logging.getLogger("hiremind.tools.hr_memory")


# ---------------------------------------------------------------------------
# Tool: Create Memory — 创建记忆
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_memory_create",
    name="HR Memory Create",
    endpoint="/api/v1/memories/",
    method="POST",
    tool_name="hr_memory_create",
    permissions=["memory:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_memory_create_v1",
    description="Create a new memory record (preference/insight/decision/pattern/fact)",
    request_model="MemoryCreate",
    response_model="MemoryResponse",
    rate_limit="60/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "memory", "create"],
    timeout=10.0,
)
async def create_memory(
    *,
    memory_type: str,
    category: str,
    content: str,
    source: str = "system",
    source_id: str | None = None,
    confidence: float = 0.5,
    importance: float = 0.5,
    tags: list[str] | None = None,
    metadata_: dict | None = None,
    tenant_id: str = "default",
) -> dict[str, Any]:
    """
    Create a new memory record.

    Args:
        memory_type: Type of memory (preference/insight/decision/pattern/fact).
        category: Category (recruitment/candidate/interview/offer/market/team).
        content: Memory content text.
        source: Source type (interaction/log/system/ai_inferred).
        source_id: Source entity ID.
        confidence: Confidence score (0-1).
        importance: Importance score (0-1).
        tags: Tags for categorization.
        metadata_: Additional metadata.
        tenant_id: Tenant scope identifier.

    Returns:
        Dict with created memory details.
    """
    from app.dependencies import get_db
    from app.schemas.memory import MemoryCreate
    from app.services.memory_service import MemoryService

    async for session in get_db():
        svc = MemoryService(session)
        create_data = MemoryCreate(
            memory_type=memory_type,
            category=category,
            content=content,
            source=source,
            source_id=source_id,
            confidence=confidence,
            importance=importance,
            tags=tags,
            metadata_=metadata_,
        )
        try:
            memory = await svc.create_memory(
                data=create_data,
                tenant_id=tenant_id,
            )
            return {
                "status": "success",
                "memory_id": str(memory.id),
                "memory_type": memory.memory_type,
                "category": memory.category,
                "content": memory.content[:100],
                "confidence": memory.confidence,
                "importance": memory.importance,
            }
        except Exception as exc:
            return {"error": str(exc)}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: Search Memories — 语义搜索记忆
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_memory_search",
    name="HR Memory Search",
    endpoint="/api/v1/memories/search",
    method="POST",
    tool_name="hr_memory_search",
    permissions=["memory:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_memory_search_v1",
    description="Semantic search memories by query text or embedding",
    request_model="MemorySearchRequest",
    response_model="list[MemoryResponse]",
    rate_limit="60/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "memory", "search"],
    timeout=15.0,
)
async def search_memories(
    *,
    query: str,
    tenant_id: str = "default",
    memory_type: str | None = None,
    category: str | None = None,
    top_k: int = 10,
    min_confidence: float = 0.0,
) -> dict[str, Any]:
    """
    Semantic search memories.

    When embeddings are available, performs cosine similarity search.
    Falls back to keyword matching otherwise.

    Args:
        query: Search query text.
        tenant_id: Tenant scope identifier.
        memory_type: Optional filter by memory type.
        category: Optional filter by category.
        top_k: Number of results to return.
        min_confidence: Minimum confidence threshold.

    Returns:
        Dict with search results.
    """
    from app.dependencies import get_db
    from app.services.memory_service import MemoryService

    async for session in get_db():
        svc = MemoryService(session)

        # Generate simple query embedding (mock: hash-based)
        query_embedding = _simple_embedding(query)

        try:
            results = await svc.search_memories(
                query_embedding=query_embedding,
                tenant_id=tenant_id,
                top_k=top_k,
                memory_type=memory_type,
                category=category,
                min_confidence=min_confidence,
            )
            return {
                "status": "success",
                "query": query,
                "total": len(results),
                "results": [
                    {
                        "memory_id": str(r["memory"].id),
                        "content": r["memory"].content[:200],
                        "memory_type": r["memory"].memory_type,
                        "category": r["memory"].category,
                        "similarity": round(r["similarity"], 3),
                        "confidence": r["memory"].confidence,
                    }
                    for r in results
                ],
            }
        except Exception as exc:
            return {"error": str(exc)}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: Update Memory — 更新记忆
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_memory_update",
    name="HR Memory Update",
    endpoint="/api/v1/memories/{memory_id}",
    method="PUT",
    tool_name="hr_memory_update",
    permissions=["memory:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_memory_update_v1",
    description="Update an existing memory record",
    request_model="MemoryUpdate",
    response_model="MemoryResponse",
    rate_limit="30/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "memory", "update"],
    timeout=10.0,
)
async def update_memory(
    memory_id: str,
    *,
    content: str | None = None,
    confidence: float | None = None,
    importance: float | None = None,
    tags: list[str] | None = None,
    is_active: bool | None = None,
) -> dict[str, Any]:
    """
    Update an existing memory record.

    Args:
        memory_id: UUID of the memory to update.
        content: New content (optional).
        confidence: New confidence score (optional).
        importance: New importance score (optional).
        tags: New tags (optional).
        is_active: New active status (optional).

    Returns:
        Dict with updated memory details.
    """
    from uuid import UUID

    from app.dependencies import get_db
    from app.schemas.memory import MemoryUpdate
    from app.services.memory_service import MemoryService

    async for session in get_db():
        svc = MemoryService(session)
        update_data = MemoryUpdate(
            content=content,
            confidence=confidence,
            importance=importance,
            tags=tags,
            is_active=is_active,
        )
        try:
            memory = await svc.update_memory(
                memory_id=UUID(memory_id),
                data=update_data,
            )
            if memory is None:
                return {"error": "Memory not found", "memory_id": memory_id}
            return {
                "status": "success",
                "memory_id": str(memory.id),
                "content": memory.content[:100],
                "confidence": memory.confidence,
                "importance": memory.importance,
                "is_active": memory.is_active,
            }
        except Exception as exc:
            return {"error": str(exc), "memory_id": memory_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: Delete Memory — 删除记忆
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_memory_delete",
    name="HR Memory Delete",
    endpoint="/api/v1/memories/{memory_id}",
    method="DELETE",
    tool_name="hr_memory_delete",
    permissions=["memory:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_memory_delete_v1",
    description="Delete a memory record permanently",
    request_model="MemoryDeleteRequest",
    response_model="MemoryDeleteResponse",
    rate_limit="30/minute",
    data_classification="L2",
    audit_level="detailed",
    tags=["hr", "memory", "delete"],
    timeout=10.0,
)
async def delete_memory(
    memory_id: str,
) -> dict[str, Any]:
    """
    Delete a memory record permanently.

    Args:
        memory_id: UUID of the memory to delete.

    Returns:
        Dict with deletion confirmation.
    """
    from uuid import UUID

    from app.dependencies import get_db
    from app.services.memory_service import MemoryService

    async for session in get_db():
        svc = MemoryService(session)
        try:
            deleted = await svc.delete_memory(UUID(memory_id))
            if not deleted:
                return {"error": "Memory not found", "memory_id": memory_id}
            return {
                "status": "success",
                "memory_id": memory_id,
                "message": "Memory deleted",
            }
        except Exception as exc:
            return {"error": str(exc), "memory_id": memory_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: Get Memory Stats — 统计
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_memory_stats",
    name="HR Memory Stats",
    endpoint="/api/v1/memories/stats",
    method="GET",
    tool_name="hr_memory_stats",
    permissions=["memory:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_memory_stats_v1",
    description="Get memory statistics (distribution by type, category, source)",
    request_model="MemoryStatsRequest",
    response_model="MemoryStatsResponse",
    rate_limit="60/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "memory", "stats"],
    timeout=10.0,
)
async def get_memory_stats(
    tenant_id: str = "default",
) -> dict[str, Any]:
    """
    Get memory statistics.

    Args:
        tenant_id: Tenant scope identifier.

    Returns:
        Dict with memory statistics.
    """
    from app.dependencies import get_db
    from app.services.memory_service import MemoryService

    async for session in get_db():
        svc = MemoryService(session)
        try:
            stats = await svc.get_memory_stats(tenant_id)
            return {
                "status": "success",
                "total": stats.total,
                "active": stats.active,
                "by_type": stats.by_type,
                "by_category": stats.by_category,
                "by_source": stats.by_source,
                "avg_confidence": stats.avg_confidence,
                "avg_importance": stats.avg_importance,
            }
        except Exception as exc:
            return {"error": str(exc)}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Utility: Simple embedding (mock)
# ---------------------------------------------------------------------------

def _simple_embedding(text: str, dim: int = 384) -> list[float]:
    """
    生成简单的伪向量（基于文本哈希），用于语义搜索占位。

    生产环境应替换为真实的 Embedding 模型。
    """
    import hashlib
    import struct

    result = []
    for i in range(dim):
        chunk = f"{text}:{i}".encode("utf-8")
        h = hashlib.md5(chunk).digest()
        val = struct.unpack("f", h[:4])[0]
        # Normalize to [-1, 1]
        result.append(max(-1.0, min(1.0, val / 1e10)))
    return result
