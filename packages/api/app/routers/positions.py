"""
Position CRUD Router.

Provides endpoints for managing job positions (岗位) in the recruitment pipeline.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUserDep, DbSession, PaginationDep
from app.schemas.position import (
    PositionCreate,
    PositionListResponse,
    PositionResponse,
    PositionUpdate,
)

router = APIRouter()


@router.get("/", response_model=PositionListResponse, summary="List positions")
async def list_positions(
    db: DbSession,
    pagination: PaginationDep,
    current_user: CurrentUserDep,
    department_id: UUID | None = Query(None, description="Filter by department"),
    status: str | None = Query(None, description="Filter by status (open/closed/draft)"),
    keyword: str | None = Query(None, description="Search in title / description"),
):
    """Return a paginated list of positions with optional filters."""
    # TODO: delegate to position_service.list_positions(...)
    return PositionListResponse(
        items=[],
        total=0,
        page=pagination.page,
        page_size=pagination.page_size,
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
    """Create a new job position."""
    # TODO: delegate to position_service.create(...)
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{position_id}", response_model=PositionResponse, summary="Get position")
async def get_position(
    position_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Retrieve a single position by ID."""
    # TODO: delegate to position_service.get(...)
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.put("/{position_id}", response_model=PositionResponse, summary="Update position")
async def update_position(
    position_id: UUID,
    payload: PositionUpdate,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Update an existing position."""
    # TODO: delegate to position_service.update(...)
    raise HTTPException(status_code=501, detail="Not implemented yet")


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
    """Soft-delete a position (marks as 'closed')."""
    # TODO: delegate to position_service.delete(...)
    raise HTTPException(status_code=501, detail="Not implemented yet")
