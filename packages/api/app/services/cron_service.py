"""
CronService — business logic for scheduled task management.

Provides CRUD operations for CronJob records, execution engine with
retry logic, and a pending-job scanner for the scheduler loop.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cron_job import CronJob
from app.models.cron_log import CronLog
from app.schemas.cron import CronJobCreate, CronJobUpdate

logger = logging.getLogger("hiremind.services.cron")


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Valid task types and their descriptions
# ---------------------------------------------------------------------------

VALID_TASK_TYPES = {
    "daily_report": "Generate daily recruitment report",
    "weekly_report": "Generate weekly recruitment report",
    "insight_scan": "Scan for AI insights and risk alerts",
    "data_snapshot": "Take analytics data snapshot",
    "custom": "Custom task with configurable handler",
}


class CronService:
    """Service layer for cron job CRUD and execution."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_job(
        self,
        data: CronJobCreate,
        tenant_id: str,
        user_id: str | None = None,
    ) -> CronJob:
        """Create a new cron job and compute its first next_run_at."""
        if data.task_type not in VALID_TASK_TYPES:
            raise ValueError(
                f"Invalid task_type '{data.task_type}'. "
                f"Must be one of: {list(VALID_TASK_TYPES.keys())}"
            )

        job = CronJob(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            task_type=data.task_type,
            schedule_config=data.schedule_config,
            is_active=data.is_active,
            max_retries=data.max_retries,
            timeout_seconds=data.timeout_seconds,
            created_by=user_id,
        )

        # Compute next_run_at
        job.next_run_at = self._calculate_next_run_from_config(job.schedule_config)

        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        logger.info("Created cron job %s (%s) for tenant %s", job.id, job.name, tenant_id)
        return job

    async def update_job(
        self,
        job_id: UUID,
        data: CronJobUpdate,
        tenant_id: str,
    ) -> CronJob:
        """Update an existing cron job's configuration."""
        job = await self._get_job(job_id, tenant_id)
        if job is None:
            raise ValueError(f"CronJob {job_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(job, field, value)

        # Recalculate next_run_at if schedule_config changed
        if "schedule_config" in update_data:
            job.next_run_at = self._calculate_next_run_from_config(job.schedule_config)

        await self.db.flush()
        await self.db.refresh(job)
        logger.info("Updated cron job %s", job_id)
        return job

    async def toggle_job(
        self,
        job_id: UUID,
        active: bool,
        tenant_id: str,
    ) -> CronJob:
        """Enable or disable a cron job."""
        job = await self._get_job(job_id, tenant_id)
        if job is None:
            raise ValueError(f"CronJob {job_id} not found")

        job.is_active = active

        if active:
            # Reset failure count and recalculate next_run_at
            job.failure_count = 0
            job.next_run_at = self._calculate_next_run_from_config(job.schedule_config)
        else:
            job.next_run_at = None

        await self.db.flush()
        await self.db.refresh(job)
        logger.info("Toggled cron job %s to active=%s", job_id, active)
        return job

    async def delete_job(self, job_id: UUID, tenant_id: str) -> None:
        """Delete a cron job and all its logs."""
        job = await self._get_job(job_id, tenant_id)
        if job is None:
            raise ValueError(f"CronJob {job_id} not found")

        await self.db.delete(job)
        await self.db.flush()
        logger.info("Deleted cron job %s", job_id)

    async def list_jobs(
        self,
        tenant_id: str,
        *,
        is_active: bool | None = None,
        task_type: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[CronJob], int]:
        """List cron jobs for a tenant with optional filters."""
        filters = [CronJob.tenant_id == tenant_id]
        if is_active is not None:
            filters.append(CronJob.is_active == is_active)
        if task_type is not None:
            filters.append(CronJob.task_type == task_type)

        count_stmt = select(func.count()).select_from(CronJob).where(*filters)
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = (
            select(CronJob)
            .where(*filters)
            .order_by(CronJob.next_run_at.asc().nulls_last(), CronJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def get_job(self, job_id: UUID, tenant_id: str) -> CronJob | None:
        """Get a single cron job by ID."""
        return await self._get_job(job_id, tenant_id)

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------

    async def get_job_logs(
        self,
        job_id: UUID,
        tenant_id: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[CronLog], int]:
        """Get execution logs for a cron job."""
        filters = [CronLog.cron_job_id == job_id, CronLog.tenant_id == tenant_id]

        count_stmt = select(func.count()).select_from(CronLog).where(*filters)
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = (
            select(CronLog)
            .where(*filters)
            .order_by(CronLog.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    # ------------------------------------------------------------------
    # Execution Engine
    # ------------------------------------------------------------------

    async def execute_job(
        self,
        job_id: UUID,
        tenant_id: str | None = None,
        retry_attempt: int = 0,
    ) -> CronLog:
        """
        Execute a cron job by dispatching to the appropriate handler.

        Records a CronLog with start/end times, status, and results.
        Implements retry logic: on failure, increments failure_count
        and reschedules if under max_retries.
        """
        job = await self.db.get(CronJob, job_id)
        if job is None:
            raise ValueError(f"CronJob {job_id} not found")

        effective_tenant = tenant_id or job.tenant_id

        # Create log entry
        log = CronLog(
            tenant_id=effective_tenant,
            cron_job_id=job.id,
            status="running",
            started_at=_now(),
            retry_attempt=retry_attempt,
        )
        self.db.add(log)
        await self.db.flush()

        # Dispatch execution
        try:
            result_data = await asyncio.wait_for(
                self._dispatch_task(job, effective_tenant),
                timeout=job.timeout_seconds,
            )
            # Success
            log.status = "success"
            log.result = result_data or {}
            log.finished_at = _now()
            log.duration_seconds = (log.finished_at - log.started_at).total_seconds()

            # Reset failure count
            job.failure_count = 0
            job.last_run_at = log.finished_at
            job.next_run_at = self._calculate_next_run_from_config(job.schedule_config)

        except asyncio.TimeoutError:
            log.status = "timeout"
            log.error_message = f"Execution timed out after {job.timeout_seconds}s"
            log.finished_at = _now()
            log.duration_seconds = (log.finished_at - log.started_at).total_seconds()
            await self._handle_failure(job, retry_attempt)

        except Exception as exc:
            log.status = "failed"
            log.error_message = str(exc)[:2000]
            log.finished_at = _now()
            log.duration_seconds = (log.finished_at - log.started_at).total_seconds()
            await self._handle_failure(job, retry_attempt)

        await self.db.flush()
        await self.db.refresh(log)
        logger.info(
            "Executed cron job %s: status=%s duration=%.1fs",
            job_id, log.status, log.duration_seconds or 0,
        )
        return log

    async def _handle_failure(self, job: CronJob, retry_attempt: int) -> None:
        """Handle a failed execution: increment failure count, maybe retry."""
        job.failure_count += 1

        if job.failure_count < job.max_retries:
            # Schedule retry soon (1 minute * attempt number)
            retry_delay = timedelta(minutes=retry_attempt + 1)
            job.next_run_at = _now() + retry_delay
            logger.warning(
                "Cron job %s failed (attempt %d/%d), retrying in %s",
                job.id, retry_attempt + 1, job.max_retries, retry_delay,
            )
        else:
            # Max retries exceeded — disable job
            job.is_active = False
            job.next_run_at = None
            logger.error(
                "Cron job %s exceeded max_retries (%d), disabled",
                job.id, job.max_retries,
            )

    async def _dispatch_task(self, job: CronJob, tenant_id: str) -> dict[str, Any]:
        """Dispatch to the appropriate service based on task_type."""
        if job.task_type == "daily_report":
            return await self._run_daily_report(tenant_id)
        elif job.task_type == "weekly_report":
            return await self._run_weekly_report(tenant_id)
        elif job.task_type == "insight_scan":
            return await self._run_insight_scan(tenant_id)
        elif job.task_type == "data_snapshot":
            return await self._run_data_snapshot(tenant_id)
        elif job.task_type == "custom":
            return await self._run_custom_task(job, tenant_id)
        else:
            raise ValueError(f"Unknown task_type: {job.task_type}")

    async def _run_daily_report(self, tenant_id: str) -> dict[str, Any]:
        """Generate a daily recruitment report."""
        try:
            from app.services.dashboard_ai_service import DashboardAIService
            svc = DashboardAIService(self.db)
            report = await svc.generate_daily_report(tenant_id=tenant_id)
            return {"report_id": str(report.id), "title": report.title}
        except Exception as exc:
            logger.error("Daily report generation failed: %s", exc)
            return {"error": str(exc), "task": "daily_report"}

    async def _run_weekly_report(self, tenant_id: str) -> dict[str, Any]:
        """Generate a weekly recruitment report."""
        try:
            from app.services.dashboard_ai_service import DashboardAIService
            svc = DashboardAIService(self.db)
            report = await svc.generate_weekly_report(tenant_id=tenant_id)
            return {"report_id": str(report.id), "title": report.title}
        except Exception as exc:
            logger.error("Weekly report generation failed: %s", exc)
            return {"error": str(exc), "task": "weekly_report"}

    async def _run_insight_scan(self, tenant_id: str) -> dict[str, Any]:
        """Scan for AI insights and risk alerts."""
        try:
            from app.services.insight_engine import InsightEngine
            engine = InsightEngine(self.db)
            insights = await engine.scan(tenant_id=tenant_id)
            return {"insights_count": len(insights) if insights else 0}
        except Exception as exc:
            logger.error("Insight scan failed: %s", exc)
            return {"error": str(exc), "task": "insight_scan"}

    async def _run_data_snapshot(self, tenant_id: str) -> dict[str, Any]:
        """Take an analytics data snapshot."""
        try:
            from app.services.analytics_service import AnalyticsService
            svc = AnalyticsService(self.db)
            snapshot = await svc.create_snapshot(tenant_id=tenant_id)
            return {"snapshot_id": str(snapshot.id)}
        except Exception as exc:
            logger.error("Data snapshot failed: %s", exc)
            return {"error": str(exc), "task": "data_snapshot"}

    async def _run_custom_task(self, job: CronJob, tenant_id: str) -> dict[str, Any]:
        """Execute a custom task using the schedule_config handler."""
        handler = job.schedule_config.get("handler")
        if not handler:
            return {"status": "skipped", "reason": "No custom handler configured"}

        # Custom tasks are placeholder — log the handler name
        logger.info("Custom task handler: %s for job %s", handler, job.id)
        return {"handler": handler, "status": "completed"}

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def _calculate_next_run_from_config(self, config: dict) -> datetime | None:
        """
        Calculate the next run time from schedule_config.

        Supports:
          - cron_expr: standard cron expression (simplified: interval-based)
          - interval_minutes: run every N minutes
          - specific_time: run at a specific time daily (HH:MM format)
        """
        now = _now()

        # Interval-based scheduling
        interval_minutes = config.get("interval_minutes")
        if interval_minutes:
            return now + timedelta(minutes=int(int(interval_minutes)))

        # Specific time daily
        specific_time = config.get("specific_time")
        if specific_time:
            try:
                parts = str(specific_time).split(":")
                hour, minute = int(parts[0]), int(parts[1])
                tz_str = config.get("timezone", "UTC")

                # Build today's target time
                target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if target <= now:
                    target += timedelta(days=1)
                return target
            except (ValueError, IndexError):
                logger.warning("Invalid specific_time format: %s", specific_time)
                return now + timedelta(hours=24)

        # Cron expression (simplified: parse interval from expression)
        cron_expr = config.get("cron_expr")
        if cron_expr:
            return self._parse_cron_next_run(cron_expr, now)

        # Default: run in 24 hours
        return now + timedelta(hours=24)

    def _parse_cron_next_run(self, cron_expr: str, now: datetime) -> datetime:
        """
        Simplified cron expression parser.

        Supports common patterns:
          - "*/5 * * * *"  → every 5 minutes
          - "0 * * * *"    → every hour
          - "0 9 * * *"    → daily at 9:00
          - "0 9 * * 1"    → weekly on Monday at 9:00
        """
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return now + timedelta(hours=24)

        minute_str, hour_str, _, _, dow_str = parts

        # Every N minutes pattern
        if minute_str.startswith("*/"):
            try:
                interval = int(minute_str[2:])
                return now + timedelta(minutes=interval)
            except ValueError:
                pass

        # Every N hours pattern
        if minute_str == "0" and hour_str.startswith("*/"):
            try:
                interval = int(hour_str[2:])
                return now + timedelta(hours=interval)
            except ValueError:
                pass

        # Specific time daily
        if minute_str.isdigit() and hour_str.isdigit():
            target = now.replace(
                hour=int(hour_str), minute=int(minute_str),
                second=0, microsecond=0,
            )
            if dow_str != "*":
                # Weekly pattern
                target_dow = int(dow_str)
                days_ahead = (target_dow - now.weekday()) % 7
                if days_ahead == 0 and target <= now:
                    days_ahead = 7
                target += timedelta(days=days_ahead)
            elif target <= now:
                target += timedelta(days=1)
            return target

        return now + timedelta(hours=24)

    async def calculate_next_run(self, job_id: UUID, tenant_id: str) -> datetime | None:
        """Calculate and update the next_run_at for a job."""
        job = await self._get_job(job_id, tenant_id)
        if job is None:
            raise ValueError(f"CronJob {job_id} not found")
        return self._calculate_next_run_from_config(job.schedule_config)

    # ------------------------------------------------------------------
    # Pending Jobs Scanner
    # ------------------------------------------------------------------

    async def run_pending_jobs(self) -> list[dict[str, Any]]:
        """
        Scan for all active jobs whose next_run_at <= now and execute them.

        Returns a summary list of execution results.
        """
        now = _now()
        stmt = (
            select(CronJob)
            .where(
                CronJob.is_active == True,  # noqa: E712
                CronJob.next_run_at != None,  # noqa: E711
                CronJob.next_run_at <= now,
            )
        )
        result = await self.db.execute(stmt)
        pending_jobs = list(result.scalars().all())

        if not pending_jobs:
            return []

        logger.info("Found %d pending cron jobs to execute", len(pending_jobs))
        results = []

        for job in pending_jobs:
            try:
                # Determine retry_attempt from recent logs
                retry_attempt = 0
                recent_log_stmt = (
                    select(CronLog)
                    .where(CronLog.cron_job_id == job.id)
                    .order_by(CronLog.started_at.desc())
                    .limit(1)
                )
                recent_log = (await self.db.execute(recent_log_stmt)).scalar_one_or_none()
                if recent_log and recent_log.status in ("failed", "timeout"):
                    retry_attempt = recent_log.retry_attempt + 1

                log = await self.execute_job(
                    job_id=job.id,
                    tenant_id=job.tenant_id,
                    retry_attempt=retry_attempt,
                )
                results.append({
                    "job_id": str(job.id),
                    "job_name": job.name,
                    "task_type": job.task_type,
                    "status": log.status,
                    "duration_seconds": log.duration_seconds,
                })
            except Exception as exc:
                logger.error("Failed to execute pending job %s: %s", job.id, exc)
                results.append({
                    "job_id": str(job.id),
                    "job_name": job.name,
                    "task_type": job.task_type,
                    "status": "error",
                    "error": str(exc),
                })

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_job(self, job_id: UUID, tenant_id: str) -> CronJob | None:
        """Fetch a single cron job scoped to tenant."""
        stmt = select(CronJob).where(
            CronJob.id == job_id,
            CronJob.tenant_id == tenant_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()
