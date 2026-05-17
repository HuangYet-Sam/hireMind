"""
AI Tasks Router.

Endpoints for managing background AI tasks (list, create, get, cancel, retry).
"""

import math
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUserDep, DbSession
from app.models.ai_task import TaskStatus
from app.schemas.ai_task import (
    AiTaskCreate,
    AiTaskResponse,
    PaginatedAiTaskResponse,
)
from app.services.ai_task_service import AiTaskService

router = APIRouter()


@router.get("/", response_model=PaginatedAiTaskResponse, summary="List AI tasks")
async def list_ai_tasks(
    db: DbSession,
    current_user: CurrentUserDep,
    task_status: TaskStatus | None = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    service = AiTaskService(db)
    items, total = await service.list_tasks(
        tenant_id=current_user.tenant_id,
        status=task_status,
        page=page,
        page_size=page_size,
    )
    pages = math.ceil(total / page_size) if total > 0 else 0
    return PaginatedAiTaskResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post(
    "/",
    response_model=AiTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create AI task",
)
async def create_ai_task(
    payload: AiTaskCreate,
    db: DbSession,
    current_user: CurrentUserDep,
):
    service = AiTaskService(db)
    task = await service.create_task(
        tenant_id=current_user.tenant_id,
        data=payload,
        user_id=current_user.user_id,
    )
    return task


@router.get(
    "/{task_id}",
    response_model=AiTaskResponse,
    summary="Get AI task by ID",
)
async def get_ai_task(
    task_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    service = AiTaskService(db)
    task = await service.get_task(task_id, current_user.tenant_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return task


@router.post(
    "/{task_id}/cancel",
    response_model=AiTaskResponse,
    summary="Cancel AI task",
)
async def cancel_ai_task(
    task_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    service = AiTaskService(db)
    try:
        task = await service.cancel_task(task_id, current_user.tenant_id)
    except ValueError as exc:
        msg = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in msg
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(status_code=status_code, detail=msg)
    return task


@router.post(
    "/{task_id}/retry",
    response_model=AiTaskResponse,
    summary="Retry AI task",
)
async def retry_ai_task(
    task_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    service = AiTaskService(db)
    try:
        task = await service.retry_task(task_id, current_user.tenant_id)
    except ValueError as exc:
        msg = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in msg
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(status_code=status_code, detail=msg)
    return task
