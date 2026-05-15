"""
Position CRUD Router.

Provides endpoints for managing job positions in the recruitment pipeline.
"""

import math
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUserDep, DbSession, PaginationDep
from app.schemas.position import (
    PositionCreate,
    PositionListResponse,
    PositionResponse,
    PositionUpdate,
)
from app.services.position_service import PositionService

router = APIRouter()


@router.get("/", response_model=PositionListResponse, summary="List positions")
async def list_positions(
    db: DbSession,
    pagination: PaginationDep,
    current_user: CurrentUserDep,
    department_id: UUID | None = Query(None, description="Filter by department"),
    status: str | None = Query(None, description="Filter by status"),
    keyword: str | None = Query(None, description="Search in title"),
):
    service = PositionService(db)
    items, total = await service.list_positions(
        tenant_id=current_user.tenant_id,
        department_id=department_id,
        status=status,
        keyword=keyword,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    return PositionListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
    )


@router.post(
    "/",
    response_model=PositionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create position",
)
async def create_position(
    payload: PositionCreate,
    db: DbSession,
    current_user: CurrentUserDep,
):
    service = PositionService(db)
    try:
        position = await service.create(
            data=payload,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return position


@router.get(
    "/{position_id}", response_model=PositionResponse, summary="Get position"
)
async def get_position(
    position_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    service = PositionService(db)
    position = await service.get_by_id(position_id, current_user.tenant_id)
    if position is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Position not found"
        )
    return position


@router.patch(
    "/{position_id}", response_model=PositionResponse, summary="Update position"
)
async def update_position(
    position_id: UUID,
    payload: PositionUpdate,
    db: DbSession,
    current_user: CurrentUserDep,
):
    service = PositionService(db)
    try:
        position = await service.update(
            position_id=position_id,
            data=payload,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as exc:
        msg = str(exc)
        if "transition" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=msg
            )
        if "conflict" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=msg
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=msg
        )
    return position


@router.delete(
    "/{position_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete position",
)
async def delete_position(
    position_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    service = PositionService(db)
    try:
        await service.soft_delete(position_id, current_user.tenant_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
