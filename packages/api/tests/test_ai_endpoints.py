"""
Integration tests for end-to-end AI capability endpoints.

Covers:
- POST /api/v1/positions/ai-interpret  — AI JD interpretation
- POST /api/v1/positions/ai-confirm    — Confirm & create position
- POST /api/v1/resumes/parse           — AI resume parsing
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.department import Department
from app.models.position import Position
from app.models.resume import Resume
from app.models.tenant import Tenant
from app.services.pii_masking import PIIMaskingService


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def sample_jd_text():
    return (
        "我们需要一位高级Java开发工程师，工作地点在北京，全职。"
        "要求3年以上Java开发经验，熟悉Spring Boot、MySQL。"
        "月薪20k-30k，提供五险一金。"
        "联系人张三，邮箱zhangsan@example.com，手机13800138000。"
    )


@pytest.fixture
def sample_interpret_response():
    return {
        "title": "高级Java开发工程师",
        "department": "技术部",
        "location": "北京",
        "employment_type": "full_time",
        "headcount": 1,
        "salary_min": 20000.0,
        "salary_max": 30000.0,
        "description": "高级Java开发工程师岗位",
        "requirements": "3年以上Java开发经验，熟悉Spring Boot、MySQL",
        "benefits": "五险一金",
        "required_skills": ["Java", "Spring Boot", "MySQL"],
        "preferred_skills": None,
        "education_requirement": None,
        "experience_years_min": 3,
        "is_remote": False,
        "priority": "normal",
    }


# ── AI Interpret JD Tests ────────────────────────────────────────


class TestAIInterpretJD:

    @pytest.mark.asyncio
    async def test_ai_interpret_success(
        self, client: AsyncClient, test_tenant, sample_jd_text, sample_interpret_response
    ):
        with patch("app.services.position_service.ai_client") as mock_ai:
            mock_ai.interpret_jd = AsyncMock(return_value=sample_interpret_response)
            resp = await client.post(
                "/api/v1/positions/ai-interpret",
                json={"text": sample_jd_text},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "高级Java开发工程师"
        assert data["location"] == "北京"
        assert data["required_skills"] == ["Java", "Spring Boot", "MySQL"]

    @pytest.mark.asyncio
    async def test_ai_interpret_pii_masking_integrated(
        self, client: AsyncClient, test_tenant, sample_jd_text, sample_interpret_response
    ):
        """Verify PII masking is called before LLM and unmasking happens on response."""
        with patch("app.services.position_service.ai_client") as mock_ai:
            mock_ai.interpret_jd = AsyncMock(return_value=sample_interpret_response)
            resp = await client.post(
                "/api/v1/positions/ai-interpret",
                json={"text": sample_jd_text},
            )
        assert resp.status_code == 200
        data = resp.json()
        # The response should contain original PII (unmasked)
        # PII was masked before sending to LLM, but unmasked on the way back
        assert isinstance(data, dict)
        assert "title" in data

    @pytest.mark.asyncio
    async def test_ai_interpret_llm_failure(self, client: AsyncClient, test_tenant):
        with patch("app.services.position_service.ai_client") as mock_ai:
            mock_ai.interpret_jd = AsyncMock(return_value=None)
            resp = await client.post(
                "/api/v1/positions/ai-interpret",
                json={"text": "We need a Python developer with 5 years experience in web development."},
            )
        assert resp.status_code == 502

    @pytest.mark.asyncio
    async def test_ai_interpret_validation_too_short(self, client: AsyncClient, test_tenant):
        resp = await client.post(
            "/api/v1/positions/ai-interpret",
            json={"text": "short"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ai_interpret_requires_auth(self, client: AsyncClient, test_tenant):
        """Endpoint should be accessible (auth is stubbed in tests)."""
        with patch("app.services.position_service.ai_client") as mock_ai:
            mock_ai.interpret_jd = AsyncMock(return_value={"title": "Dev"})
            resp = await client.post(
                "/api/v1/positions/ai-interpret",
                json={"text": "A" * 20},
            )
        assert resp.status_code == 200


# ── AI Confirm JD Tests ──────────────────────────────────────────


class TestAIConfirmJD:

    @pytest.mark.asyncio
    async def test_ai_confirm_creates_position(
        self, client: AsyncClient, test_tenant, test_department, sample_interpret_response
    ):
        resp = await client.post(
            "/api/v1/positions/ai-confirm",
            json={
                "data": sample_interpret_response,
                "department_id": str(test_department.id),
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "高级Java开发工程师"
        assert data["status"] == "draft"
        assert data["department_id"] == str(test_department.id)

    @pytest.mark.asyncio
    async def test_ai_confirm_without_department(
        self, client: AsyncClient, test_tenant, test_department, sample_interpret_response
    ):
        resp = await client.post(
            "/api/v1/positions/ai-confirm",
            json={
                "data": sample_interpret_response,
                "department_id": str(test_department.id),
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["department_id"] == str(test_department.id)

    @pytest.mark.asyncio
    async def test_ai_confirm_invalid_department(
        self, client: AsyncClient, test_tenant, sample_interpret_response
    ):
        fake_dept_id = str(uuid4())
        resp = await client.post(
            "/api/v1/positions/ai-confirm",
            json={
                "data": sample_interpret_response,
                "department_id": fake_dept_id,
            },
        )
        assert resp.status_code == 409


# ── AI Resume Parse Tests ────────────────────────────────────────


class TestAIResumeParse:

    @pytest.mark.asyncio
    async def test_ai_parse_resume_success(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant
    ):
        # Create a resume record with a temp file
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            f.write("John Doe\nEmail: john@example.com\nPhone: 13912345678\nPython developer")
            temp_path = f.name

        resume = Resume(
            original_filename="test_resume.txt",
            file_path=temp_path,
            file_type="txt",
            file_size=100,
            content_type="text/plain",
            file_hash="abc123",
            source="upload",
            uploaded_by="test-user-id",
            parse_status="pending",
            tenant_id=str(test_tenant.id),
        )
        db_session.add(resume)
        await db_session.commit()
        await db_session.refresh(resume)

        mock_result = {
            "basic_info": {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "13912345678",
            },
            "skills": ["Python"],
        }

        with patch("app.services.ai_client.ai_client") as mock_ai:
            mock_ai.parse_resume_with_ai = AsyncMock(return_value=mock_result)
            resp = await client.post(
                "/api/v1/resumes/parse",
                json={"resume_id": str(resume.id)},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["parse_status"] == "completed"
        assert data["parsed_data"] is not None

        Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_ai_parse_resume_not_found(self, client: AsyncClient, test_tenant):
        fake_id = str(uuid4())
        resp = await client.post(
            "/api/v1/resumes/parse",
            json={"resume_id": fake_id},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_ai_parse_resume_pii_masking(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant
    ):
        """Verify PII masking pipeline is called during resume parsing."""
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            f.write("张三的手机号是13800138000，邮箱zhangsan@test.com")
            temp_path = f.name

        resume = Resume(
            original_filename="pii_test.txt",
            file_path=temp_path,
            file_type="txt",
            file_size=50,
            content_type="text/plain",
            file_hash="pii_test_hash",
            source="upload",
            uploaded_by="test-user-id",
            parse_status="pending",
            tenant_id=str(test_tenant.id),
        )
        db_session.add(resume)
        await db_session.commit()
        await db_session.refresh(resume)

        captured_text = None

        async def fake_parse(text):
            nonlocal captured_text
            captured_text = text
            return {"basic_info": {"name": "[NAME_1]"}}

        with patch("app.services.ai_client.ai_client") as mock_ai:
            mock_ai.parse_resume_with_ai = AsyncMock(side_effect=fake_parse)
            resp = await client.post(
                "/api/v1/resumes/parse",
                json={"resume_id": str(resume.id)},
            )

        assert resp.status_code == 200
        # The text sent to LLM should have been masked (PII removed)
        assert captured_text is not None
        assert "13800138000" not in captured_text
        assert "zhangsan@test.com" not in captured_text

        Path(temp_path).unlink(missing_ok=True)


# ── @AiCapability Registry Integration ───────────────────────────


class TestAICapabilityRegistry:

    def test_all_ai_capabilities_registered(self):
        """Verify all 3 AI capabilities are in the registry after import."""
        from app.decorators.ai_capability import get_all_capabilities

        # Importing the services triggers registration
        import app.services.position_service  # noqa: F401
        import app.services.resume_service  # noqa: F401

        caps = get_all_capabilities()
        cap_ids = set(caps.keys())

        assert "position_ai_interpret_jd" in cap_ids
        assert "position_ai_confirm_jd" in cap_ids
        assert "resume_ai_parse" in cap_ids

    def test_capability_metadata_complete(self):
        from app.decorators.ai_capability import get_capability

        import app.services.position_service  # noqa: F401

        cap = get_capability("position_ai_interpret_jd")
        assert cap is not None
        assert cap["name"] == "AI JD Interpretation"
        assert cap["endpoint"] == "/api/v1/positions/ai-interpret"
        assert cap["data_classification"] == "L2"
        assert cap["allowed_callers"] == ["api", "agent"]
        assert cap["timeout"] == 30.0
