"""
HR Resume Agent Tool.

Exposes resume query / parse / dedup capabilities as an Agent Tool
via the ``@AiCapability`` decorator.

Registered capabilities:
  - ``hr_resume_query``      — query parsed resume data
  - ``hr_resume_parse``      — trigger AI parsing on an uploaded resume
  - ``hr_resume_dedup``      — check for duplicates / similar resumes
  - ``hr_resume_credibility`` — score resume credibility
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.decorators.ai_capability import AiCapability

logger = logging.getLogger("hiremind.tools.hr_resume")


# ---------------------------------------------------------------------------
# Tool: HR Resume Query
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_resume_query",
    name="HR Resume Query",
    endpoint="/api/v1/resumes/{resume_id}",
    method="GET",
    tool_name="hr_resume_query",
    permissions=["resume:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_resume_query_v1",
    description="Query parsed resume data by resume ID",
    request_model="ResumeQueryRequest",
    response_model="ResumeQueryResult",
    rate_limit="100/minute",
    data_classification="L3",
    audit_level="standard",
    tags=["hr", "resume", "query"],
    timeout=10.0,
)
async def hr_resume_query(
    resume_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Query a single resume's parsed data.

    Args:
        resume_id: UUID of the resume.
        tenant_id: Tenant scope identifier.

    Returns:
        Dict containing resume metadata and parsed_data.
    """
    from app.dependencies import get_db
    from app.services.resume_service import ResumeService

    async for session in get_db():
        svc = ResumeService(session)
        resume = await svc.get_by_id(UUID(resume_id), tenant_id)
        if resume is None:
            return {"error": "Resume not found", "resume_id": resume_id}

        return {
            "resume_id": str(resume.id),
            "filename": resume.original_filename,
            "parse_status": resume.parse_status,
            "parsed_data": resume.parsed_data,
            "file_type": resume.file_type,
            "source": resume.source,
            "created_at": str(resume.created_at) if resume.created_at else None,
        }

    # Should never reach here
    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Resume Parse
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_resume_parse",
    name="HR Resume Parse",
    endpoint="/api/v1/resumes/{resume_id}/parse",
    method="POST",
    tool_name="hr_resume_parse",
    permissions=["resume:parse"],
    llm_model="gpt-4o-mini",
    fallback_model="gpt-3.5-turbo",
    prompt_version="v2",
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_resume_parse_v2",
    description="Trigger AI-powered 7-category resume parsing",
    request_model="ResumeParseRequest",
    response_model="SmartResumeParseResult",
    rate_limit="20/minute",
    data_classification="L3",
    audit_level="detailed",
    tags=["hr", "resume", "parse", "ai"],
    timeout=45.0,
)
async def hr_resume_parse(
    resume_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Parse a resume using the 7-category AI extraction engine.

    Args:
        resume_id: UUID of the resume to parse.
        tenant_id: Tenant scope identifier.

    Returns:
        Dict with parse_status and parsed_data.
    """
    from app.dependencies import get_db
    from app.services.resume_service import ResumeService

    async for session in get_db():
        svc = ResumeService(session)
        result = await svc.parse_resume(UUID(resume_id), tenant_id)
        return result

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Resume Dedup
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_resume_dedup",
    name="HR Resume Dedup",
    endpoint="/api/v1/resumes/dedup-check",
    method="POST",
    tool_name="hr_resume_dedup",
    permissions=["resume:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_resume_dedup_v1",
    description="Check for duplicate or similar resumes before ingestion",
    request_model="ResumeDedupRequest",
    response_model="ResumeDedupResult",
    rate_limit="30/minute",
    data_classification="L3",
    audit_level="standard",
    tags=["hr", "resume", "dedup"],
    timeout=15.0,
)
async def hr_resume_dedup(
    *,
    phone: str | None = None,
    email: str | None = None,
    resume_data: dict[str, Any] | None = None,
    tenant_id: str = "default",
    similarity_threshold: float = 0.8,
) -> dict[str, Any]:
    """
    Check for exact duplicates (phone+email) and similar resumes.

    Args:
        phone: Candidate phone number.
        email: Candidate email address.
        resume_data: Structured resume data for similarity comparison.
        tenant_id: Tenant scope.
        similarity_threshold: Jaccard threshold for fuzzy matching (0–1).

    Returns:
        Dict with duplicate_check and similar_results.
    """
    from app.dependencies import get_db
    from app.services.resume_dedup import ResumeDedupService

    async for session in get_db():
        dedup = ResumeDedupService(session)

        # Exact duplicate check
        dup_result = await dedup.check_duplicate(phone, email, tenant_id)

        # Fuzzy similarity check (if resume_data provided)
        similar: list[dict[str, Any]] = []
        if resume_data:
            similar = await dedup.find_similar(
                resume_data, tenant_id, threshold=similarity_threshold
            )

        return {
            "duplicate_check": dup_result,
            "similar_results": similar,
        }

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Resume Credibility
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_resume_credibility",
    name="HR Resume Credibility Scoring",
    endpoint="/api/v1/resumes/{resume_id}/credibility",
    method="POST",
    tool_name="hr_resume_credibility",
    permissions=["resume:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_resume_credibility_v1",
    description="Score resume credibility with internal consistency checks",
    request_model="ResumeCredibilityRequest",
    response_model="ResumeCredibilityResult",
    rate_limit="30/minute",
    data_classification="L3",
    audit_level="standard",
    tags=["hr", "resume", "credibility"],
    timeout=10.0,
)
async def hr_resume_credibility(
    resume_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Score resume credibility based on internal consistency checks.

    Args:
        resume_data: Structured resume data (output of parser).

    Returns:
        Dict with score, checks, and flagged_fields.
    """
    from app.services.resume_credibility import resume_credibility_service

    result = await resume_credibility_service.score_credibility(resume_data)
    return result
