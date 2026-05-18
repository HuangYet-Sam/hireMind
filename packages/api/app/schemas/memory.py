"""
Memory Pydantic Schemas — 记忆系统的请求/响应模型。

包含记忆的创建、更新、响应、搜索请求、关联响应等 Schema。
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Memory Type Enums (as string literals for validation) ──────────────

MEMORY_TYPES = {"preference", "insight", "decision", "pattern", "fact"}
MEMORY_CATEGORIES = {"recruitment", "candidate", "interview", "offer", "market", "team"}
MEMORY_SOURCES = {"interaction", "log", "system", "ai_inferred"}
RELATION_TYPES = {"similar", "contradicts", "supplements", "derived_from"}


# ── Request Schemas ────────────────────────────────────────────────────

class MemoryCreate(BaseModel):
    """创建记忆请求。"""

    memory_type: str = Field(
        ..., description="记忆类型: preference/insight/decision/pattern/fact",
    )
    category: str = Field(
        ..., description="分类: recruitment/candidate/interview/offer/market/team",
    )
    content: str = Field(..., min_length=1, description="记忆内容")
    source: str = Field("system", description="来源: interaction/log/system/ai_inferred")
    source_id: str | None = Field(None, description="来源实体 ID")
    confidence: float = Field(0.5, ge=0.0, le=1.0, description="置信度")
    importance: float = Field(0.5, ge=0.0, le=1.0, description="重要性")
    expires_at: datetime | None = Field(None, description="过期时间")
    tags: list[str] | None = Field(None, description="标签列表")
    metadata_: dict | None = Field(None, alias="metadata", description="元数据")
    embedding: list[float] | None = Field(None, description="向量嵌入")


class MemoryUpdate(BaseModel):
    """更新记忆请求。"""

    memory_type: str | None = None
    category: str | None = None
    content: str | None = Field(None, min_length=1)
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    importance: float | None = Field(None, ge=0.0, le=1.0)
    expires_at: datetime | None = None
    tags: list[str] | None = None
    metadata_: dict | None = Field(None, alias="metadata")
    embedding: list[float] | None = None
    is_active: bool | None = None


class MemorySearchRequest(BaseModel):
    """记忆语义搜索请求。"""

    query: str = Field(..., min_length=1, description="搜索查询文本")
    memory_type: str | None = Field(None, description="按记忆类型筛选")
    category: str | None = Field(None, description="按分类筛选")
    tags: list[str] | None = Field(None, description="按标签筛选")
    top_k: int = Field(10, ge=1, le=100, description="返回前 K 个结果")
    min_confidence: float = Field(0.0, ge=0.0, le=1.0, description="最低置信度阈值")
    min_importance: float = Field(0.0, ge=0.0, le=1.0, description="最低重要性阈值")


# ── Response Schemas ───────────────────────────────────────────────────

class MemoryResponse(BaseModel):
    """记忆响应。"""

    id: UUID
    tenant_id: str
    memory_type: str
    category: str
    content: str
    source: str
    source_id: str | None
    confidence: float
    importance: float
    expires_at: datetime | None
    access_count: int
    last_accessed_at: datetime | None
    tags: list | None
    metadata_: dict | None = Field(None, alias="metadata")
    embedding: list[float] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class MemoryListResponse(BaseModel):
    """分页记忆列表。"""

    items: list[MemoryResponse]
    total: int
    page: int
    page_size: int
    pages: int


class MemoryStatsResponse(BaseModel):
    """记忆统计。"""

    total: int = Field(0, description="记忆总数")
    active: int = Field(0, description="活跃记忆数")
    by_type: dict[str, int] = Field(default_factory=dict, description="按类型分布")
    by_category: dict[str, int] = Field(default_factory=dict, description="按分类分布")
    by_source: dict[str, int] = Field(default_factory=dict, description="按来源分布")
    avg_confidence: float = Field(0.0, description="平均置信度")
    avg_importance: float = Field(0.0, description="平均重要性")


class MemoryRelationResponse(BaseModel):
    """记忆关联响应。"""

    id: UUID
    source_memory_id: UUID
    target_memory_id: UUID
    relation_type: str
    strength: float
    tenant_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoryBuildResponse(BaseModel):
    """记忆构建（冷启动）响应。"""

    total_extracted: int = Field(0, description="提取的记忆总数")
    new_memories: int = Field(0, description="新增记忆数")
    updated_memories: int = Field(0, description="更新记忆数")
    categories: dict[str, int] = Field(default_factory=dict, description="按分类统计")
    duration_seconds: float = Field(0.0, description="耗时（秒）")
