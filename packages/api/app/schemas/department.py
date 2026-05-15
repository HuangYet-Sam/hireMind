"""
Department Pydantic Schemas.

Request / response models for Department CRUD and tree endpoints.
Aligned to DDL §7.2.1 (M1 module).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    """Schema for creating a department."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str | None = Field(None, max_length=50, description="Department code (e.g. ENG, HR)")
    parent_id: UUID | None = Field(None, description="Parent department ID")
    description: str | None = None
    head_user_id: str | None = Field(None, description="Department head user ID")
    headcount_limit: int | None = None
    sort_order: int = 0


class DepartmentUpdate(BaseModel):
    """Schema for updating a department."""

    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = None
    parent_id: UUID | None = None
    description: str | None = None
    head_user_id: str | None = None
    headcount_limit: int | None = None
    status: str | None = None
    sort_order: int | None = None


class DepartmentResponse(BaseModel):
    """Department response schema (flat, includes DDL fields)."""

    id: UUID
    name: str
    code: str | None
    parent_id: UUID | None
    description: str | None
    head_user_id: str | None
    headcount_limit: int | None
    current_headcount: int
    status: str
    sort_order: int
    tree_path: str | None = Field(None, description="Materialized path, e.g. 'tech.backend'")
    manager_name: str | None = Field(None, description="Department manager display name")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DepartmentListResponse(BaseModel):
    """Department list response (flat)."""

    items: list[DepartmentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class DepartmentTreeNode(BaseModel):
    """Recursive tree node for a single department with its children."""

    id: UUID
    name: str
    code: str | None
    parent_id: UUID | None
    description: str | None
    head_user_id: str | None
    headcount_limit: int | None
    current_headcount: int
    status: str
    sort_order: int
    tree_path: str | None
    manager_name: str | None
    created_at: datetime
    updated_at: datetime
    children: list[DepartmentTreeNode] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class DepartmentTreeResponse(BaseModel):
    """Response wrapper containing the department tree."""

    tree: list[DepartmentTreeNode]
