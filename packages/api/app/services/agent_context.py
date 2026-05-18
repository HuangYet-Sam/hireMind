"""AgentContext security mechanism for AI Agent ↔ FastAPI context passing (PRD §8.1b)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from typing import Tuple

from fastapi import Depends, HTTPException, Request


@dataclass(frozen=True)
class AgentContext:
    tenant_id: str
    user_id: str
    session_id: str
    capabilities: Tuple[str, ...]
    timestamp: float  # Unix timestamp
    nonce: str  # UUID4


def _signing_payload(context: AgentContext) -> str:
    return f"{context.tenant_id}.{context.user_id}.{context.session_id}.{context.timestamp}.{context.nonce}"


def sign(context: AgentContext, secret: str) -> str:
    """Generate HMAC-SHA256 signature for an AgentContext."""
    payload = _signing_payload(context)
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def verify(context: AgentContext, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature for an AgentContext."""
    expected = sign(context, secret)
    return hmac.compare_digest(expected, signature)


class _NonceCache:
    """Thread-safe in-memory LRU cache for recent nonces (max 1000)."""

    def __init__(self, maxsize: int = 1000) -> None:
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._maxsize = maxsize

    def check_and_store(self, nonce: str) -> bool:
        """Return True if nonce is new (not a replay), False if already seen."""
        if nonce in self._cache:
            return False
        self._cache[nonce] = time.time()
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)
        return True


_nonce_cache = _NonceCache()

MAX_TIMESTAMP_DRIFT = 300  # 5 minutes


async def verify_agent_context(request: Request) -> AgentContext:
    """FastAPI dependency: extract, validate, and inject AgentContext from request headers."""
    ctx_header = request.headers.get("X-Agent-Context")
    sig_header = request.headers.get("X-Agent-Signature")

    if not ctx_header or not sig_header:
        raise HTTPException(status_code=401, detail="Missing agent context headers")

    try:
        raw = json.loads(ctx_header)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid agent context JSON")

    try:
        capabilities = tuple(raw["capabilities"])
        context = AgentContext(
            tenant_id=raw["tenant_id"],
            user_id=raw["user_id"],
            session_id=raw["session_id"],
            capabilities=capabilities,
            timestamp=float(raw["timestamp"]),
            nonce=raw["nonce"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid agent context: {exc}")

    # Timestamp freshness check
    now = time.time()
    if abs(now - context.timestamp) > MAX_TIMESTAMP_DRIFT:
        raise HTTPException(status_code=401, detail="Agent context timestamp expired")

    # Nonce replay check
    if not _nonce_cache.check_and_store(context.nonce):
        raise HTTPException(status_code=401, detail="Replayed nonce detected")

    # HMAC signature check — secret from app state or env
    secret = request.app.state.agent_context_secret if hasattr(request.app.state, "agent_context_secret") else ""
    if not secret:
        raise HTTPException(status_code=500, detail="Agent context secret not configured")

    if not verify(context, sig_header, secret):
        raise HTTPException(status_code=401, detail="Invalid agent context signature")

    return context


AgentContextDep = AgentContext  # Type alias for DI annotation
