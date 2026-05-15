"""
Department Service.

Business logic for creating, querying, and managing departments.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.models.position import Position
from app.schemas.department import DepartmentCreate, DepartmentUpdate


class DepartmentService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_departments(
        self,
        *,
        tenant_id: str,
        parent_id: UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Department], int]:
        filters = [Department.tenant_id == tenant_id, Department.status == "active"]
        if parent_id is not None:
            filters.append(Department.parent_id == parent_id)

        count_stmt = select(func.count()).select_from(Department).where(*filters)
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = (
            select(Department)
            .where(*filters)
            .order_by(Department.sort_order.asc(), Department.name.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def get_by_id(self, dept_id: UUID, tenant_id: str) -> Department | None:
        stmt = select(Department).where(
            Department.id == dept_id,
            Department.tenant_id == tenant_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        data: DepartmentCreate,
        tenant_id: str,
        user_id: str,
    ) -> Department:
        tree_path = data.code
        if data.parent_id is not None:
            parent = await self.get_by_id(data.parent_id, tenant_id)
            if parent is None:
                raise ValueError("Parent department not found")
            tree_path = (
                f"{parent.tree_path}.{data.code}"
                if parent.tree_path and data.code
                else data.code
            )

        dept = Department(
            name=data.name,
            code=data.code,
            parent_id=data.parent_id,
            description=data.description,
            head_user_id=data.head_user_id,
            headcount_limit=data.headcount_limit,
            sort_order=data.sort_order,
            tree_path=tree_path,
            status="active",
            tenant_id=tenant_id,
        )
        self.db.add(dept)
        await self.db.flush()
        await self.db.refresh(dept)
        return dept

    async def update(
        self,
        dept_id: UUID,
        data: DepartmentUpdate,
        tenant_id: str,
    ) -> Department:
        dept = await self.get_by_id(dept_id, tenant_id)
        if dept is None:
            raise ValueError("Department not found")

        update_data = data.model_dump(exclude_unset=True)

        if "parent_id" in update_data or "code" in update_data:
            new_parent_id = update_data.get("parent_id", dept.parent_id)
            new_code = update_data.get("code", dept.code)
            if new_parent_id is not None:
                parent = await self.get_by_id(new_parent_id, tenant_id)
                if parent is None:
                    raise ValueError("Parent department not found")
                update_data["tree_path"] = (
                    f"{parent.tree_path}.{new_code}"
                    if parent.tree_path and new_code
                    else new_code
                )
            else:
                update_data["tree_path"] = new_code

        allowed_fields = {
            "name", "code", "parent_id", "description",
            "head_user_id", "headcount_limit", "status", "sort_order",
            "tree_path",
        }
        for key, value in update_data.items():
            if key in allowed_fields:
                setattr(dept, key, value)
        await self.db.flush()
        await self.db.refresh(dept)
        return dept

    async def soft_delete(self, dept_id: UUID, tenant_id: str) -> None:
        dept = await self.get_by_id(dept_id, tenant_id)
        if dept is None:
            raise ValueError("Department not found")

        active_positions_stmt = (
            select(func.count())
            .select_from(Position)
            .where(
                Position.department_id == dept_id,
                Position.status.in_(["draft", "open", "paused"]),
            )
        )
        active_count = (await self.db.execute(active_positions_stmt)).scalar_one()
        if active_count > 0:
            raise ValueError("Cannot delete department with active positions")

        dept.status = "inactive"
        await self.db.flush()
