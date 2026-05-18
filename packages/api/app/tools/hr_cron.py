"""
HR Cron Job Agent Tool.

Exposes cron job management capabilities as Agent Tools
via the ``@AiCapability`` decorator.

Registered capabilities:
  - ``hr_cron_job_create``   — Create a scheduled cron job
  - ``hr_cron_job_toggle``   — Enable/disable a cron job
  - ``hr_cron_job_list``     — List cron jobs for a tenant
  - ``hr_cron_job_logs``     — View execution logs for a cron job
  - ``hr_cron_job_delete``   — Delete a cron job
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.decorators.ai_capability import AiCapability

logger = logging.getLogger("hiremind.tools.hr_cron")


# ---------------------------------------------------------------------------
# Tool: Create Cron Job — 创建定时任务
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_cron_job_create",
    name="HR Cron Job Create",
    endpoint="/api/v1/cron/",
    method="POST",
    tool_name="hr_cron_job_create",
    permissions=["cron:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_cron_job_create_v1",
    description="Create a new scheduled cron job (daily report, weekly report, insight scan, data snapshot, or custom)",
    request_model="CronJobCreate",
    response_model="CronJobResponse",
    rate_limit="30/minute",
    data_classification="L2",
    audit_level="detailed",
    tags=["hr", "cron", "schedule"],
    timeout=10.0,
)
async def create_cron_job(
    *,
    name: str,
    task_type: str,
    schedule_config: dict,
    description: str | None = None,
    is_active: bool = True,
    max_retries: int = 3,
    timeout_seconds: int = 300,
    tenant_id: str = "default",
    user_id: str = "agent",
) -> dict[str, Any]:
    """
    Create a new scheduled cron job.

    Args:
        name: Human-readable job name.
        task_type: One of daily_report/weekly_report/insight_scan/data_snapshot/custom.
        schedule_config: Schedule configuration dict (cron_expr, interval_minutes, or specific_time).
        description: Optional job description.
        is_active: Whether to activate immediately.
        max_retries: Maximum retry attempts on failure.
        timeout_seconds: Execution timeout.
        tenant_id: Tenant scope identifier.
        user_id: Creator user ID.

    Returns:
        Dict with created cron job details.
    """
    from app.dependencies import get_db
    from app.schemas.cron import CronJobCreate
    from app.services.cron_service import CronService

    async for session in get_db():
        svc = CronService(session)
        create_data = CronJobCreate(
            name=name,
            description=description,
            task_type=task_type,
            schedule_config=schedule_config,
            is_active=is_active,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
        )
        try:
            job = await svc.create_job(
                data=create_data,
                tenant_id=tenant_id,
                user_id=user_id,
            )
            return {
                "status": "success",
                "job_id": str(job.id),
                "name": job.name,
                "task_type": job.task_type,
                "is_active": job.is_active,
                "next_run_at": str(job.next_run_at) if job.next_run_at else None,
            }
        except ValueError as exc:
            return {"error": str(exc), "name": name}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: Toggle Cron Job — 启停任务
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_cron_job_toggle",
    name="HR Cron Job Toggle",
    endpoint="/api/v1/cron/{job_id}/toggle",
    method="PATCH",
    tool_name="hr_cron_job_toggle",
    permissions=["cron:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_cron_job_toggle_v1",
    description="Enable or disable a cron job",
    request_model="CronJobToggleRequest",
    response_model="CronJobResponse",
    rate_limit="30/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "cron", "toggle"],
    timeout=10.0,
)
async def toggle_cron_job(
    job_id: str,
    tenant_id: str,
    *,
    active: bool = True,
) -> dict[str, Any]:
    """
    Enable or disable a cron job.

    Args:
        job_id: UUID of the cron job.
        tenant_id: Tenant scope identifier.
        active: True to enable, False to disable.

    Returns:
        Dict with updated job status.
    """
    from app.dependencies import get_db
    from app.services.cron_service import CronService

    async for session in get_db():
        svc = CronService(session)
        try:
            job = await svc.toggle_job(
                job_id=UUID(job_id),
                active=active,
                tenant_id=tenant_id,
            )
            return {
                "status": "success",
                "job_id": str(job.id),
                "name": job.name,
                "is_active": job.is_active,
                "next_run_at": str(job.next_run_at) if job.next_run_at else None,
            }
        except ValueError as exc:
            return {"error": str(exc), "job_id": job_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: List Cron Jobs — 查看任务列表
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_cron_job_list",
    name="HR Cron Job List",
    endpoint="/api/v1/cron/",
    method="GET",
    tool_name="hr_cron_job_list",
    permissions=["cron:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_cron_job_list_v1",
    description="List all cron jobs for a tenant with optional filters",
    request_model="CronJobListRequest",
    response_model="CronJobListResponse",
    rate_limit="60/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "cron", "list"],
    timeout=10.0,
)
async def list_cron_jobs(
    tenant_id: str,
    *,
    is_active: bool | None = None,
    task_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """
    List cron jobs for a tenant.

    Args:
        tenant_id: Tenant scope identifier.
        is_active: Optional filter by active status.
        task_type: Optional filter by task type.
        page: Page number (1-based).
        page_size: Items per page.

    Returns:
        Dict with paginated cron job list.
    """
    from app.dependencies import get_db
    from app.services.cron_service import CronService

    async for session in get_db():
        svc = CronService(session)
        offset = (page - 1) * page_size
        items, total = await svc.list_jobs(
            tenant_id=tenant_id,
            is_active=is_active,
            task_type=task_type,
            offset=offset,
            limit=page_size,
        )
        return {
            "status": "success",
            "items": [
                {
                    "job_id": str(j.id),
                    "name": j.name,
                    "task_type": j.task_type,
                    "is_active": j.is_active,
                    "last_run_at": str(j.last_run_at) if j.last_run_at else None,
                    "next_run_at": str(j.next_run_at) if j.next_run_at else None,
                    "failure_count": j.failure_count,
                }
                for j in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: Get Cron Logs — 查看执行日志
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_cron_job_logs",
    name="HR Cron Job Logs",
    endpoint="/api/v1/cron/{job_id}/logs",
    method="GET",
    tool_name="hr_cron_job_logs",
    permissions=["cron:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_cron_job_logs_v1",
    description="View execution logs for a specific cron job",
    request_model="CronLogListRequest",
    response_model="CronLogListResponse",
    rate_limit="60/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "cron", "logs"],
    timeout=10.0,
)
async def get_cron_logs(
    job_id: str,
    tenant_id: str,
    *,
    limit: int = 20,
) -> dict[str, Any]:
    """
    View execution logs for a cron job.

    Args:
        job_id: UUID of the cron job.
        tenant_id: Tenant scope identifier.
        limit: Maximum number of log entries.

    Returns:
        Dict with execution log entries.
    """
    from app.dependencies import get_db
    from app.services.cron_service import CronService

    async for session in get_db():
        svc = CronService(session)
        try:
            logs, total = await svc.get_job_logs(
                job_id=UUID(job_id),
                tenant_id=tenant_id,
                limit=limit,
            )
            return {
                "status": "success",
                "job_id": job_id,
                "logs": [
                    {
                        "log_id": str(lg.id),
                        "status": lg.status,
                        "started_at": str(lg.started_at),
                        "finished_at": str(lg.finished_at) if lg.finished_at else None,
                        "duration_seconds": lg.duration_seconds,
                        "error_message": lg.error_message,
                        "retry_attempt": lg.retry_attempt,
                    }
                    for lg in logs
                ],
                "total": total,
            }
        except ValueError as exc:
            return {"error": str(exc), "job_id": job_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: Delete Cron Job — 删除任务
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_cron_job_delete",
    name="HR Cron Job Delete",
    endpoint="/api/v1/cron/{job_id}",
    method="DELETE",
    tool_name="hr_cron_job_delete",
    permissions=["cron:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_cron_job_delete_v1",
    description="Delete a cron job and all its execution logs",
    request_model="CronJobDeleteRequest",
    response_model="CronJobDeleteResponse",
    rate_limit="30/minute",
    data_classification="L2",
    audit_level="detailed",
    tags=["hr", "cron", "delete"],
    timeout=10.0,
)
async def delete_cron_job(
    job_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Delete a cron job permanently.

    Args:
        job_id: UUID of the cron job to delete.
        tenant_id: Tenant scope identifier.

    Returns:
        Dict with deletion confirmation.
    """
    from app.dependencies import get_db
    from app.services.cron_service import CronService

    async for session in get_db():
        svc = CronService(session)
        try:
            await svc.delete_job(
                job_id=UUID(job_id),
                tenant_id=tenant_id,
            )
            return {
                "status": "success",
                "job_id": job_id,
                "message": "Cron job deleted",
            }
        except ValueError as exc:
            return {"error": str(exc), "job_id": job_id}

    return {"error": "Database session unavailable"}
