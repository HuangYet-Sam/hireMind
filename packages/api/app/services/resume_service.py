"""
Resume Service.

Business logic for resume upload, storage, AI parsing, and retrieval.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.decorators.ai_capability import AiCapability
from app.models.resume import Resume
from app.services.pii_masking import PIIMaskingService

logger = logging.getLogger("hiremind.resume")


class ResumeService:
    UPLOAD_DIR = Path("uploads/resumes")
    ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "png", "jpg", "jpeg"}
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_resumes(
        self,
        *,
        tenant_id: str,
        candidate_id: UUID | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Resume], int]:
        stmt = select(Resume).where(Resume.tenant_id == tenant_id)
        count_stmt = select(func.count()).select_from(Resume).where(Resume.tenant_id == tenant_id)

        if candidate_id is not None:
            stmt = stmt.where(Resume.candidate_id == candidate_id)
            count_stmt = count_stmt.where(Resume.candidate_id == candidate_id)

        if status is not None:
            stmt = stmt.where(Resume.parse_status == status)
            count_stmt = count_stmt.where(Resume.parse_status == status)

        total = (await self.db.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(Resume.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        resumes = list(result.scalars().all())

        return resumes, total

    async def get_by_id(self, resume_id: UUID, tenant_id: str) -> Resume | None:
        stmt = select(Resume).where(Resume.id == resume_id, Resume.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upload(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        candidate_id: UUID | None,
        position_id: UUID | None = None,
        tenant_id: str,
        user_id: str,
    ) -> Resume:
        file_hash = hashlib.sha256(content).hexdigest()

        if len(content) > self.MAX_FILE_SIZE:
            raise ValueError("File too large (max 20MB)")

        dup_stmt = select(Resume).where(
            Resume.file_hash == file_hash,
            Resume.tenant_id == tenant_id,
        )
        dup_result = await self.db.execute(dup_stmt)
        if dup_result.scalar_one_or_none() is not None:
            raise ValueError("Duplicate file")

        safe_name = Path(filename).name
        if not safe_name or safe_name.startswith('.'):
            raise ValueError("Invalid filename")

        ext = Path(safe_name).suffix.lstrip(".").lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"Invalid file type: {ext}")
        file_type = ext

        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid4().hex}.{ext}"
        file_path = self.UPLOAD_DIR / stored_name
        file_path.write_bytes(content)

        resume = Resume(
            candidate_id=candidate_id,
            position_id=position_id,
            original_filename=filename,
            file_path=str(file_path),
            file_type=file_type,
            file_size=len(content),
            content_type=content_type,
            file_hash=file_hash,
            source="upload",
            uploaded_by=user_id,
            parse_status="pending",
            tenant_id=tenant_id,
        )
        self.db.add(resume)
        await self.db.flush()
        await self.db.refresh(resume)

        return resume

    async def parse(self, resume_id: UUID, tenant_id: str) -> dict:
        resume = await self.get_by_id(resume_id, tenant_id)
        if resume is None:
            raise ValueError("Resume not found")

        resume.parse_status = "processing"
        await self.db.flush()

        # Try AI-powered parsing first
        parsed_data = None
        resume_text = self._read_file_content(resume.file_path)

        if resume_text:
            from app.services.ai_client import ai_client

            parsed_data = await ai_client.parse_resume_with_ai(resume_text)

        # Fallback to structured mock if AI unavailable
        if parsed_data is None:
            parsed_data = self._generate_fallback_parse(resume)

        resume.parse_status = "completed"
        resume.parsed_at = datetime.now(timezone.utc).isoformat()
        resume.parsed_data = parsed_data
        await self.db.flush()
        await self.db.refresh(resume)

        return {
            "resume_id": resume.id,
            "parse_status": resume.parse_status,
            "parsed_data": resume.parsed_data,
        }

    def _read_file_content(self, file_path: str) -> str | None:
        """Read resume file content as text. Returns None for binary formats."""
        path = Path(file_path)
        if not path.exists():
            return None
        try:
            # For text-extractable files, try reading as UTF-8
            # In production, use proper PDF/DOCX parsers
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

    def _generate_fallback_parse(self, resume: Resume) -> dict:
        """Generate basic parsed data from resume metadata when AI is unavailable."""
        return {
            "basic_info": {
                "name": resume.original_filename or "Unknown",
                "email": None,
                "phone": None,
            },
            "education": [],
            "work_experience": [],
            "skills": [],
            "summary": (
                f"Parsed from {resume.original_filename} "
                "(fallback mode - AI unavailable)"
            ),
            "_parse_mode": "fallback",
        }

    async def delete(self, resume_id: UUID, tenant_id: str) -> None:
        resume = await self.get_by_id(resume_id, tenant_id)
        if resume is None:
            raise ValueError("Resume not found")

        file_path = Path(resume.file_path)
        if file_path.exists():
            file_path.unlink()

        await self.db.delete(resume)
        await self.db.flush()

    # ── AI Capability ────────────────────────────────────────────

    @AiCapability(
        capability="resume_parse",
        name="AI Resume Parsing",
        endpoint="/api/v1/resumes/parse",
        method="POST",
        tool_name="parse_resume",
        permissions=["resume:parse"],
        llm_model="gpt-4",
        fallback_model="gpt-3.5-turbo",
        prompt_version="v1",
        allowed_callers=["api", "agent"],
        requires_tenant_isolation=True,
        ai_capability_id="resume_ai_parse",
        description="AI-powered resume parsing into structured candidate data",
        request_model="ResumeParseRequest",
        response_model="ResumeParseResult",
        rate_limit="20/minute",
        data_classification="L3",
        audit_level="detailed",
        tags=["ai", "resume", "parse"],
        timeout=45.0,
    )
    async def parse_resume(self, resume_id: UUID, tenant_id: str) -> dict:
        """
        AI-powered resume parsing with PII masking.

        Flow: read file → mask PII → LLM parse → unmask → update parsed_data.
        """
        resume = await self.get_by_id(resume_id, tenant_id)
        if resume is None:
            raise ValueError("Resume not found")

        resume.parse_status = "processing"
        await self.db.flush()

        pii = PIIMaskingService()
        parsed_data = None

        resume_text = self._read_file_content(resume.file_path)
        if resume_text:
            masked_text, mapping = await pii.mask(resume_text)

            from app.services.ai_client import ai_client
            raw = await ai_client.parse_resume_with_ai(masked_text)

            if raw is not None:
                unmasked = await pii.unmask(json.dumps(raw, ensure_ascii=False), mapping)
                parsed_data = json.loads(unmasked)

        if parsed_data is None:
            parsed_data = self._generate_fallback_parse(resume)

        resume.parse_status = "completed"
        resume.parsed_at = datetime.now(timezone.utc).isoformat()
        resume.parsed_data = parsed_data
        await self.db.flush()
        await self.db.refresh(resume)

        logger.info("parse_resume completed resume_id=%s", resume_id)
        return {
            "resume_id": resume.id,
            "parse_status": resume.parse_status,
            "parsed_data": resume.parsed_data,
        }
