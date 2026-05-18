"""
Skills Router — endpoints for AI skill management.

Provides CRUD, invocation, and usage statistics for registered skills.
"""

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import CurrentUser, CurrentUserDep, DbSession, PaginationDep, require_role
from app.schemas.skill import (
    SkillCallRequest,
    SkillCallResponse,
    SkillCreate,
    SkillListResponse,
    SkillResponse,
    SkillStatsResponse,
    SkillUpdate,
)
from app.services.skill_service import SkillService

router = APIRouter()

_RecruiterOrAbove = Annotated[CurrentUser, Depends(require_role("recruiter", "hr_manager", "admin"))]


@router.get("", response_model=SkillListResponse, summary="List skills")
async def list_skills(
    db: DbSession,
    pagination: PaginationDep,
    current_user: CurrentUserDep,
    skill_type: str | None = Query(None, description="Filter by type: tool/prompt/workflow"),
    is_active: bool | None = Query(None, description="Filter by active status"),
):
    """List all registered skills for the current tenant."""
    service = SkillService(db)
    items, total = await service.list_skills(
        tenant_id=current_user.tenant_id,
        skill_type=skill_type,
        is_active=is_active,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    return SkillListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
    )


@router.post(
    "/",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register skill",
)
async def register_skill(
    payload: SkillCreate,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    """Register a new AI skill (tool, prompt, or workflow)."""
    service = SkillService(db)
    try:
        skill = await service.register_skill(
            data=payload,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    return skill


@router.get("/{skill_id}", response_model=SkillResponse, summary="Get skill details")
async def get_skill(
    skill_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Get details of a specific skill."""
    service = SkillService(db)
    skill = await service.get_skill(skill_id, current_user.tenant_id)
    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found"
        )
    return skill


@router.put("/{skill_id}", response_model=SkillResponse, summary="Update skill")
async def update_skill(
    skill_id: UUID,
    payload: SkillUpdate,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    """Update a skill's configuration."""
    service = SkillService(db)
    try:
        skill = await service.update_skill(
            skill_id=skill_id,
            data=payload,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=msg
        )
    return skill


@router.post("/{skill_id}/call", response_model=SkillCallResponse, summary="Call skill")
async def call_skill(
    skill_id: UUID,
    payload: SkillCallRequest,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Invoke a registered skill with input data."""
    service = SkillService(db)
    try:
        result = await service.call_skill(
            skill_id=skill_id,
            input_data=payload.input_data,
            tenant_id=current_user.tenant_id,
            timeout_seconds=payload.timeout_seconds,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    return SkillCallResponse(
        skill_id=skill_id,
        skill_name=result.get("skill_name", ""),
        skill_type=result.get("skill_type", ""),
        status=result.get("status", "error"),
        output=result.get("output"),
        latency_ms=result.get("latency_ms", 0),
        error=result.get("error"),
    )


@router.get("/{skill_id}/stats", response_model=SkillStatsResponse, summary="Skill usage stats")
async def get_skill_stats(
    skill_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """View usage statistics for a skill."""
    service = SkillService(db)
    try:
        stats = await service.get_skill_stats(
            skill_id=skill_id,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    return SkillStatsResponse(**stats)


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete skill",
)
async def delete_skill(
    skill_id: UUID,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    """Permanently delete a registered skill."""
    service = SkillService(db)
    try:
        await service.delete_skill(
            skill_id=skill_id,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
