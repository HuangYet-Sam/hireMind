"""
Resume Router.

Endpoints for uploading, parsing, and managing candidate resumes.
"""

import math
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.dependencies import CurrentUserDep, DbSession, PaginationDep
from app.schemas.resume import (
    ResumeListResponse,
    ResumeParseResult,
    ResumeResponse,
)
from app.services.resume_service import ResumeService

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
    service = ResumeService(db)
    resumes, total = await service.list_resumes(
        tenant_id=current_user.tenant_id,
        candidate_id=candidate_id,
        status=status,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    return ResumeListResponse(
        items=resumes,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
    )


@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload resume",
)
async def upload_resume(
    db: DbSession,
    current_user: CurrentUserDep,
    file: UploadFile = File(..., description="Resume file (PDF/DOCX)"),
    candidate_id: UUID | None = Form(None),
    position_id: UUID | None = Form(None),
    source: str = Form("upload"),
):
    """Upload a resume file and create a pending parse record."""
    content = await file.read()
    service = ResumeService(db)
    try:
        resume = await service.upload(
            filename=file.filename,
            content=content,
            content_type=file.content_type,
            candidate_id=candidate_id,
            position_id=position_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
        )
    except ValueError as e:
        if "Duplicate file" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        raise
    return resume


@router.get("/{resume_id}", response_model=ResumeResponse, summary="Get resume")
async def get_resume(
    resume_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Retrieve a single resume by ID."""
    service = ResumeService(db)
    resume = await service.get_by_id(resume_id, current_user.tenant_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


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
    service = ResumeService(db)
    try:
        result = await service.parse(resume_id, current_user.tenant_id)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Resume not found")
        raise
    return result


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
    service = ResumeService(db)
    try:
        await service.delete(resume_id, current_user.tenant_id)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Resume not found")
        raise
