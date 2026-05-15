"""
AI Service Client.

Centralized client for LLM and Hermes Agent interactions.
Handles API calls, error recovery, and fallback logic.
"""

import json
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger("hiremind.ai")


class AIClient:
    """Unified client for AI service interactions."""

    def __init__(self):
        self._openai_key = settings.OPENAI_API_KEY
        self._openai_base = settings.OPENAI_API_BASE
        self._openai_model = settings.OPENAI_MODEL_RESUME
        self._hermes_url = settings.HERMES_AGENT_URL
        self._hermes_key = settings.HERMES_AGENT_API_KEY

    async def is_openai_available(self) -> bool:
        """Check if OpenAI API is configured."""
        return bool(self._openai_key)

    async def is_hermes_available(self) -> bool:
        """Check if Hermes Agent is reachable."""
        if not self._hermes_url:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._hermes_url}/health")
                return resp.status_code == 200
        except Exception:
            return False

    async def chat_completion(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> dict | None:
        """
        Call OpenAI Chat Completion API.

        Returns parsed JSON if response_format is set, else raw content dict.
        Returns None if API is unavailable.
        """
        if not self._openai_key:
            logger.warning("OpenAI API key not configured")
            return None

        url = f"{self._openai_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._openai_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model or self._openai_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]

                if response_format and response_format.get("type") == "json_object":
                    return json.loads(content)
                return {"content": content}
        except httpx.HTTPStatusError as exc:
            logger.error(
                "OpenAI API error: %s %s",
                exc.response.status_code,
                exc.response.text[:200],
            )
            return None
        except Exception as exc:
            logger.error("OpenAI request failed: %s", exc)
            return None

    async def parse_resume_with_ai(self, resume_text: str) -> dict | None:
        """
        Use OpenAI to parse resume text into structured data.

        Returns parsed resume dict or None if AI is unavailable.
        """
        system_prompt = """You are an expert resume parser. Extract the following information from the resume text and return it as a JSON object with these exact fields:

{
  "basic_info": {
    "name": "Full name",
    "email": "Email address",
    "phone": "Phone number",
    "location": "City/Country",
    "current_company": "Current employer",
    "current_title": "Current job title",
    "years_of_experience": 5.0
  },
  "education": [
    {
      "school": "University name",
      "degree": "Bachelor/Master/PhD",
      "major": "Field of study",
      "start_date": "YYYY-MM",
      "end_date": "YYYY-MM"
    }
  ],
  "work_experience": [
    {
      "company": "Company name",
      "position": "Job title",
      "start_date": "YYYY-MM",
      "end_date": "YYYY-MM or 'present'",
      "description": "Brief description of responsibilities",
      "duration_years": 2.5
    }
  ],
  "skills": ["Skill1", "Skill2", "Skill3"],
  "certifications": ["Cert1"],
  "languages": ["Chinese", "English"],
  "summary": "Brief professional summary in 2-3 sentences"
}

Rules:
- Extract ONLY information explicitly stated in the resume
- Use null for missing fields, NOT made-up values
- Calculate duration_years from start/end dates if possible
- Skills should be individual technical/professional skills
- Return valid JSON only, no markdown"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Parse this resume:\n\n{resume_text}"},
        ]

        return await self.chat_completion(
            messages,
            response_format={"type": "json_object"},
            max_tokens=4096,
        )

    async def score_candidate_match(
        self,
        position_info: dict,
        candidate_info: dict,
    ) -> dict | None:
        """
        Use OpenAI to provide AI-enhanced matching score between position and candidate.

        Returns {"ai_score": 0-100, "ai_reasoning": "explanation"} or None.
        """
        system_prompt = """You are an expert recruiter. Given a job position and a candidate profile, provide:
1. A compatibility score from 0-100
2. A brief reasoning explaining the score

Return JSON: {"ai_score": 75, "ai_reasoning": "explanation"}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {"position": position_info, "candidate": candidate_info},
                    ensure_ascii=False,
                ),
            },
        ]

        return await self.chat_completion(
            messages,
            response_format={"type": "json_object"},
            max_tokens=512,
        )


# Singleton instance
ai_client = AIClient()
