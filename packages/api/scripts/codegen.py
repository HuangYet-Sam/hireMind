"""
Code generator for HireMind AI capabilities.

Reads metadata from ``_AI_CAPABILITIES_REGISTRY`` (populated by
``@AiCapability`` decorators) and renders:
  - FastAPI route skeletons  -> app/routers/generated/ai_routes.py
  - Agent Tool registrations  -> app/tools/generated/ai_tools.py

Usage:
    python -m scripts.codegen            # generate everything
    python -m scripts.codegen --routes   # routes only
    python -m scripts.codegen --tools    # tools only
    python -m scripts.codegen --check    # detect drift (exit 1 if stale)
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent  # packages/api/

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
ROUTE_TEMPLATE = "route.py.jinja2"
TOOLS_TEMPLATE = "tools.py.jinja2"

ROUTES_OUTPUT = ROOT / "app" / "routers" / "generated" / "ai_routes.py"
TOOLS_OUTPUT = ROOT / "app" / "tools" / "generated" / "ai_tools.py"

# Modules whose import triggers @AiCapability registration.
_MODULES_TO_IMPORT = [
    "app.decorators.ai_capability",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_importable() -> None:
    """Add ``ROOT`` to ``sys.path`` so ``app.*`` imports work."""
    api_dir = str(ROOT)
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)


def collect_capabilities() -> list[dict]:
    """Import modules that register capabilities and return their metadata."""
    _ensure_importable()

    for mod_name in _MODULES_TO_IMPORT:
        importlib.import_module(mod_name)

    # Import after registration modules so the registry is populated.
    from app.decorators.ai_capability import get_all_capabilities

    caps = get_all_capabilities()
    return list(caps.values())


def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def generate_routes(capabilities: list[dict]) -> str:
    """Render FastAPI route skeletons from *capabilities* metadata."""
    env = _jinja_env()
    tmpl = env.get_template(ROUTE_TEMPLATE)
    return tmpl.render(capabilities=capabilities)


def generate_tool_registrations(capabilities: list[dict]) -> str:
    """Render Agent Tool registration code from *capabilities* metadata."""
    env = _jinja_env()
    tmpl = env.get_template(TOOLS_TEMPLATE)
    return tmpl.render(capabilities=capabilities)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _is_drift(path: Path, content: str) -> bool:
    """Return True when *path* exists but differs from *content*."""
    if not path.exists():
        return True
    return path.read_text(encoding="utf-8") != content


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate FastAPI routes and Tool registrations from @AiCapability metadata",
    )
    parser.add_argument("--routes", action="store_true", help="Generate routes only")
    parser.add_argument("--tools", action="store_true", help="Generate tools only")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Detect drift: exit 1 if generated files are stale",
    )
    args = parser.parse_args(argv)

    generate_all = not args.routes and not args.tools

    capabilities = collect_capabilities()
    print(f"Collected {len(capabilities)} capability(ies) from registry")

    drift = False

    if generate_all or args.routes:
        code = generate_routes(capabilities)
        if args.check:
            if _is_drift(ROUTES_OUTPUT, code):
                print(f"DRIFT detected: {ROUTES_OUTPUT}")
                drift = True
            else:
                print(f"OK: {ROUTES_OUTPUT}")
        else:
            _write(ROUTES_OUTPUT, code)
            print(f"Generated routes → {ROUTES_OUTPUT}")

    if generate_all or args.tools:
        code = generate_tool_registrations(capabilities)
        if args.check:
            if _is_drift(TOOLS_OUTPUT, code):
                print(f"DRIFT detected: {TOOLS_OUTPUT}")
                drift = True
            else:
                print(f"OK: {TOOLS_OUTPUT}")
        else:
            _write(TOOLS_OUTPUT, code)
            print(f"Generated tools → {TOOLS_OUTPUT}")

    if args.check and drift:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
