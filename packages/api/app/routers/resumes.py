"""
Resume Router.

Endpoints for uploading, parsing, and managing candidate resumes (简历).
"""

from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.dependencies import CurrentUserDep, DbSession, PaginationDep
from app.schemas.resume import (
    ResumeListResponse,
    ResumeParseResult,
    ResumeResponse,
)

router = APIRouter()


@router.get("/", response_model=ResumeListResponse, summary="List resumes")
async def list_resumes(
    db: DbSession,
    pagination: PaginationDep,
    current_user: CurrentUserDep,
    candidate_id: UUID | None = Query(None, description="Filter by candidate"),
    status: str | None = Query(None, description="Filter by parse status"),
):
    """Return a paginated list of uploaded resumes."""
    return ResumeListResponse(
        items=[],
        total=0,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload resume",
)
async def upload_resume(
    file: UploadFile = File(..., description="Resume file (PDF/DOCX)"),
    candidate_id: UUID | None = None,
    db: DbSession = None,
    current_user: CurrentUserDep = None,
):
    """Upload a resume file (PDF/DOCX), store in MinIO, and trigger AI parsing."""
    # TODO: delegate to resume_service.upload_and_parse(...)
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post(
    "/{resume_id}/parse",
    response_model=ResumeParseResult,
    summary="Parse / re-parse resume",
)
async def parse_resume(
    resume_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Trigger AI-powered resume parsing (or re-parse)."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{resume_id}", response_model=ResumeResponse, summary="Get resume")
async def get_resume(
    resume_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Retrieve a single resume by ID."""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete resume",
)
async def delete_resume(
    resume_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Delete a resume and its stored file."""
    raise HTTPException(status_code=501, detail="Not implemented yet")
