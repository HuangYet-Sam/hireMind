"""
AI Service Client.

Centralized client for LLM and Hermes Agent interactions.
Handles API calls, error recovery, and fallback logic.

Provider priority: Hermes Agent -> OpenAI -> Algorithmic fallback
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

    # ── Provider availability ───────────────────────────────────

    async def is_openai_available(self) -> bool:
        return bool(self._openai_key)

    async def is_hermes_available(self) -> bool:
        if not self._hermes_url:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._hermes_url}/health")
                return resp.status_code == 200
        except Exception:
            return False

    # ── Hermes Agent API ────────────────────────────────────────

    async def hermes_chat_completion(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> dict | None:
        """
        Call Hermes Agent chat completion API (OpenAI-compatible).

        Endpoint: {HERMES_AGENT_URL}/api/hermes/v1/chat/completions
        """
        if not self._hermes_url:
            return None

        url = f"{self._hermes_url}/api/hermes/v1/chat/completions"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._hermes_key:
            headers["Authorization"] = f"Bearer {self._hermes_key}"

        payload: dict[str, Any] = {
            "model": model or "default",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]

                if response_format and response_format.get("type") == "json_object":
                    return json.loads(content)
                return {"content": content}
        except httpx.HTTPStatusError as exc:
            logger.warning("Hermes API error: %s %s", exc.response.status_code, exc.response.text[:200])
            return None
        except Exception as exc:
            logger.warning("Hermes request failed: %s", exc)
            return None

    # ── OpenAI API ──────────────────────────────────────────────

    async def openai_chat_completion(
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
        """
        if not self._openai_key:
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
            logger.error("OpenAI API error: %s %s", exc.response.status_code, exc.response.text[:200])
            return None
        except Exception as exc:
            logger.error("OpenAI request failed: %s", exc)
            return None

    # ── Unified chat (Hermes first, OpenAI fallback) ────────────

    async def chat_completion(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: dict | None = None,
        prefer_hermes: bool = True,
    ) -> dict | None:
        """
        Unified chat completion with provider fallback.

        Priority: Hermes Agent -> OpenAI -> None
        """
        if prefer_hermes:
            result = await self.hermes_chat_completion(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
            if result is not None:
                logger.debug("Used Hermes Agent for chat completion")
                return result

        result = await self.openai_chat_completion(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        if result is not None:
            logger.debug("Used OpenAI for chat completion")
            return result

        logger.warning("All AI providers unavailable")
        return None

    # ── High-level AI capabilities ──────────────────────────────

    async def parse_resume_with_ai(self, resume_text: str) -> dict | None:
        """
        Parse resume text into structured data.

        Priority: Hermes Agent -> OpenAI -> None
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
        AI-enhanced matching score between position and candidate.

        Priority: Hermes Agent -> OpenAI -> None

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

    async def generate_interview_questions(
        self,
        position_info: dict,
        candidate_info: dict,
        interview_type: str = "technical",
        num_questions: int = 5,
    ) -> dict | None:
        """
        Generate interview questions tailored to a position-candidate pair.

        Returns {"questions": [...], "suggested_duration_minutes": int} or None.
        """
        system_prompt = f"""You are an expert interviewer. Generate {num_questions} {interview_type} interview questions for the given position and candidate.

Return JSON:
{{
  "questions": [
    {{
      "question": "The question text",
      "category": "technical/behavioral/system/case",
      "difficulty": "easy/medium/hard",
      "expected_answer_points": ["point1", "point2"]
    }}
  ],
  "suggested_duration_minutes": 60
}}"""

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
            max_tokens=2048,
        )

    async def generate_offer_recommendation(
        self,
        candidate_info: dict,
        position_info: dict,
        market_data: dict | None = None,
    ) -> dict | None:
        """
        Generate AI-powered offer recommendation with salary analysis.

        Returns {"recommended_salary": int, "reasoning": str, "risk_factors": [...]} or None.
        """
        system_prompt = """You are a compensation expert. Based on the candidate profile, position details, and market data, recommend a fair salary range and identify risk factors.

Return JSON:
{
  "recommended_base_salary": 25000,
  "salary_range_low": 20000,
  "salary_range_high": 30000,
  "reasoning": "Explanation of the recommendation",
  "risk_factors": ["risk1", "risk2"],
  "negotiation_tips": ["tip1", "tip2"]
}"""

        payload = {
            "candidate": candidate_info,
            "position": position_info,
        }
        if market_data:
            payload["market_data"] = market_data

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]

        return await self.chat_completion(
            messages,
            response_format={"type": "json_object"},
            max_tokens=1024,
        )

    async def interpret_jd(self, jd_text: str) -> dict | None:
        """
        Interpret a natural-language job description into structured position data.

        Returns a JSON dict matching AIInterpretResponse fields, or None.
        """
        system_prompt = """You are an expert HR assistant specializing in job description analysis.
Given a natural-language job description, extract and return structured position data as JSON.

Return JSON with these exact fields:
{
  "title": "Position title",
  "department": "Department name if mentioned",
  "location": "Work location",
  "employment_type": "full_time / part_time / contract / internship",
  "headcount": 1,
  "salary_min": null,
  "salary_max": null,
  "description": "Full job description",
  "requirements": "Job requirements text",
  "benefits": "Benefits text",
  "required_skills": ["skill1", "skill2"],
  "preferred_skills": ["skill1"],
  "education_requirement": "Minimum education level",
  "experience_years_min": 3,
  "is_remote": false,
  "priority": "normal"
}

Rules:
- Extract ONLY information explicitly stated or clearly implied
- Use null for fields where no information is provided
- required_skills and preferred_skills should be individual items
- salary values should be monthly in CNY if specified
- Return valid JSON only, no markdown"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this job description:\n\n{jd_text}"},
        ]

        return await self.chat_completion(
            messages,
            response_format={"type": "json_object"},
            max_tokens=4096,
        )


# Singleton instance
ai_client = AIClient()
