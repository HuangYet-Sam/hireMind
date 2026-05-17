"""
Department / Organization Structure Router.

Endpoints for managing departments and organizational hierarchy.
"""

import math
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUserDep, DbSession
from app.schemas.department import (
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentTreeResponse,
    DepartmentTreeNode,
    DepartmentUpdate,
)
from app.services.department_service import DepartmentService

router = APIRouter()


@router.get("/tree", response_model=DepartmentTreeResponse, summary="Get department tree")
async def get_department_tree(
    db: DbSession,
    current_user: CurrentUserDep,
):
    service = DepartmentService(db)
    items, _ = await service.list_departments(
        tenant_id=current_user.tenant_id,
        offset=0,
        limit=1000,
    )

    node_map: dict[UUID, DepartmentTreeNode] = {}
    for dept in items:
        node_map[dept.id] = DepartmentTreeNode(
            id=dept.id,
            name=dept.name,
            code=dept.code,
            parent_id=dept.parent_id,
            description=dept.description,
            head_user_id=dept.head_user_id,
            headcount_limit=dept.headcount_limit,
            current_headcount=dept.current_headcount,
            status=dept.status,
            sort_order=dept.sort_order,
            tree_path=dept.tree_path,
            manager_name=dept.manager_name,
            created_at=dept.created_at,
            updated_at=dept.updated_at,
            children=[],
        )

    roots: list[DepartmentTreeNode] = []
    for node in node_map.values():
        if node.parent_id and node.parent_id in node_map:
            node_map[node.parent_id].children.append(node)
        else:
            roots.append(node)

    return DepartmentTreeResponse(tree=roots)


@router.get("", response_model=DepartmentListResponse, summary="List departments")
async def list_departments(
    db: DbSession,
    current_user: CurrentUserDep,
    parent_id: UUID | None = Query(None, description="Filter by parent department"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    service = DepartmentService(db)
    offset = (page - 1) * page_size
    items, total = await service.list_departments(
        tenant_id=current_user.tenant_id,
        parent_id=parent_id,
        offset=offset,
        limit=page_size,
    )
    pages = math.ceil(total / page_size) if total > 0 else 0
    return DepartmentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post(
    "/",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create department",
)
async def create_department(
    payload: DepartmentCreate,
    db: DbSession,
    current_user: CurrentUserDep,
):
    service = DepartmentService(db)
    try:
        dept = await service.create(
            data=payload,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return dept


@router.get(
    "/{department_id}", response_model=DepartmentResponse, summary="Get department"
)
async def get_department(
    department_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    service = DepartmentService(db)
    dept = await service.get_by_id(department_id, current_user.tenant_id)
    if dept is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
        )
    return dept


@router.patch(
    "/{department_id}", response_model=DepartmentResponse, summary="Update department"
)
async def update_department(
    department_id: UUID,
    payload: DepartmentUpdate,
    db: DbSession,
    current_user: CurrentUserDep,
):
    service = DepartmentService(db)
    try:
        dept = await service.update(
            dept_id=department_id,
            data=payload,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        msg = str(exc)
        status_code = (
            status.HTTP_409_CONFLICT
            if "conflict" in msg.lower()
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=status_code, detail=msg)
    return dept


@router.delete(
    "/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete department",
)
async def delete_department(
    department_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    service = DepartmentService(db)
    try:
        await service.soft_delete(department_id, current_user.tenant_id)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=msg
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=msg
        )
