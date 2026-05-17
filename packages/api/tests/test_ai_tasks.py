"""
HireMind AI Tasks Integration Tests.

Covers all 5 endpoints: list, create, get, cancel, retry.
Tests: CRUD flow, pagination, status filtering, 404 not found,
409 state conflicts, and multi-tenant isolation.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_task import AiTask, TaskStatus, TaskType


# ── Helper ────────────────────────────────────────────────────────────

async def _create_task_via_api(client: AsyncClient, **overrides) -> dict:
    """Create an AI task via POST and return the JSON response."""
    payload = {
        "task_type": "resume_parse",
        "input_data": '{"resume_url": "https://example.com/resume.pdf"}',
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/ai-tasks/", json=payload)
    assert resp.status_code == 201, f"Create failed: {resp.text}"
    return resp.json()


# ── List AI Tasks ─────────────────────────────────────────────────────

class TestListAiTasks:

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient):
        response = await client.get("/api/v1/ai-tasks/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["pages"] == 0

    @pytest.mark.asyncio
    async def test_list_after_create(self, client: AsyncClient):
        await _create_task_via_api(client)
        response = await client.get("/api/v1/ai-tasks/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_list_pagination(self, client: AsyncClient, db_session: AsyncSession, test_tenant):
        """Create 5 tasks directly in DB, then paginate."""
        for i in range(5):
            db_session.add(AiTask(
                tenant_id=str(test_tenant.id),
                task_type=TaskType.resume_parse,
                status=TaskStatus.pending,
                input_data=f'{{"batch": {i}}}',
            ))
        await db_session.commit()

        response = await client.get("/api/v1/ai-tasks/?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["pages"] == 3  # ceil(5/2) = 3

    @pytest.mark.asyncio
    async def test_list_pagination_page_2(self, client: AsyncClient, db_session: AsyncSession, test_tenant):
        for i in range(5):
            db_session.add(AiTask(
                tenant_id=str(test_tenant.id),
                task_type=TaskType.resume_parse,
                status=TaskStatus.pending,
            ))
        await db_session.commit()

        response = await client.get("/api/v1/ai-tasks/?page=2&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["page"] == 2

    @pytest.mark.asyncio
    async def test_list_filter_by_status(self, client: AsyncClient, db_session: AsyncSession, test_tenant):
        for status_val in [TaskStatus.pending, TaskStatus.completed, TaskStatus.failed]:
            db_session.add(AiTask(
                tenant_id=str(test_tenant.id),
                task_type=TaskType.resume_parse,
                status=status_val,
            ))
        await db_session.commit()

        response = await client.get("/api/v1/ai-tasks/?status=completed")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_list_filter_by_status_no_results(self, client: AsyncClient):
        response = await client.get("/api/v1/ai-tasks/?status=cancelled")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_default_page_size(self, client: AsyncClient):
        response = await client.get("/api/v1/ai-tasks/")
        assert response.status_code == 200
        data = response.json()
        assert data["page_size"] == 20

    @pytest.mark.asyncio
    async def test_list_multi_tenant_isolation(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Tasks from another tenant should not be visible."""
        other_tenant_id = str(uuid4())
        db_session.add(AiTask(
            tenant_id=other_tenant_id,
            task_type=TaskType.resume_parse,
            status=TaskStatus.pending,
        ))
        await db_session.commit()

        response = await client.get("/api/v1/ai-tasks/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


# ── Create AI Task ────────────────────────────────────────────────────

class TestCreateAiTask:

    @pytest.mark.asyncio
    async def test_create_success(self, client: AsyncClient):
        data = await _create_task_via_api(client)
        assert "id" in data
        assert data["task_type"] == "resume_parse"
        assert data["status"] == "pending"
        assert data["input_data"] == '{"resume_url": "https://example.com/resume.pdf"}'
        assert data["output_data"] is None
        assert data["error_message"] is None
        assert data["created_by"] == "test-user-id"

    @pytest.mark.asyncio
    async def test_create_all_task_types(self, client: AsyncClient):
        for task_type in ["resume_parse", "candidate_match", "batch_score", "report_generate", "data_import"]:
            data = await _create_task_via_api(client, task_type=task_type)
            assert data["task_type"] == task_type

    @pytest.mark.asyncio
    async def test_create_without_input_data(self, client: AsyncClient):
        payload = {"task_type": "batch_score"}
        resp = await client.post("/api/v1/ai-tasks/", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["input_data"] is None

    @pytest.mark.asyncio
    async def test_create_missing_task_type_returns_422(self, client: AsyncClient):
        payload = {"input_data": '{"test": true}'}
        resp = await client.post("/api/v1/ai-tasks/", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_invalid_task_type_returns_422(self, client: AsyncClient):
        payload = {"task_type": "invalid_type"}
        resp = await client.post("/api/v1/ai-tasks/", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_returns_201_status_code(self, client: AsyncClient):
        payload = {"task_type": "data_import"}
        resp = await client.post("/api/v1/ai-tasks/", json=payload)
        assert resp.status_code == 201


# ── Get AI Task ───────────────────────────────────────────────────────

class TestGetAiTask:

    @pytest.mark.asyncio
    async def test_get_existing_task(self, client: AsyncClient):
        created = await _create_task_via_api(client)
        response = await client.get(f"/api/v1/ai-tasks/{created['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created["id"]
        assert data["task_type"] == created["task_type"]
        assert data["status"] == created["status"]

    @pytest.mark.asyncio
    async def test_get_not_found(self, client: AsyncClient):
        fake_id = uuid4()
        response = await client.get(f"/api/v1/ai-tasks/{fake_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_invalid_uuid_returns_422(self, client: AsyncClient):
        response = await client.get("/api/v1/ai-tasks/not-a-uuid")
        assert response.status_code == 422


# ── Cancel AI Task ────────────────────────────────────────────────────

class TestCancelAiTask:

    @pytest.mark.asyncio
    async def test_cancel_pending_task(self, client: AsyncClient):
        created = await _create_task_via_api(client)
        response = await client.post(f"/api/v1/ai-tasks/{created['id']}/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["id"] == created["id"]

    @pytest.mark.asyncio
    async def test_cancel_running_task(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant
    ):
        task = AiTask(
            tenant_id=str(test_tenant.id),
            task_type=TaskType.resume_parse,
            status=TaskStatus.running,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        response = await client.post(f"/api/v1/ai-tasks/{task.id}/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_completed_task_conflict(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant
    ):
        task = AiTask(
            tenant_id=str(test_tenant.id),
            task_type=TaskType.resume_parse,
            status=TaskStatus.completed,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        response = await client.post(f"/api/v1/ai-tasks/{task.id}/cancel")
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_cancel_failed_task_conflict(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant
    ):
        task = AiTask(
            tenant_id=str(test_tenant.id),
            task_type=TaskType.resume_parse,
            status=TaskStatus.failed,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        response = await client.post(f"/api/v1/ai-tasks/{task.id}/cancel")
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled_conflict(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant
    ):
        task = AiTask(
            tenant_id=str(test_tenant.id),
            task_type=TaskType.resume_parse,
            status=TaskStatus.cancelled,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        response = await client.post(f"/api/v1/ai-tasks/{task.id}/cancel")
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_cancel_not_found(self, client: AsyncClient):
        fake_id = uuid4()
        response = await client.post(f"/api/v1/ai-tasks/{fake_id}/cancel")
        assert response.status_code == 404


# ── Retry AI Task ─────────────────────────────────────────────────────

class TestRetryAiTask:

    @pytest.mark.asyncio
    async def test_retry_failed_task(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant
    ):
        task = AiTask(
            tenant_id=str(test_tenant.id),
            task_type=TaskType.resume_parse,
            status=TaskStatus.failed,
            error_message="Something went wrong",
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        response = await client.post(f"/api/v1/ai-tasks/{task.id}/retry")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["error_message"] is None
        assert data["output_data"] is None

    @pytest.mark.asyncio
    async def test_retry_cancelled_task(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant
    ):
        task = AiTask(
            tenant_id=str(test_tenant.id),
            task_type=TaskType.candidate_match,
            status=TaskStatus.cancelled,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        response = await client.post(f"/api/v1/ai-tasks/{task.id}/retry")
        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_retry_pending_task_conflict(self, client: AsyncClient):
        created = await _create_task_via_api(client)
        response = await client.post(f"/api/v1/ai-tasks/{created['id']}/retry")
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_retry_running_task_conflict(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant
    ):
        task = AiTask(
            tenant_id=str(test_tenant.id),
            task_type=TaskType.resume_parse,
            status=TaskStatus.running,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        response = await client.post(f"/api/v1/ai-tasks/{task.id}/retry")
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_retry_completed_task_conflict(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant
    ):
        task = AiTask(
            tenant_id=str(test_tenant.id),
            task_type=TaskType.resume_parse,
            status=TaskStatus.completed,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        response = await client.post(f"/api/v1/ai-tasks/{task.id}/retry")
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_retry_not_found(self, client: AsyncClient):
        fake_id = uuid4()
        response = await client.post(f"/api/v1/ai-tasks/{fake_id}/retry")
        assert response.status_code == 404


# ── Multi-Tenant Isolation ────────────────────────────────────────────

class TestMultiTenantIsolation:

    @pytest.mark.asyncio
    async def test_get_task_from_other_tenant_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Task created under a different tenant_id is invisible."""
        other_tenant_id = str(uuid4())
        task = AiTask(
            tenant_id=other_tenant_id,
            task_type=TaskType.resume_parse,
            status=TaskStatus.pending,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        response = await client.get(f"/api/v1/ai-tasks/{task.id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_task_from_other_tenant_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        other_tenant_id = str(uuid4())
        task = AiTask(
            tenant_id=other_tenant_id,
            task_type=TaskType.resume_parse,
            status=TaskStatus.pending,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        response = await client.post(f"/api/v1/ai-tasks/{task.id}/cancel")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_retry_task_from_other_tenant_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        other_tenant_id = str(uuid4())
        task = AiTask(
            tenant_id=other_tenant_id,
            task_type=TaskType.resume_parse,
            status=TaskStatus.failed,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        response = await client.post(f"/api/v1/ai-tasks/{task.id}/retry")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_excludes_other_tenant_tasks(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant
    ):
        # One task in current tenant
        db_session.add(AiTask(
            tenant_id=str(test_tenant.id),
            task_type=TaskType.resume_parse,
            status=TaskStatus.pending,
        ))
        # One task in other tenant
        db_session.add(AiTask(
            tenant_id=str(uuid4()),
            task_type=TaskType.resume_parse,
            status=TaskStatus.pending,
        ))
        await db_session.commit()

        response = await client.get("/api/v1/ai-tasks/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1


# ── Full Workflow ─────────────────────────────────────────────────────

class TestAiTaskWorkflow:

    @pytest.mark.asyncio
    async def test_create_cancel_retry_workflow(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Full lifecycle: create → cancel → retry → cancel again."""
        # 1. Create
        created = await _create_task_via_api(client)
        task_id = created["id"]
        assert created["status"] == "pending"

        # 2. Cancel
        resp = await client.post(f"/api/v1/ai-tasks/{task_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

        # 3. Retry (cancelled → pending)
        resp = await client.post(f"/api/v1/ai-tasks/{task_id}/retry")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

        # 4. Cancel again (pending → cancelled)
        resp = await client.post(f"/api/v1/ai-tasks/{task_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_create_get_list_workflow(self, client: AsyncClient):
        """Create task, retrieve it individually, verify it appears in list."""
        created = await _create_task_via_api(
            client, task_type="report_generate", input_data='{"report": "quarterly"}'
        )
        task_id = created["id"]

        # Get by ID
        resp = await client.get(f"/api/v1/ai-tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["task_type"] == "report_generate"

        # List includes the task
        resp = await client.get("/api/v1/ai-tasks/")
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert task_id in ids
