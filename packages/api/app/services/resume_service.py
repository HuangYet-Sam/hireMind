"""
Resume Service.

Business logic for resume upload, storage, AI parsing, and retrieval.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class ResumeService:
    """Handles resume upload, MinIO storage, and AI-powered parsing."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        candidate_id: UUID | None,
        tenant_id: str,
        user_id: str,
    ) -> dict:
        """
        Upload a resume file to MinIO and create a DB record.

        Args:
            filename: Original file name.
            content: Raw file bytes.
            content_type: MIME type (application/pdf, etc.).
            candidate_id: Optional candidate to link.
            tenant_id: Owning tenant.
            user_id: Uploader.

        Returns:
            The created resume record dict.
        """
        # TODO: upload to MinIO, create DB record, trigger async parse
        raise NotImplementedError

    async def parse(self, resume_id: UUID, tenant_id: str) -> dict:
        """
        Trigger AI parsing of a resume via Hermes Agent.

        Extracts: personal info, education, work experience, skills, certifications.

        Returns:
            Parsed result dict.
        """
        # TODO: call Hermes Agent for AI parsing
        raise NotImplementedError

    async def get_by_id(self, resume_id: UUID, tenant_id: str) -> dict | None:
        """Fetch a single resume record."""
        return None

    async def list_resumes(
        self,
        *,
        tenant_id: str,
        candidate_id: UUID | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list, int]:
        """Return paginated list of resumes."""
        return [], 0

    async def delete(self, resume_id: UUID, tenant_id: str) -> None:
        """Delete resume record and remove file from MinIO."""
        raise NotImplementedError
