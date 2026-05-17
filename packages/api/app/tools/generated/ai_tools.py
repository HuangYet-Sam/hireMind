"""
Auto-generated Agent Tool registrations from @AiCapability metadata.

DO NOT EDIT - regenerate with: python -m scripts.codegen --tools
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Tool registry — one entry per @AiCapability with a tool_name
# ---------------------------------------------------------------------------
TOOL_REGISTRY: dict[str, dict[str, Any]] = {
}


def get_tool(name: str) -> dict[str, Any] | None:
    """Look up a registered tool by name."""
    return TOOL_REGISTRY.get(name)


def list_tools() -> list[dict[str, Any]]:
    """Return all registered tools."""
    return list(TOOL_REGISTRY.values())
