"""
Cron Router — endpoints for scheduled task management.

Provides CRUD, toggle, manual execution, and log viewing for CronJobs.
"""

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import CurrentUser, CurrentUserDep, DbSession, PaginationDep, require_role
from app.schemas.cron import (
    CronJobCreate,
    CronJobListResponse,
    CronJobResponse,
    CronJobUpdate,
    CronLogListResponse,
    CronLogResponse,
)
from app.services.cron_service import CronService

router = APIRouter()

_RecruiterOrAbove = Annotated[CurrentUser, Depends(require_role("recruiter", "hr_manager", "admin"))]


@router.get("", response_model=CronJobListResponse, summary="List cron jobs")
async def list_cron_jobs(
    db: DbSession,
    pagination: PaginationDep,
    current_user: CurrentUserDep,
    is_active: bool | None = Query(None, description="Filter by active status"),
    task_type: str | None = Query(None, description="Filter by task type"),
):
    """List all cron jobs for the current tenant."""
    service = CronService(db)
    items, total = await service.list_jobs(
        tenant_id=current_user.tenant_id,
        is_active=is_active,
        task_type=task_type,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    return CronJobListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
    )


@router.post(
    "/",
    response_model=CronJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create cron job",
)
async def create_cron_job(
    payload: CronJobCreate,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    """Create a new scheduled cron job."""
    service = CronService(db)
    try:
        job = await service.create_job(
            data=payload,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    return job


@router.get("/{job_id}", response_model=CronJobResponse, summary="Get cron job")
async def get_cron_job(
    job_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Get details of a specific cron job."""
    service = CronService(db)
    job = await service.get_job(job_id, current_user.tenant_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cron job not found"
        )
    return job


@router.put("/{job_id}", response_model=CronJobResponse, summary="Update cron job")
async def update_cron_job(
    job_id: UUID,
    payload: CronJobUpdate,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    """Update a cron job's configuration."""
    service = CronService(db)
    try:
        job = await service.update_job(
            job_id=job_id,
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
    return job


@router.patch("/{job_id}/toggle", response_model=CronJobResponse, summary="Toggle cron job")
async def toggle_cron_job(
    job_id: UUID,
    db: DbSession,
    current_user: _RecruiterOrAbove,
    active: bool = Query(..., description="True to enable, False to disable"),
):
    """Enable or disable a cron job."""
    service = CronService(db)
    try:
        job = await service.toggle_job(
            job_id=job_id,
            active=active,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    return job


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete cron job",
)
async def delete_cron_job(
    job_id: UUID,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    """Delete a cron job and all its execution logs."""
    service = CronService(db)
    try:
        await service.delete_job(
            job_id=job_id,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )


@router.get("/{job_id}/logs", response_model=CronLogListResponse, summary="Cron job execution logs")
async def get_cron_logs(
    job_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
    limit: int = Query(20, ge=1, le=100, description="Max log entries"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """View execution logs for a specific cron job."""
    service = CronService(db)
    logs, total = await service.get_job_logs(
        job_id=job_id,
        tenant_id=current_user.tenant_id,
        limit=limit,
        offset=offset,
    )
    return CronLogListResponse(
        items=logs,
        total=total,
    )


@router.post("/{job_id}/execute", response_model=CronLogResponse, summary="Manually execute cron job")
async def execute_cron_job(
    job_id: UUID,
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    """Manually trigger execution of a cron job."""
    service = CronService(db)
    try:
        log = await service.execute_job(
            job_id=job_id,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    return log
