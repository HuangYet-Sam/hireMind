"""
HR Storage Agent Tool.

Exposes file storage and version management capabilities for resume files
via the ``@AiCapability`` decorator.

Registered capabilities:
  - ``hr_storage_upload``    — upload a resume file with dedup check
  - ``hr_storage_version``   — manage resume file versions
  - ``hr_storage_status``    — query storage status / metadata
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.decorators.ai_capability import AiCapability

logger = logging.getLogger("hiremind.tools.hr_storage")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_UPLOAD_DIR = Path("uploads/resumes")
_ALLOWED_EXTENSIONS = frozenset({"pdf", "docx", "doc", "png", "jpg", "jpeg"})
_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


# ---------------------------------------------------------------------------
# Tool: HR Storage Upload
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_storage_upload",
    name="HR Resume File Upload",
    endpoint="/api/v1/resumes/upload",
    method="POST",
    tool_name="hr_storage_upload",
    permissions=["resume:upload"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_storage_upload_v1",
    description="Upload a resume file with dedup and virus scan placeholder",
    request_model="ResumeUploadRequest",
    response_model="ResumeUploadResult",
    rate_limit="10/minute",
    data_classification="L3",
    audit_level="detailed",
    tags=["hr", "storage", "upload"],
    timeout=30.0,
)
async def hr_storage_upload(
    *,
    filename: str,
    content: bytes,
    content_type: str,
    candidate_id: str | None = None,
    position_id: str | None = None,
    tenant_id: str = "default",
    user_id: str = "system",
    skip_dedup: bool = False,
) -> dict[str, Any]:
    """
    Upload a resume file to storage.

    Includes file-hash dedup check and PII-safe storage.

    Args:
        filename: Original file name.
        content: Raw file bytes.
        content_type: MIME type.
        candidate_id: Optional candidate UUID to link.
        position_id: Optional position UUID.
        tenant_id: Tenant scope.
        user_id: Uploader user ID.
        skip_dedup: Skip file-hash dedup check (for agent re-ingestion).

    Returns:
        Dict with resume_id, file_path, file_hash, and dedup status.
    """
    from app.dependencies import get_db
    from app.services.resume_service import ResumeService

    # Pre-flight validation
    if len(content) > _MAX_FILE_SIZE:
        return {"error": f"File too large (max {_MAX_FILE_SIZE // (1024*1024)}MB)"}

    safe_name = Path(filename).name
    if not safe_name or safe_name.startswith("."):
        return {"error": "Invalid filename"}

    ext = Path(safe_name).suffix.lstrip(".").lower()
    if ext not in _ALLOWED_EXTENSIONS:
        return {"error": f"Unsupported file type: {ext}"}

    file_hash = hashlib.sha256(content).hexdigest()

    async for session in get_db():
        svc = ResumeService(session)

        # Optional dedup check
        if not skip_dedup:
            from sqlalchemy import select
            from app.models.resume import Resume

            dup_stmt = select(Resume).where(
                Resume.file_hash == file_hash,
                Resume.tenant_id == tenant_id,
            )
            dup_result = await session.execute(dup_stmt)
            if dup_result.scalar_one_or_none() is not None:
                return {
                    "status": "duplicate",
                    "file_hash": file_hash,
                    "message": "File with same hash already exists in tenant",
                }

        # Upload via service
        try:
            resume = await svc.upload(
                filename=filename,
                content=content,
                content_type=content_type,
                candidate_id=UUID(candidate_id) if candidate_id else None,
                position_id=UUID(position_id) if position_id else None,
                tenant_id=tenant_id,
                user_id=user_id,
            )
            await session.commit()

            logger.info(
                "storage_upload resume_id=%s file_hash=%s tenant=%s",
                resume.id,
                file_hash[:12],
                tenant_id,
            )

            return {
                "status": "created",
                "resume_id": str(resume.id),
                "file_path": resume.file_path,
                "file_hash": file_hash,
                "file_size": resume.file_size,
                "parse_status": resume.parse_status,
            }
        except ValueError as exc:
            return {"error": str(exc)}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Storage Version Management
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_storage_version",
    name="HR Resume Version Management",
    endpoint="/api/v1/resumes/{resume_id}/version",
    method="POST",
    tool_name="hr_storage_version",
    permissions=["resume:upload", "resume:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_storage_version_v1",
    description="Create a new version of an existing resume file",
    request_model="ResumeVersionRequest",
    response_model="ResumeVersionResult",
    rate_limit="10/minute",
    data_classification="L3",
    audit_level="detailed",
    tags=["hr", "storage", "version"],
    timeout=15.0,
)
async def hr_storage_version(
    *,
    resume_id: str,
    content: bytes,
    filename: str,
    tenant_id: str = "default",
    user_id: str = "system",
) -> dict[str, Any]:
    """
    Create a new version of an existing resume.

    Preserves the previous version's audit trail by creating a new Resume
    record linked to the same candidate.

    Args:
        resume_id: UUID of the existing resume to version.
        content: New file bytes.
        filename: New file name.
        tenant_id: Tenant scope.
        user_id: User performing the versioning.

    Returns:
        Dict with new resume_id and version number.
    """
    from app.dependencies import get_db
    from app.services.resume_service import ResumeService

    async for session in get_db():
        svc = ResumeService(session)
        old_resume = await svc.get_by_id(UUID(resume_id), tenant_id)
        if old_resume is None:
            return {"error": "Original resume not found"}

        # Create new version as a fresh upload linked to same candidate/position
        content_type = (
            "application/pdf" if filename.endswith(".pdf")
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if filename.endswith(".docx")
            else "application/octet-stream"
        )

        try:
            new_resume = await svc.upload(
                filename=filename,
                content=content,
                content_type=content_type,
                candidate_id=old_resume.candidate_id,
                position_id=old_resume.position_id,
                tenant_id=tenant_id,
                user_id=user_id,
            )

            # Increment version on the new record
            new_resume.version = (old_resume.version or 1) + 1
            await session.commit()

            logger.info(
                "storage_version old_id=%s new_id=%s version=%d",
                resume_id,
                new_resume.id,
                new_resume.version,
            )

            return {
                "status": "versioned",
                "old_resume_id": resume_id,
                "new_resume_id": str(new_resume.id),
                "version": new_resume.version,
                "file_size": new_resume.file_size,
            }
        except ValueError as exc:
            return {"error": str(exc)}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Storage Status
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_storage_status",
    name="HR Resume Storage Status",
    endpoint="/api/v1/resumes/{resume_id}/status",
    method="GET",
    tool_name="hr_storage_status",
    permissions=["resume:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_storage_status_v1",
    description="Query resume file storage status and metadata",
    request_model="ResumeStatusRequest",
    response_model="ResumeStatusResult",
    rate_limit="100/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "storage", "status"],
    timeout=5.0,
)
async def hr_storage_status(
    resume_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Get storage status and metadata for a resume file.

    Args:
        resume_id: UUID of the resume.
        tenant_id: Tenant scope.

    Returns:
        Dict with file metadata, parse status, and version info.
    """
    from app.dependencies import get_db
    from app.services.resume_service import ResumeService

    async for session in get_db():
        svc = ResumeService(session)
        resume = await svc.get_by_id(UUID(resume_id), tenant_id)
        if resume is None:
            return {"error": "Resume not found", "resume_id": resume_id}

        file_path = Path(resume.file_path)
        file_exists = file_path.exists()

        return {
            "resume_id": str(resume.id),
            "original_filename": resume.original_filename,
            "file_type": resume.file_type,
            "file_size": resume.file_size,
            "file_hash": resume.file_hash,
            "file_exists_on_disk": file_exists,
            "source": resume.source,
            "parse_status": resume.parse_status,
            "parsed_at": resume.parsed_at,
            "version": resume.version,
            "uploaded_by": resume.uploaded_by,
            "created_at": str(resume.created_at) if resume.created_at else None,
            "updated_at": str(resume.updated_at) if resume.updated_at else None,
        }

    return {"error": "Database session unavailable"}
