"""Health check tests."""
import pytest


@pytest.mark.anyio
async def test_health_check(client):
    """Test that health check endpoint returns 200."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.anyio
async def test_root_redirect(client):
    """Test that root returns API info."""
    response = await client.get("/")
    assert response.status_code == 200
