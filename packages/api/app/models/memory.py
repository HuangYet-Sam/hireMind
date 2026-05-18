"""
Memory Model — 招聘记忆系统核心模型。

存储 HR 操作中提取的偏好、洞察、决策模式等记忆，
支持语义检索和关联分析，为主动式 AI 提供知识基础。

Memory types:
  - preference:  HR 偏好（偏好某类候选人/薪资范围/技能权重）
  - insight:     系统洞察（从数据中发现的规律）
  - decision:    决策记录（筛选/面试/Offer 决策）
  - pattern:     行为模式（常用筛选条件/偏好渠道）
  - fact:        事实信息（团队规模/招聘周期等）
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PrimaryKeyMixin, TenantMixin, TimestampMixin


class Memory(Base, PrimaryKeyMixin, TimestampMixin, TenantMixin):
    """招聘记忆 — 存储 HR 偏好、洞察、决策模式等结构化知识。"""

    __tablename__ = "memories"

    memory_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="记忆类型: preference/insight/decision/pattern/fact",
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="分类: recruitment/candidate/interview/offer/market/team",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="记忆内容",
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="system",
        index=True,
        comment="来源: interaction/log/system/ai_inferred",
    )
    source_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="来源实体 ID（如候选人 ID、岗位 ID）",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
        comment="置信度 (0-1)",
    )
    importance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
        comment="重要性 (0-1)",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="过期时间（null 表示永不过期）",
    )
    access_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="访问次数",
    )
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后访问时间",
    )
    tags: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="标签列表",
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
        comment="元数据（来源详情、提取参数等）",
    )
    embedding: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="向量嵌入（用于语义相关性检索）",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="是否激活",
    )

    def __repr__(self) -> str:
        return f"<Memory {self.id} type={self.memory_type} category={self.category}>"
