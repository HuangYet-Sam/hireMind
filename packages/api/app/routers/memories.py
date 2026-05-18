"""
Memories Router — endpoints for memory management.

Provides CRUD, semantic search, statistics, cold-start building,
and consolidation for the memory system.
"""

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import CurrentUser, CurrentUserDep, DbSession, PaginationDep, require_role
from app.schemas.memory import (
    MemoryBuildResponse,
    MemoryCreate,
    MemoryListResponse,
    MemoryResponse,
    MemorySearchRequest,
    MemoryStatsResponse,
    MemoryUpdate,
)
from app.services.memory_service import MemoryService

router = APIRouter()

_RecruiterOrAbove = Annotated[CurrentUser, Depends(require_role("recruiter", "hr_manager", "admin"))]


@router.get("", response_model=MemoryListResponse, summary="List memories")
async def list_memories(
    db: DbSession,
    pagination: PaginationDep,
    current_user: CurrentUserDep,
    memory_type: str | None = Query(None, description="Filter by type: preference/insight/decision/pattern/fact"),
    category: str | None = Query(None, description="Filter by category: recruitment/candidate/interview/offer/market/team"),
    search: str | None = Query(None, description="Keyword search in content"),
):
    """List all memories for the current tenant with optional filters."""
    service = MemoryService(db)
    items, total = await service.list_memories(
        tenant_id=current_user.tenant_id,
        memory_type=memory_type,
        category=category,
        offset=pagination.offset,
        limit=pagination.limit,
    )

    # Keyword search filter (post-fetch, simple containment)
    if search:
        search_lower = search.lower()
        items = [m for m in items if search_lower in (m.content or "").lower()]
        total = len(items)

    pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    return MemoryListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
    )


@router.post(
    "/",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create memory",
)
async def create_memory(
    payload: MemoryCreate,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    """Create a new memory record."""
    service = MemoryService(db)
    try:
        memory = await service.create_memory(
            data=payload,
            tenant_id=current_user.tenant_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    return memory


@router.get("/search", summary="Semantic search memories")
async def search_memories(
    db: DbSession,
    current_user: CurrentUserDep,
    query: str = Query(..., min_length=1, description="Search query text"),
    top_k: int = Query(10, ge=1, le=100, description="Number of results"),
):
    """Semantic search memories by query text.

    When embeddings are available, performs cosine similarity search.
    Falls back to keyword matching when no embeddings exist.
    """
    service = MemoryService(db)

    # Generate simple embedding (mock for now)
    query_embedding = _simple_embedding(query)

    try:
        results = await service.search_memories(
            query_embedding=query_embedding,
            tenant_id=current_user.tenant_id,
            top_k=top_k,
        )
        return {
            "status": "success",
            "query": query,
            "total": len(results),
            "results": [
                {
                    "memory_id": str(r["memory"].id),
                    "content": r["memory"].content,
                    "memory_type": r["memory"].memory_type,
                    "category": r["memory"].category,
                    "similarity": round(r["similarity"], 3),
                    "confidence": r["memory"].confidence,
                    "importance": r["memory"].importance,
                }
                for r in results
            ],
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {exc}",
        )


@router.get("/stats", response_model=MemoryStatsResponse, summary="Memory statistics")
async def get_memory_stats(
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Get memory statistics for the current tenant."""
    service = MemoryService(db)
    stats = await service.get_memory_stats(current_user.tenant_id)
    return stats


@router.get("/{memory_id}", response_model=MemoryResponse, summary="Get memory details")
async def get_memory(
    memory_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Get details of a specific memory."""
    service = MemoryService(db)
    memory = await service.get_memory(memory_id)
    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found"
        )
    # Increment access count
    await service.increment_access(memory_id)
    return memory


@router.put("/{memory_id}", response_model=MemoryResponse, summary="Update memory")
async def update_memory(
    memory_id: UUID,
    payload: MemoryUpdate,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    """Update a memory record."""
    service = MemoryService(db)
    memory = await service.update_memory(
        memory_id=memory_id,
        data=payload,
    )
    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found"
        )
    return memory


@router.delete(
    "/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete memory",
)
async def delete_memory(
    memory_id: UUID,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    """Delete a memory record permanently."""
    service = MemoryService(db)
    deleted = await service.delete_memory(memory_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found"
        )


@router.post("/build", response_model=MemoryBuildResponse, summary="Build initial memories (cold start)")
async def build_memories(
    db: DbSession,
    current_user: _RecruiterOrAbove,
    days: int = Query(7, ge=1, le=30, description="Number of history days to analyze"),
):
    """Trigger cold-start memory building from historical data.

    Analyzes the last N days of recruitment activity to extract
    preferences, patterns, and decision records.
    """
    from app.services.memory_builder import MemoryBuilder

    builder = MemoryBuilder(db)
    try:
        result = await builder.build_initial_memories(
            tenant_id=current_user.tenant_id,
            days=days,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Memory build failed: {exc}",
        )
    return MemoryBuildResponse(**result)


@router.post("/consolidate", summary="Consolidate memories")
async def consolidate_memories(
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    """Merge similar memories and resolve contradictions.

    Runs the memory consolidation engine to:
    - Merge highly similar memories
    - Resolve contradictory memories (keep latest)
    - Expire low-confidence, never-accessed memories
    """
    from app.services.memory_builder import MemoryBuilder

    builder = MemoryBuilder(db)
    try:
        stats = await builder.consolidate_memories(
            tenant_id=current_user.tenant_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Consolidation failed: {exc}",
        )
    return {
        "status": "success",
        "merged": stats.get("merged", 0),
        "contradicted": stats.get("contradicted", 0),
        "expired": stats.get("expired", 0),
    }


# ---------------------------------------------------------------------------
# Utility: Simple embedding (mock)
# ---------------------------------------------------------------------------

def _simple_embedding(text: str, dim: int = 384) -> list[float]:
    """
    Generate a simple pseudo-embedding (hash-based) for semantic search.

    In production, replace with a real embedding model.
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
