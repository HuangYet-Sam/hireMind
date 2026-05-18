"""Unit tests for @AiCapability decorator and registry."""

from __future__ import annotations

import asyncio
import pytest

from app.decorators.ai_capability import (
    AiCapability,
    _AI_CAPABILITIES_REGISTRY,
    _registry_lock,
    get_all_capabilities,
    get_capability,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_registry() -> None:
    """Remove all entries from the global registry (for test isolation)."""
    with _registry_lock:
        _AI_CAPABILITIES_REGISTRY.clear()


@pytest.fixture(autouse=True)
def _isolate_registry():
    """Ensure each test starts with an empty registry."""
    _clear_registry()
    yield
    _clear_registry()


# ---------------------------------------------------------------------------
# Backward compatibility – original 5-param usage still works
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    def test_minimal_decorator(self):
        """Original single-arg usage still works."""

        @AiCapability("resume_parse")
        async def parse_resume(text: str) -> str:
            return text

        assert asyncio.iscoroutinefunction(parse_resume)
        result = asyncio.get_event_loop().run_until_complete(parse_resume("hello"))
        assert result == "hello"

    def test_original_params(self):
        """All original 5 params accepted without error."""

        async def fb():
            return "fallback"

        @AiCapability(
            "resume_parse",
            fallback=fb,
            timeout=60.0,
            cache_ttl=120,
        )
        async def parse_resume(text: str) -> str:
            return text

        assert asyncio.iscoroutinefunction(parse_resume)

    def test_sync_function(self):
        """Sync wrapped functions still work."""

        @AiCapability("sync_cap")
        def do_work() -> int:
            return 42

        assert do_work() == 42


# ---------------------------------------------------------------------------
# Full 21-field registration
# ---------------------------------------------------------------------------

class TestFullRegistration:
    def test_all_21_fields_stored(self):
        """When all fields are provided, every one is stored in the registry."""

        async def fb():
            return "fb"

        @AiCapability(
            "candidate_match",
            name="Candidate Matching",
            endpoint="/api/v1/ai/candidate-match",
            method="POST",
            tool_name="candidate_match_tool",
            permissions=["admin", "recruiter"],
            llm_model="gpt-4",
            fallback_model="gpt-3.5-turbo",
            prompt_version="v2.1",
            allowed_callers=["api", "agent"],
            requires_tenant_isolation=True,
            ai_capability_id="cap.candidate.match.v1",
            description="Match candidates to job descriptions",
            request_model="CandidateMatchRequest",
            response_model="CandidateMatchResponse",
            rate_limit="100/minute",
            data_classification="L3",
            audit_level="detailed",
            tags=["matching", "nlp"],
            fallback=fb,
            timeout=45.0,
            cache_ttl=300,
        )
        async def match():
            return "ok"

        cap = get_capability("cap.candidate.match.v1")
        assert cap is not None
        assert cap["capability"] == "candidate_match"
        assert cap["name"] == "Candidate Matching"
        assert cap["endpoint"] == "/api/v1/ai/candidate-match"
        assert cap["method"] == "POST"
        assert cap["tool_name"] == "candidate_match_tool"
        assert cap["permissions"] == ["admin", "recruiter"]
        assert cap["llm_model"] == "gpt-4"
        assert cap["fallback_model"] == "gpt-3.5-turbo"
        assert cap["prompt_version"] == "v2.1"
        assert cap["allowed_callers"] == ["api", "agent"]
        assert cap["requires_tenant_isolation"] is True
        assert cap["ai_capability_id"] == "cap.candidate.match.v1"
        assert cap["description"] == "Match candidates to job descriptions"
        assert cap["request_model"] == "CandidateMatchRequest"
        assert cap["response_model"] == "CandidateMatchResponse"
        assert cap["rate_limit"] == "100/minute"
        assert cap["data_classification"] == "L3"
        assert cap["audit_level"] == "detailed"
        assert cap["tags"] == ["matching", "nlp"]
        assert cap["timeout"] == 45.0
        assert cap["cache_ttl"] == 300

    def test_defaults(self):
        """Fields that are optional default to None / sensible values."""

        @AiCapability("simple_cap")
        async def simple():
            return "ok"

        cap = get_capability("simple_cap")
        assert cap is not None
        assert cap["name"] is None
        assert cap["method"] == "POST"
        assert cap["data_classification"] == "L2"
        assert cap["audit_level"] == "standard"
        assert cap["requires_tenant_isolation"] is False
        assert cap["timeout"] == 30.0
        assert cap["cache_ttl"] is None
        assert cap["tags"] is None


# ---------------------------------------------------------------------------
# Registry APIs
# ---------------------------------------------------------------------------

class TestRegistryAPIs:
    def test_get_all_capabilities(self):
        @AiCapability("cap_a", ai_capability_id="id_a")
        async def a():
            pass

        @AiCapability("cap_b", ai_capability_id="id_b")
        async def b():
            pass

        all_caps = get_all_capabilities()
        assert len(all_caps) == 2
        assert "id_a" in all_caps
        assert "id_b" in all_caps

    def test_get_capability_by_capability_name(self):
        """Lookup by *capability* when no *ai_capability_id* is set."""

        @AiCapability("my_cap")
        async def fn():
            pass

        assert get_capability("my_cap") is not None

    def test_get_capability_returns_none_for_unknown(self):
        assert get_capability("nonexistent") is None

    def test_get_all_returns_copy(self):
        """Mutating the returned dict must not affect the registry."""

        @AiCapability("cap_x")
        async def x():
            pass

        copy = get_all_capabilities()
        copy.clear()
        assert len(get_all_capabilities()) == 1

    def test_metadata_includes_qualified_name_and_module(self):
        @AiCapability("cap_meta")
        async def meta_fn():
            pass

        cap = get_capability("cap_meta")
        assert cap["qualified_name"].endswith("meta_fn")
        assert "test_ai_capability" in cap["module"]

    def test_overwrite_on_duplicate_key(self):
        """Later registration overwrites earlier with the same key."""

        @AiCapability("dup", name="first")
        async def first():
            pass

        @AiCapability("dup", name="second")
        async def second():
            pass

        assert get_capability("dup")["name"] == "second"


# ---------------------------------------------------------------------------
# Async / sync wrapping behaviour
# ---------------------------------------------------------------------------

class TestWrapping:
    def test_async_fallback_invoked_on_exception(self):
        """Fallback runs when the wrapped async function raises."""

        async def fb():
            return "recovered"

        @AiCapability("err_cap", fallback=fb)
        async def failing():
            raise RuntimeError("boom")

        result = asyncio.get_event_loop().run_until_complete(failing())
        assert result == "recovered"

    def test_sync_fallback_invoked_on_exception(self):
        def fb():
            return "sync_recovered"

        @AiCapability("sync_err", fallback=fb)
        def failing():
            raise RuntimeError("boom")

        assert failing() == "sync_recovered"

    def test_exception_propagates_when_no_fallback(self):
        @AiCapability("no_fb")
        async def failing():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            asyncio.get_event_loop().run_until_complete(failing())
