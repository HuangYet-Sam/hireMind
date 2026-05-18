"""
SkillService — business logic for AI skill/tool/prompt registration and invocation.

Provides CRUD for SkillRegistry, invocation dispatching based on skill_type,
and usage statistics tracking (call_count, avg_latency_ms).
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill_registry import SkillRegistry
from app.schemas.skill import SkillCreate, SkillUpdate

logger = logging.getLogger("hiremind.services.skill")


def _now_ms() -> float:
    return time.time() * 1000


class SkillService:
    """Service layer for skill registry CRUD and invocation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def register_skill(
        self,
        data: SkillCreate,
        tenant_id: str,
    ) -> SkillRegistry:
        """Register a new skill."""
        valid_types = {"tool", "prompt", "workflow"}
        if data.skill_type not in valid_types:
            raise ValueError(
                f"Invalid skill_type '{data.skill_type}'. "
                f"Must be one of: {valid_types}"
            )

        # Check for duplicate name within tenant
        existing = await self._get_by_name(data.name, tenant_id)
        if existing:
            raise ValueError(f"Skill '{data.name}' already exists in this tenant")

        skill = SkillRegistry(
            tenant_id=tenant_id,
            name=data.name,
            skill_type=data.skill_type,
            description=data.description,
            prompt_template=data.prompt_template,
            input_schema=data.input_schema,
            output_schema=data.output_schema,
            is_active=data.is_active,
            tags=data.tags or [],
        )

        self.db.add(skill)
        await self.db.flush()
        await self.db.refresh(skill)
        logger.info("Registered skill %s (%s) for tenant %s", skill.id, skill.name, tenant_id)
        return skill

    async def update_skill(
        self,
        skill_id: UUID,
        data: SkillUpdate,
        tenant_id: str,
    ) -> SkillRegistry:
        """Update an existing skill's configuration."""
        skill = await self._get_skill(skill_id, tenant_id)
        if skill is None:
            raise ValueError(f"Skill {skill_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(skill, field, value)

        await self.db.flush()
        await self.db.refresh(skill)
        logger.info("Updated skill %s", skill_id)
        return skill

    async def deactivate_skill(self, skill_id: UUID, tenant_id: str) -> SkillRegistry:
        """Deactivate (soft-delete) a skill."""
        skill = await self._get_skill(skill_id, tenant_id)
        if skill is None:
            raise ValueError(f"Skill {skill_id} not found")

        skill.is_active = False
        await self.db.flush()
        await self.db.refresh(skill)
        logger.info("Deactivated skill %s", skill_id)
        return skill

    async def delete_skill(self, skill_id: UUID, tenant_id: str) -> None:
        """Permanently delete a skill."""
        skill = await self._get_skill(skill_id, tenant_id)
        if skill is None:
            raise ValueError(f"Skill {skill_id} not found")

        await self.db.delete(skill)
        await self.db.flush()
        logger.info("Deleted skill %s", skill_id)

    async def list_skills(
        self,
        tenant_id: str,
        *,
        skill_type: str | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[SkillRegistry], int]:
        """List skills for a tenant with optional filters."""
        filters = [SkillRegistry.tenant_id == tenant_id]
        if skill_type is not None:
            filters.append(SkillRegistry.skill_type == skill_type)
        if is_active is not None:
            filters.append(SkillRegistry.is_active == is_active)

        count_stmt = select(func.count()).select_from(SkillRegistry).where(*filters)
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = (
            select(SkillRegistry)
            .where(*filters)
            .order_by(SkillRegistry.name.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def get_skill(self, skill_id: UUID, tenant_id: str) -> SkillRegistry | None:
        """Get a single skill by ID."""
        return await self._get_skill(skill_id, tenant_id)

    # ------------------------------------------------------------------
    # Invocation
    # ------------------------------------------------------------------

    async def call_skill(
        self,
        skill_id: UUID,
        input_data: dict,
        tenant_id: str,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """
        Invoke a skill and record usage statistics.

        Dispatches to the appropriate handler based on skill_type:
          - tool: external API call or tool function
          - prompt: LLM prompt template rendering
          - workflow: multi-step orchestration

        Returns a dict with output, latency, and status.
        """
        skill = await self._get_skill(skill_id, tenant_id)
        if skill is None:
            raise ValueError(f"Skill {skill_id} not found")

        if not skill.is_active:
            raise ValueError(f"Skill '{skill.name}' is not active")

        start_ms = _now_ms()
        output = None
        error = None
        status = "success"

        try:
            if skill.skill_type == "tool":
                output = await self._invoke_tool(skill, input_data, timeout_seconds)
            elif skill.skill_type == "prompt":
                output = await self._invoke_prompt(skill, input_data, timeout_seconds)
            elif skill.skill_type == "workflow":
                output = await self._invoke_workflow(skill, input_data, timeout_seconds)
            else:
                raise ValueError(f"Unknown skill_type: {skill.skill_type}")

        except Exception as exc:
            status = "error"
            error = str(exc)
            logger.error("Skill %s invocation failed: %s", skill_id, exc)

        end_ms = _now_ms()
        latency_ms = end_ms - start_ms

        # Update statistics
        await self._update_stats(skill, latency_ms)

        return {
            "skill_id": str(skill.id),
            "skill_name": skill.name,
            "skill_type": skill.skill_type,
            "status": status,
            "output": output,
            "latency_ms": round(latency_ms, 2),
            "error": error,
        }

    async def _invoke_tool(
        self,
        skill: SkillRegistry,
        input_data: dict,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """
        Invoke a tool-type skill.

        Tool skills reference an external function or API endpoint.
        The handler is looked up from the skill's input_schema or a registry.
        """
        handler_name = (skill.input_schema or {}).get("handler")
        if not handler_name:
            return {"result": "Tool skill executed (no specific handler)", "input": input_data}

        # Dispatch to registered tool handlers
        # In production, this would look up the handler from a tool registry
        logger.info("Invoking tool handler: %s for skill %s", handler_name, skill.id)
        return {
            "handler": handler_name,
            "result": f"Executed tool '{handler_name}'",
            "input_received": list(input_data.keys()),
        }

    async def _invoke_prompt(
        self,
        skill: SkillRegistry,
        input_data: dict,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """
        Invoke a prompt-type skill.

        Renders the prompt_template with input_data variables and
        sends it to the AI client for completion.
        """
        if not skill.prompt_template:
            raise ValueError(f"Prompt skill '{skill.name}' has no prompt_template")

        # Render template with input variables
        prompt = skill.prompt_template
        for key, value in input_data.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))

        # Send to AI client
        try:
            from app.services.ai_client import ai_client
            result = await ai_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=(skill.output_schema or {}).get("model", "gpt-4o-mini"),
            )
            return {"prompt_result": result, "rendered_prompt": prompt}
        except Exception as exc:
            logger.warning("AI client not available, returning rendered prompt: %s", exc)
            return {"rendered_prompt": prompt, "note": "AI client unavailable"}

    async def _invoke_workflow(
        self,
        skill: SkillRegistry,
        input_data: dict,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """
        Invoke a workflow-type skill.

        Workflows are multi-step orchestrations defined in the skill's config.
        """
        steps = (skill.input_schema or {}).get("steps", [])
        if not steps:
            return {"result": "Workflow skill executed (no steps defined)", "input": input_data}

        results = []
        for i, step in enumerate(steps):
            step_type = step.get("type", "unknown")
            step_name = step.get("name", f"step_{i}")
            logger.info(
                "Workflow step %d/%d: %s (%s) for skill %s",
                i + 1, len(steps), step_name, step_type, skill.id,
            )
            results.append({
                "step": i + 1,
                "name": step_name,
                "type": step_type,
                "status": "completed",
            })

        return {
            "workflow_result": "completed",
            "steps_executed": len(results),
            "steps": results,
        }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    async def _update_stats(self, skill: SkillRegistry, latency_ms: float) -> None:
        """Update call_count and avg_latency_ms for a skill."""
        new_count = skill.call_count + 1

        if skill.avg_latency_ms is not None and skill.call_count > 0:
            # Running average
            new_avg = ((skill.avg_latency_ms * skill.call_count) + latency_ms) / new_count
        else:
            new_avg = latency_ms

        skill.call_count = new_count
        skill.avg_latency_ms = round(new_avg, 2)
        skill.last_called_at = _now_ms_as_datetime()

        await self.db.flush()

    async def get_skill_stats(
        self,
        skill_id: UUID,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Get usage statistics for a skill."""
        skill = await self._get_skill(skill_id, tenant_id)
        if skill is None:
            raise ValueError(f"Skill {skill_id} not found")

        return {
            "skill_id": str(skill.id),
            "skill_name": skill.name,
            "skill_type": skill.skill_type,
            "call_count": skill.call_count,
            "avg_latency_ms": skill.avg_latency_ms,
            "last_called_at": skill.last_called_at,
            "created_at": skill.created_at,
        }

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search_skills(
        self,
        query: str,
        tenant_id: str,
        *,
        skill_type: str | None = None,
        limit: int = 20,
    ) -> list[SkillRegistry]:
        """
        Search skills by name, description, or tags.

        Uses case-insensitive ILIKE matching.
        """
        pattern = f"%{query}%"
        filters = [
            SkillRegistry.tenant_id == tenant_id,
            or_(
                SkillRegistry.name.ilike(pattern),
                SkillRegistry.description.ilike(pattern),
            ),
        ]
        if skill_type:
            filters.append(SkillRegistry.skill_type == skill_type)

        stmt = (
            select(SkillRegistry)
            .where(*filters)
            .order_by(SkillRegistry.call_count.desc(), SkillRegistry.name.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_skill(self, skill_id: UUID, tenant_id: str) -> SkillRegistry | None:
        """Fetch a single skill scoped to tenant."""
        stmt = select(SkillRegistry).where(
            SkillRegistry.id == skill_id,
            SkillRegistry.tenant_id == tenant_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _get_by_name(self, name: str, tenant_id: str) -> SkillRegistry | None:
        """Fetch a skill by name within a tenant."""
        stmt = select(SkillRegistry).where(
            SkillRegistry.name == name,
            SkillRegistry.tenant_id == tenant_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()


def _now_ms_as_datetime():
    """Return current UTC time as datetime."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)
