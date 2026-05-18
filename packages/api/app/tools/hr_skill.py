"""
HR Skill Agent Tool.

Exposes AI skill management capabilities as Agent Tools
via the ``@AiCapability`` decorator.

Registered capabilities:
  - ``hr_skill_register``   — Register a new AI skill
  - ``hr_skill_list``       — List registered skills
  - ``hr_skill_call``       — Invoke a skill
  - ``hr_skill_stats``      — View skill usage statistics
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.decorators.ai_capability import AiCapability

logger = logging.getLogger("hiremind.tools.hr_skill")


# ---------------------------------------------------------------------------
# Tool: Register Skill — 注册 Skill
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_skill_register",
    name="HR Skill Register",
    endpoint="/api/v1/skills/",
    method="POST",
    tool_name="hr_skill_register",
    permissions=["skill:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_skill_register_v1",
    description="Register a new AI skill (tool, prompt, or workflow) in the system",
    request_model="SkillCreate",
    response_model="SkillResponse",
    rate_limit="30/minute",
    data_classification="L2",
    audit_level="detailed",
    tags=["hr", "skill", "register"],
    timeout=10.0,
)
async def register_skill(
    *,
    name: str,
    skill_type: str,
    description: str | None = None,
    prompt_template: str | None = None,
    input_schema: dict | None = None,
    output_schema: dict | None = None,
    is_active: bool = True,
    tags: list[str] | None = None,
    tenant_id: str = "default",
) -> dict[str, Any]:
    """
    Register a new AI skill.

    Args:
        name: Skill display name.
        skill_type: One of tool/prompt/workflow.
        description: Skill description.
        prompt_template: Prompt template with {{variable}} placeholders (for prompt/workflow types).
        input_schema: JSON Schema for input validation.
        output_schema: JSON Schema for output validation.
        is_active: Whether to activate immediately.
        tags: Tags for categorization.
        tenant_id: Tenant scope identifier.

    Returns:
        Dict with registered skill details.
    """
    from app.dependencies import get_db
    from app.schemas.skill import SkillCreate
    from app.services.skill_service import SkillService

    async for session in get_db():
        svc = SkillService(session)
        create_data = SkillCreate(
            name=name,
            skill_type=skill_type,
            description=description,
            prompt_template=prompt_template,
            input_schema=input_schema,
            output_schema=output_schema,
            is_active=is_active,
            tags=tags,
        )
        try:
            skill = await svc.register_skill(
                data=create_data,
                tenant_id=tenant_id,
            )
            return {
                "status": "success",
                "skill_id": str(skill.id),
                "name": skill.name,
                "skill_type": skill.skill_type,
                "is_active": skill.is_active,
            }
        except ValueError as exc:
            return {"error": str(exc), "name": name}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: List Skills — 查看 Skill 列表
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_skill_list",
    name="HR Skill List",
    endpoint="/api/v1/skills/",
    method="GET",
    tool_name="hr_skill_list",
    permissions=["skill:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_skill_list_v1",
    description="List registered skills with optional type filter",
    request_model="SkillListRequest",
    response_model="SkillListResponse",
    rate_limit="60/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "skill", "list"],
    timeout=10.0,
)
async def list_skills(
    tenant_id: str,
    *,
    skill_type: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """
    List registered skills.

    Args:
        tenant_id: Tenant scope identifier.
        skill_type: Optional filter by type (tool/prompt/workflow).
        is_active: Optional filter by active status.
        page: Page number (1-based).
        page_size: Items per page.

    Returns:
        Dict with paginated skill list.
    """
    from app.dependencies import get_db
    from app.services.skill_service import SkillService

    async for session in get_db():
        svc = SkillService(session)
        offset = (page - 1) * page_size
        items, total = await svc.list_skills(
            tenant_id=tenant_id,
            skill_type=skill_type,
            is_active=is_active,
            offset=offset,
            limit=page_size,
        )
        return {
            "status": "success",
            "items": [
                {
                    "skill_id": str(s.id),
                    "name": s.name,
                    "skill_type": s.skill_type,
                    "is_active": s.is_active,
                    "call_count": s.call_count,
                    "avg_latency_ms": s.avg_latency_ms,
                    "last_called_at": str(s.last_called_at) if s.last_called_at else None,
                    "tags": s.tags,
                }
                for s in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: Call Skill — 调用 Skill
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_skill_call",
    name="HR Skill Call",
    endpoint="/api/v1/skills/{skill_id}/call",
    method="POST",
    tool_name="hr_skill_call",
    permissions=["skill:execute"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_skill_call_v1",
    description="Invoke a registered skill with input data and return results",
    request_model="SkillCallRequest",
    response_model="SkillCallResponse",
    rate_limit="30/minute",
    data_classification="L3",
    audit_level="detailed",
    tags=["hr", "skill", "call", "execute"],
    timeout=30.0,
)
async def call_skill(
    skill_id: str,
    tenant_id: str,
    *,
    input_data: dict,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    """
    Invoke a registered skill.

    Args:
        skill_id: UUID of the skill to invoke.
        tenant_id: Tenant scope identifier.
        input_data: Input data for the skill.
        timeout_seconds: Optional execution timeout override.

    Returns:
        Dict with skill execution results.
    """
    from app.dependencies import get_db
    from app.services.skill_service import SkillService

    async for session in get_db():
        svc = SkillService(session)
        try:
            result = await svc.call_skill(
                skill_id=UUID(skill_id),
                input_data=input_data,
                tenant_id=tenant_id,
                timeout_seconds=timeout_seconds,
            )
            return result
        except ValueError as exc:
            return {"error": str(exc), "skill_id": skill_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: Get Skill Stats — 查看调用统计
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_skill_stats",
    name="HR Skill Stats",
    endpoint="/api/v1/skills/{skill_id}/stats",
    method="GET",
    tool_name="hr_skill_stats",
    permissions=["skill:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_skill_stats_v1",
    description="View usage statistics for a registered skill",
    request_model="SkillStatsRequest",
    response_model="SkillStatsResponse",
    rate_limit="60/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "skill", "stats"],
    timeout=10.0,
)
async def get_skill_stats(
    skill_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    View skill usage statistics.

    Args:
        skill_id: UUID of the skill.
        tenant_id: Tenant scope identifier.

    Returns:
        Dict with usage statistics.
    """
    from app.dependencies import get_db
    from app.services.skill_service import SkillService

    async for session in get_db():
        svc = SkillService(session)
        try:
            stats = await svc.get_skill_stats(
                skill_id=UUID(skill_id),
                tenant_id=tenant_id,
            )
            return {
                "status": "success",
                **stats,
            }
        except ValueError as exc:
            return {"error": str(exc), "skill_id": skill_id}

    return {"error": "Database session unavailable"}
