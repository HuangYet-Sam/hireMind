"""
Resume Deduplication Engine (M2).

Provides two levels of duplicate detection:
  1. Exact match  — phone + email composite unique constraint per tenant.
  2. Fuzzy match  — feature-vector similarity over name + work experience,
                    using Jaccard-style hashing (no external deps).

Both methods are async and tenant-scoped.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume
from app.models.candidate import Candidate

logger = logging.getLogger("hiremind.resume_dedup")

# ---------------------------------------------------------------------------
# Feature-vector helpers (pure stdlib)
# ---------------------------------------------------------------------------

# Pinyin-ish normalisation: strip non-alpha, lowercase.
# In production this would be replaced by a proper pinyin library.
_NON_ALPHA = re.compile(r"[^a-zA-Z0-9]")


def _normalise_token(token: str) -> str:
    return _NON_ALPHA.sub("", token).lower()


def _tokenize_name(name: str) -> set[str]:
    """Split a name into character unigrams + bigrams for fuzzy comparison."""
    name = name.strip()
    if not name:
        return set()
    tokens: set[str] = set()
    # character unigrams
    for ch in name:
        tokens.add(ch.lower())
    # bigrams
    for i in range(len(name) - 1):
        tokens.add(name[i : i + 2].lower())
    # whitespace-split words normalised
    for word in name.split():
        t = _normalise_token(word)
        if t:
            tokens.add(t)
    return tokens


def _tokenize_work_experience(experiences: list[dict[str, Any]]) -> set[str]:
    """Build a bag-of-tokens from work experience entries.

    Tokens: company name n-grams + job-title keywords + normalised durations.
    """
    tokens: set[str] = set()
    for exp in experiences:
        company = str(exp.get("company", "")).strip()
        title = str(exp.get("title", "")).strip()
        if company:
            tokens.add(_normalise_token(company))
            for i in range(len(company) - 1):
                tokens.add(company[i : i + 2].lower())
        if title:
            tokens.add(_normalise_token(title))
            for word in title.split():
                t = _normalise_token(word)
                if t:
                    tokens.add(t)
        # year-level duration token (e.g. "2020-2023" → {"2020", "2023", "2020-2023"})
        for date_field in ("start_date", "end_date"):
            val = str(exp.get(date_field, ""))[:4]  # year only
            if val and val.isdigit():
                tokens.add(val)
        start = str(exp.get("start_date", ""))[:4]
        end = str(exp.get("end_date", ""))[:4]
        if start.isdigit() and end.isdigit():
            tokens.add(f"{start}-{end}")
    return tokens


def build_feature_vector(resume_data: dict[str, Any]) -> set[str]:
    """Build a combined feature set from name + work experience."""
    basic: dict[str, Any] = resume_data.get("basic_info", {}) or {}
    name = str(basic.get("name", ""))
    work: list[dict[str, Any]] = resume_data.get("work_experience", []) or []

    tokens = _tokenize_name(name)
    tokens |= _tokenize_work_experience(work)
    return tokens


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    """Jaccard index between two sets. 0.0–1.0."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def fingerprint_vector(vector: set[str]) -> str:
    """Deterministic hash of a feature vector for quick pre-filtering."""
    raw = "|".join(sorted(vector))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# ResumeDedupService
# ---------------------------------------------------------------------------

class ResumeDedupService:
    """
    Resume deduplication engine.

    Scoped to a single tenant.  Requires an ``AsyncSession`` for DB queries.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def check_duplicate(
        self,
        phone: str | None,
        email: str | None,
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        Exact-duplicate check via phone + email composite key.

        Returns::

            {
                "is_duplicate": bool,
                "match_type": "phone_email" | None,
                "existing_resume_id": str | None,
                "existing_candidate_id": str | None,
            }
        """
        if not phone and not email:
            return {
                "is_duplicate": False,
                "match_type": None,
                "existing_resume_id": None,
                "existing_candidate_id": None,
            }

        # Search candidates table for matching phone/email within tenant
        candidate = await self._find_candidate_by_contact(phone, email, tenant_id)
        if candidate is not None:
            resume = await self._find_resume_for_candidate(candidate.id, tenant_id)
            logger.info(
                "dedup_exact_match found candidate_id=%s phone=%s email=%s",
                candidate.id,
                bool(phone),
                bool(email),
            )
            return {
                "is_duplicate": True,
                "match_type": "phone_email",
                "existing_resume_id": str(resume.id) if resume else None,
                "existing_candidate_id": str(candidate.id),
            }

        return {
            "is_duplicate": False,
            "match_type": None,
            "existing_resume_id": None,
            "existing_candidate_id": None,
        }

    async def find_similar(
        self,
        resume_data: dict[str, Any],
        tenant_id: str,
        threshold: float = 0.8,
    ) -> list[dict[str, Any]]:
        """
        Similarity pre-check against existing resumes in the same tenant.

        Builds a feature vector from *resume_data* (name + work experience),
        then compares against all parsed resumes in the tenant using
        Jaccard similarity.

        Returns a list of dicts sorted by descending similarity::

            [{
                "resume_id": str,
                "candidate_id": str | None,
                "similarity": float,
                "name": str | None,
            }, ...]
        """
        query_vector = build_feature_vector(resume_data)
        if not query_vector:
            return []

        # Fetch all completed resumes with parsed_data for this tenant
        stmt = (
            select(Resume)
            .where(
                Resume.tenant_id == tenant_id,
                Resume.parse_status == "completed",
                Resume.parsed_data.isnot(None),
            )
        )
        result = await self.db.execute(stmt)
        resumes = list(result.scalars().all())

        matches: list[dict[str, Any]] = []
        for resume in resumes:
            parsed = resume.parsed_data or {}
            existing_vector = build_feature_vector(parsed)
            sim = jaccard_similarity(query_vector, existing_vector)

            if sim >= threshold:
                basic = parsed.get("basic_info", {}) or {}
                matches.append({
                    "resume_id": str(resume.id),
                    "candidate_id": str(resume.candidate_id) if resume.candidate_id else None,
                    "similarity": round(sim, 4),
                    "name": basic.get("name"),
                })

        # Sort by similarity descending
        matches.sort(key=lambda m: m["similarity"], reverse=True)

        logger.info(
            "dedup_similar tenant=%s threshold=%.2f candidates_scanned=%d matches=%d",
            tenant_id,
            threshold,
            len(resumes),
            len(matches),
        )
        return matches

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _find_candidate_by_contact(
        self,
        phone: str | None,
        email: str | None,
        tenant_id: str,
    ) -> Candidate | None:
        """Find a candidate matching phone OR email within the tenant."""
        conditions = [Candidate.tenant_id == tenant_id]
        or_parts = []
        if phone:
            phone_clean = re.sub(r"\D", "", phone)
            if phone_clean:
                or_parts.append(Candidate.phone.ilike(f"%{phone_clean[-11:]}"))
        if email:
            or_parts.append(Candidate.email.ilike(email.strip()))

        if not or_parts:
            return None

        from sqlalchemy import or_
        stmt = select(Candidate).where(*conditions, or_(*or_parts)).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_resume_for_candidate(
        self,
        candidate_id: Any,
        tenant_id: str,
    ) -> Resume | None:
        """Find the latest resume for a candidate in the tenant."""
        stmt = (
            select(Resume)
            .where(
                Resume.candidate_id == candidate_id,
                Resume.tenant_id == tenant_id,
            )
            .order_by(Resume.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
