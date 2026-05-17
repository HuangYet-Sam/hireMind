"""
AI Task Service.

Business logic for creating, querying, cancelling, and retrying AI tasks.
"""

import math
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_task import AiTask, TaskStatus
from app.schemas.ai_task import AiTaskCreate


class AiTaskService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_tasks(
        self,
        *,
        tenant_id: str,
        status: TaskStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AiTask], int]:
        """Return paginated tasks for a tenant, optionally filtered by status."""
        filters = [AiTask.tenant_id == tenant_id]
        if status is not None:
            filters.append(AiTask.status == status)

        count_stmt = select(func.count()).select_from(AiTask).where(*filters)
        total = (await self.db.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        stmt = (
            select(AiTask)
            .where(*filters)
            .order_by(AiTask.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def get_task(self, task_id: UUID, tenant_id: str) -> AiTask | None:
        """Get a single task by ID scoped to tenant."""
        stmt = select(AiTask).where(
            AiTask.id == task_id,
            AiTask.tenant_id == tenant_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create_task(
        self,
        tenant_id: str,
        data: AiTaskCreate,
        user_id: str | None = None,
    ) -> AiTask:
        """Create a new AI task in pending status."""
        task = AiTask(
            tenant_id=tenant_id,
            task_type=data.task_type,
            status=TaskStatus.pending,
            input_data=data.input_data,
            created_by=user_id,
        )
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def cancel_task(self, task_id: UUID, tenant_id: str) -> AiTask:
        """Cancel a pending or running task."""
        task = await self.get_task(task_id, tenant_id)
        if task is None:
            raise ValueError("Task not found")
        if task.status not in (TaskStatus.pending, TaskStatus.running):
            raise ValueError(f"Cannot cancel task in '{task.status.value}' state")

        task.status = TaskStatus.cancelled
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def retry_task(self, task_id: UUID, tenant_id: str) -> AiTask:
        """Retry a failed or cancelled task by resetting it to pending."""
        task = await self.get_task(task_id, tenant_id)
        if task is None:
            raise ValueError("Task not found")
        if task.status not in (TaskStatus.failed, TaskStatus.cancelled):
            raise ValueError(f"Cannot retry task in '{task.status.value}' state")

        task.status = TaskStatus.pending
        task.error_message = None
        task.output_data = None
        await self.db.flush()
        await self.db.refresh(task)
        return task
