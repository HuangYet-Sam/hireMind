"""
SmartResume Parser — 7-category structured extraction engine.

Reads resume text, masks PII, sends to LLM via AIClient with a
7-category extraction prompt, and returns structured JSON.

Categories:
  1. basic_info      — name, phone, email, gender, age, birthday, location, id_number
  2. work_experience — company, title, department, start/end_date, responsibilities, achievements
  3. education       — school, degree, major, start/end_date, gpa
  4. skills          — name, proficiency, years_of_experience
  5. certifications  — name, issuer, date, expiry_date, credential_id
  6. languages       — language, proficiency, certification
  7. projects        — name, role, start/end_date, description, technologies, url
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

import yaml

from app.decorators.ai_capability import AiCapability
from app.services.pii_masking import PIIMaskingService

logger = logging.getLogger("hiremind.smart_resume_parser")

# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

_PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / "resume_extraction.yaml"


def _load_prompt_template() -> dict[str, Any]:
    if not _PROMPT_PATH.exists():
        raise FileNotFoundError(f"Prompt template not found: {_PROMPT_PATH}")
    with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


_PROMPT_CACHE: dict[str, Any] | None = None


def _get_prompt_template() -> dict[str, Any]:
    global _PROMPT_CACHE
    if _PROMPT_CACHE is None:
        _PROMPT_CACHE = _load_prompt_template()
    return _PROMPT_CACHE


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

def _build_system_prompt(template: dict[str, Any]) -> str:
    system = template["system_prompt"]
    schema_desc = template["schema"]
    example = template["output_format"]["example"]

    category_details: list[str] = []
    for cat_name, cat_def in schema_desc.items():
        fields_desc = []
        for fname, finfo in cat_def["fields"].items():
            fields_desc.append(f"    {fname} ({finfo['type']}): {finfo['description']}")
        prefix = f"  (array) {cat_name}" if cat_def.get("is_array") else f"  {cat_name}"
        category_details.append(f"{prefix} — {cat_def['description']}\n" + "\n".join(fields_desc))

    return (
        f"{system}\n\n"
        f"### Categories & Fields\n\n"
        + "\n\n".join(category_details)
        + f"\n\n### Output Example\n```json\n{example}\n```\n"
        + "\nReturn valid JSON only. No markdown fences."
    )


# ---------------------------------------------------------------------------
# SmartResumeParser
# ---------------------------------------------------------------------------

class SmartResumeParser:
    """
    7-category structured resume extraction engine.

    Flow: load prompt -> mask PII -> LLM extraction -> unmask -> validate.
    """

    # Expected top-level keys in LLM response
    REQUIRED_CATEGORIES = [
        "basic_info",
        "work_experience",
        "education",
        "skills",
        "certifications",
        "languages",
        "projects",
    ]

    def __init__(self) -> None:
        self._pii = PIIMaskingService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @AiCapability(
        capability="smart_resume_parse",
        name="SmartResume 7-Category Parser",
        endpoint="/api/hr/resumes/{id}/parse",
        method="POST",
        tool_name="smart_parse_resume",
        permissions=["resume:parse"],
        llm_model="gpt-4o-mini",
        fallback_model="gpt-3.5-turbo",
        prompt_version="v2",
        allowed_callers=["api", "agent"],
        requires_tenant_isolation=True,
        ai_capability_id="smart_resume_parse_v2",
        description="Extract 7 categories of structured data from resume text",
        request_model="SmartResumeParseRequest",
        response_model="SmartResumeParseResult",
        rate_limit="20/minute",
        data_classification="L3",
        audit_level="detailed",
        tags=["ai", "resume", "parse", "smart"],
        timeout=30.0,
    )
    async def parse(self, resume_text: str) -> dict[str, Any]:
        """
        Parse resume text into 7-category structured data.

        Args:
            resume_text: Raw text extracted from the resume file.

        Returns:
            Dict with keys: basic_info, work_experience, education,
            skills, certifications, languages, projects,
            plus _meta (parse_duration_ms, parse_model, categories_count).
        """
        start = time.monotonic()

        template = _get_prompt_template()
        system_prompt = _build_system_prompt(template)
        model_settings = template.get("model_settings", {})

        # Step 1: mask PII
        masked_text, pii_mapping = await self._pii.mask(resume_text)

        # Step 2: call LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Parse this resume:\n\n{masked_text}"},
        ]

        from app.services.ai_client import ai_client

        raw_result = await ai_client.chat_completion(
            messages,
            model=model_settings.get("model_override"),
            temperature=model_settings.get("temperature", 0.1),
            max_tokens=model_settings.get("max_tokens", 4096),
            response_format={"type": "json_object"},
        )

        if raw_result is None:
            raise RuntimeError("LLM parsing failed: all providers unavailable")

        # Step 3: unmask PII in the JSON result
        raw_json_str = json.dumps(raw_result, ensure_ascii=False)
        unmasked_json_str = await self._pii.unmask(raw_json_str, pii_mapping)
        parsed: dict[str, Any] = json.loads(unmasked_json_str)

        # Step 4: normalize & validate
        parsed = self._normalize(parsed)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        parsed["_meta"] = {
            "parse_duration_ms": elapsed_ms,
            "parse_model": model_settings.get("model_override", "gpt-4o-mini"),
            "categories_count": len(self.REQUIRED_CATEGORIES),
        }

        logger.info(
            "smart_resume_parse completed duration_ms=%d categories=%d",
            elapsed_ms,
            len(self.REQUIRED_CATEGORIES),
        )

        return parsed

    # ------------------------------------------------------------------
    # Category-specific extraction helpers (for partial re-extraction)
    # ------------------------------------------------------------------

    async def extract_basic_info(self, resume_text: str) -> dict[str, Any]:
        """Extract only basic_info category."""
        result = await self._extract_single_category(resume_text, "basic_info")
        return result.get("basic_info", {})

    async def extract_work_experience(self, resume_text: str) -> list[dict[str, Any]]:
        """Extract only work_experience category."""
        result = await self._extract_single_category(resume_text, "work_experience")
        return result.get("work_experience", [])

    async def extract_education(self, resume_text: str) -> list[dict[str, Any]]:
        """Extract only education category."""
        result = await self._extract_single_category(resume_text, "education")
        return result.get("education", [])

    async def extract_skills(self, resume_text: str) -> list[dict[str, Any]]:
        """Extract only skills category."""
        result = await self._extract_single_category(resume_text, "skills")
        return result.get("skills", [])

    async def extract_certifications(self, resume_text: str) -> list[dict[str, Any]]:
        """Extract only certifications category."""
        result = await self._extract_single_category(resume_text, "certifications")
        return result.get("certifications", [])

    async def extract_languages(self, resume_text: str) -> list[dict[str, Any]]:
        """Extract only languages category."""
        result = await self._extract_single_category(resume_text, "languages")
        return result.get("languages", [])

    async def extract_projects(self, resume_text: str) -> list[dict[str, Any]]:
        """Extract only projects category."""
        result = await self._extract_single_category(resume_text, "projects")
        return result.get("projects", [])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _extract_single_category(
        self, resume_text: str, category: str
    ) -> dict[str, Any]:
        """Re-extract a single category from resume text."""
        template = _get_prompt_template()
        cat_def = template["schema"][category]

        fields_desc = []
        for fname, finfo in cat_def["fields"].items():
            fields_desc.append(f"  - {fname} ({finfo['type']}): {finfo['description']}")

        system = (
            "You are a resume field extractor. Extract ONLY the following category "
            f"and return a JSON object with a single key \"{category}\".\n\n"
            f"Category: {cat_def['description']}\n"
            f"Fields:\n" + "\n".join(fields_desc) +
            "\n\nReturn valid JSON only. Use null for missing fields."
        )

        masked_text, pii_mapping = await self._pii.mask(resume_text)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Extract from this resume:\n\n{masked_text}"},
        ]

        from app.services.ai_client import ai_client

        raw = await ai_client.chat_completion(
            messages,
            temperature=0.1,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )

        if raw is None:
            return {category: [] if cat_def.get("is_array") else {}}

        raw_str = json.dumps(raw, ensure_ascii=False)
        unmasked_str = await self._pii.unmask(raw_str, pii_mapping)
        return json.loads(unmasked_str)

    def _normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Ensure all 7 categories exist with correct types."""
        array_categories = {
            "work_experience",
            "education",
            "skills",
            "certifications",
            "languages",
            "projects",
        }

        for cat in self.REQUIRED_CATEGORIES:
            if cat not in data:
                data[cat] = [] if cat in array_categories else {}
            elif cat in array_categories and not isinstance(data[cat], list):
                data[cat] = []
            elif cat == "basic_info" and not isinstance(data[cat], dict):
                data[cat] = {}

        # Remove any unexpected top-level keys (except _meta which is added later)
        return {k: v for k, v in data.items() if k in self.REQUIRED_CATEGORIES or k == "_meta"}


# Singleton
smart_resume_parser = SmartResumeParser()
