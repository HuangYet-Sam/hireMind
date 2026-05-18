"""Tests for AgentContext security mechanism (PRD §8.1b)."""

import json
import time
import uuid

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.services.agent_context import (
    AgentContext,
    _NonceCache,
    sign,
    verify,
    verify_agent_context,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SECRET = "test-secret-key"


def _make_context(**overrides):
    defaults = dict(
        tenant_id="tenant-1",
        user_id="user-1",
        session_id="sess-1",
        capabilities=("read", "write"),
        timestamp=time.time(),
        nonce=str(uuid.uuid4()),
    )
    defaults.update(overrides)
    return AgentContext(**defaults)


def _ctx_json(ctx: AgentContext) -> str:
    return json.dumps({
        "tenant_id": ctx.tenant_id,
        "user_id": ctx.user_id,
        "session_id": ctx.session_id,
        "capabilities": list(ctx.capabilities),
        "timestamp": ctx.timestamp,
        "nonce": ctx.nonce,
    })


# ---------------------------------------------------------------------------
# Frozen dataclass
# ---------------------------------------------------------------------------

class TestFrozenDataclass:
    def test_immutable(self):
        ctx = _make_context()
        with pytest.raises(AttributeError):
            ctx.tenant_id = "changed"

    def test_fields(self):
        ctx = _make_context()
        assert ctx.tenant_id == "tenant-1"
        assert ctx.capabilities == ("read", "write")
        assert isinstance(ctx.nonce, str)


# ---------------------------------------------------------------------------
# HMAC signing / verification
# ---------------------------------------------------------------------------

class TestHMAC:
    def test_sign_produces_hex(self):
        ctx = _make_context()
        sig = sign(ctx, SECRET)
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex

    def test_verify_correct(self):
        ctx = _make_context()
        sig = sign(ctx, SECRET)
        assert verify(ctx, sig, SECRET) is True

    def test_verify_wrong_secret(self):
        ctx = _make_context()
        sig = sign(ctx, SECRET)
        assert verify(ctx, sig, "wrong-secret") is False

    def test_verify_tampered_context(self):
        ctx = _make_context()
        sig = sign(ctx, SECRET)
        ctx2 = _make_context(user_id="tampered")
        assert verify(ctx2, sig, SECRET) is False

    def test_verify_wrong_signature(self):
        ctx = _make_context()
        assert verify(ctx, "0" * 64, SECRET) is False


# ---------------------------------------------------------------------------
# Timestamp validation
# ---------------------------------------------------------------------------

class TestTimestamp:
    @pytest.mark.asyncio
    async def test_valid_timestamp(self):
        app = FastAPI()
        app.state.agent_context_secret = SECRET

        @app.get("/test")
        async def handler(ctx: AgentContext = Depends(verify_agent_context)):
            return {"tenant_id": ctx.tenant_id}

        ctx = _make_context()
        sig = sign(ctx, SECRET)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/test",
                headers={
                    "X-Agent-Context": _ctx_json(ctx),
                    "X-Agent-Signature": sig,
                },
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_expired_timestamp(self):
        app = FastAPI()
        app.state.agent_context_secret = SECRET

        @app.get("/test")
        async def handler(ctx: AgentContext = Depends(verify_agent_context)):
            return {"ok": True}

        ctx = _make_context(timestamp=time.time() - 600)  # 10 minutes ago
        sig = sign(ctx, SECRET)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/test",
                headers={
                    "X-Agent-Context": _ctx_json(ctx),
                    "X-Agent-Signature": sig,
                },
            )
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_future_timestamp(self):
        app = FastAPI()
        app.state.agent_context_secret = SECRET

        @app.get("/test")
        async def handler(ctx: AgentContext = Depends(verify_agent_context)):
            return {"ok": True}

        ctx = _make_context(timestamp=time.time() + 600)
        sig = sign(ctx, SECRET)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/test",
                headers={
                    "X-Agent-Context": _ctx_json(ctx),
                    "X-Agent-Signature": sig,
                },
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_boundary_timestamp_within_5min(self):
        app = FastAPI()
        app.state.agent_context_secret = SECRET

        @app.get("/test")
        async def handler(ctx: AgentContext = Depends(verify_agent_context)):
            return {"ok": True}

        ctx = _make_context(timestamp=time.time() - 299)  # just under 5 min
        sig = sign(ctx, SECRET)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/test",
                headers={
                    "X-Agent-Context": _ctx_json(ctx),
                    "X-Agent-Signature": sig,
                },
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Nonce replay
# ---------------------------------------------------------------------------

class TestNonceReplay:
    def test_nonce_cache_accepts_new(self):
        cache = _NonceCache()
        assert cache.check_and_store("nonce-1") is True

    def test_nonce_cache_rejects_duplicate(self):
        cache = _NonceCache()
        cache.check_and_store("nonce-1")
        assert cache.check_and_store("nonce-1") is False

    def test_nonce_cache_evicts_old(self):
        cache = _NonceCache(maxsize=3)
        cache.check_and_store("a")
        cache.check_and_store("b")
        cache.check_and_store("c")
        cache.check_and_store("d")  # evicts "a"
        assert cache.check_and_store("a") is True  # "a" was evicted, re-accepted

    @pytest.mark.asyncio
    async def test_replayed_nonce_rejected_via_api(self):
        app = FastAPI()
        app.state.agent_context_secret = SECRET

        @app.get("/test")
        async def handler(ctx: AgentContext = Depends(verify_agent_context)):
            return {"ok": True}

        nonce = str(uuid.uuid4())
        ctx = _make_context(nonce=nonce)
        sig = sign(ctx, SECRET)
        headers = {
            "X-Agent-Context": _ctx_json(ctx),
            "X-Agent-Signature": sig,
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp1 = await client.get("/test", headers=headers)
            assert resp1.status_code == 200

            resp2 = await client.get("/test", headers=headers)
            assert resp2.status_code == 401
            assert "replay" in resp2.json()["detail"].lower()


# ---------------------------------------------------------------------------
# FastAPI dependency injection
# ---------------------------------------------------------------------------

class TestFastAPIDependency:
    @pytest.mark.asyncio
    async def test_missing_headers(self):
        app = FastAPI()

        @app.get("/test")
        async def handler(ctx: AgentContext = Depends(verify_agent_context)):
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/test")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_json(self):
        app = FastAPI()
        app.state.agent_context_secret = SECRET

        @app.get("/test")
        async def handler(ctx: AgentContext = Depends(verify_agent_context)):
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/test",
                headers={
                    "X-Agent-Context": "not-json",
                    "X-Agent-Signature": "sig",
                },
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_fields(self):
        app = FastAPI()
        app.state.agent_context_secret = SECRET

        @app.get("/test")
        async def handler(ctx: AgentContext = Depends(verify_agent_context)):
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/test",
                headers={
                    "X-Agent-Context": json.dumps({"tenant_id": "x"}),
                    "X-Agent-Signature": "sig",
                },
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_wrong_signature(self):
        app = FastAPI()
        app.state.agent_context_secret = SECRET

        @app.get("/test")
        async def handler(ctx: AgentContext = Depends(verify_agent_context)):
            return {"ok": True}

        ctx = _make_context()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/test",
                headers={
                    "X-Agent-Context": _ctx_json(ctx),
                    "X-Agent-Signature": "badsig",
                },
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_secret_not_configured(self):
        app = FastAPI()

        @app.get("/test")
        async def handler(ctx: AgentContext = Depends(verify_agent_context)):
            return {"ok": True}

        ctx = _make_context()
        sig = sign(ctx, SECRET)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/test",
                headers={
                    "X-Agent-Context": _ctx_json(ctx),
                    "X-Agent-Signature": sig,
                },
            )
        assert resp.status_code == 500

    @pytest.mark.asyncio
    async def test_successful_injection(self):
        app = FastAPI()
        app.state.agent_context_secret = SECRET

        @app.get("/test")
        async def handler(ctx: AgentContext = Depends(verify_agent_context)):
            return {
                "tenant_id": ctx.tenant_id,
                "user_id": ctx.user_id,
                "capabilities": list(ctx.capabilities),
            }

        ctx = _make_context()
        sig = sign(ctx, SECRET)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/test",
                headers={
                    "X-Agent-Context": _ctx_json(ctx),
                    "X-Agent-Signature": sig,
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["tenant_id"] == ctx.tenant_id
        assert body["user_id"] == ctx.user_id
        assert body["capabilities"] == ["read", "write"]
