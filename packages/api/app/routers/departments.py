"""
Department / Organization Structure Router.

Endpoints for managing departments (部门) and organizational hierarchy.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUserDep, DbSession
from app.schemas.department import (
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdate,
)

router = APIRouter()


@router.get("/", response_model=DepartmentListResponse, summary="List departments")
async def list_departments(
    db: DbSession,
    current_user: CurrentUserDep,
    parent_id: UUID | None = None,
):
    """Return the list of departments (optionally filtered by parent)."""
    return DepartmentListResponse(items=[], total=0)


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
    """Create a new department."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{department_id}", response_model=DepartmentResponse, summary="Get department")
async def get_department(
    department_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Retrieve a single department by ID."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.put("/{department_id}", response_model=DepartmentResponse, summary="Update department")
async def update_department(
    department_id: UUID,
    payload: DepartmentUpdate,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Update department information."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


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
    """Soft-delete a department (only if it has no active positions)."""
    raise HTTPException(status_code=501, detail="Not implemented yet")
