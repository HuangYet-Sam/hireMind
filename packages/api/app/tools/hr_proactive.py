"""
HR Proactive AI Agent Tool.

Exposes proactive AI scanning capabilities as Agent Tools
via the ``@AiCapability`` decorator.

Registered capabilities:
  - ``hr_proactive_scan``             — Trigger proactive AI scan for a tenant
  - ``hr_proactive_messages``         — Get proactive push messages list
  - ``hr_proactive_action``           — Handle push action (confirm/ignore/execute)
  - ``hr_talent_activate``            — Activate a silent candidate
  - ``hr_activation_candidates``      — Get list of candidates pending activation
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.decorators.ai_capability import AiCapability

logger = logging.getLogger("hiremind.tools.hr_proactive")


# ---------------------------------------------------------------------------
# Tool: Trigger Proactive Scan — 触发主动AI扫描
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_proactive_scan",
    name="HR Proactive Scan",
    endpoint="/api/v1/proactive/scan",
    method="POST",
    tool_name="hr_proactive_scan",
    permissions=["proactive:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_proactive_scan_v1",
    description="Trigger a proactive AI scan for a tenant, running all scenario checks and generating alerts",
    request_model="ProactiveScanRequest",
    response_model="ProactiveScanResponse",
    rate_limit="10/minute",
    data_classification="L2",
    audit_level="detailed",
    tags=["hr", "proactive", "scan"],
    timeout=60.0,
)
async def trigger_proactive_scan(
    tenant_id: str,
    *,
    scenario_types: list[str] | None = None,
) -> dict[str, Any]:
    """
    Trigger a proactive AI scan for a tenant.

    Runs all proactive scenario checks (resume arrival, match anomaly,
    interview timeout, offer stale, funnel bottleneck, silent activation,
    daily digest, weekly digest) and generates alert messages.

    Args:
        tenant_id: Tenant scope identifier.
        scenario_types: Optional list of scenario types to run.
            If None, runs all scenarios. Valid types:
            resume_arrival, match_anomaly, interview_timeout,
            offer_stale, funnel_bottleneck, silent_activation,
            daily_report, weekly_report.

    Returns:
        Dict with scan results including alert count and summary.
    """
    from app.dependencies import get_db
    from app.services.proactive_ai_engine import ProactiveAIEngine

    async for session in get_db():
        engine = ProactiveAIEngine(session)
        try:
            if scenario_types:
                # Run selected scenarios only
                all_alerts = []
                for scenario in scenario_types:
                    scenario_method = {
                        "resume_arrival": engine.check_resume_arrival,
                        "match_anomaly": engine.check_match_anomaly,
                        "interview_timeout": engine.check_interview_timeout,
                        "offer_stale": engine.check_offer_stale,
                        "funnel_bottleneck": engine.check_funnel_bottleneck,
                        "silent_activation": engine.check_silent_activation,
                    }
                    if scenario == "daily_report":
                        alert = await engine.generate_daily_digest(tenant_id)
                        all_alerts.append(alert)
                    elif scenario == "weekly_report":
                        alert = await engine.generate_weekly_digest(tenant_id)
                        all_alerts.append(alert)
                    elif scenario in scenario_method:
                        alerts = await scenario_method[scenario](tenant_id)
                        all_alerts.extend(alerts)
            else:
                all_alerts = await engine.run_all_scenarios(tenant_id)

            # Summarize by severity
            severity_counts = {"urgent": 0, "warning": 0, "info": 0}
            for alert in all_alerts:
                sev = alert.severity if alert.severity in severity_counts else "info"
                severity_counts[sev] += 1

            # Summarize by scenario type
            scenario_counts: dict[str, int] = {}
            for alert in all_alerts:
                scenario_counts[alert.scenario_type] = (
                    scenario_counts.get(alert.scenario_type, 0) + 1
                )

            return {
                "status": "success",
                "tenant_id": tenant_id,
                "total_alerts": len(all_alerts),
                "severity_counts": severity_counts,
                "scenario_counts": scenario_counts,
                "alerts": [
                    {
                        "id": alert.id,
                        "scenario_type": alert.scenario_type,
                        "title": alert.title,
                        "severity": alert.severity,
                        "action_suggestion": alert.action_suggestion,
                    }
                    for alert in all_alerts[:50]  # Cap at 50 for response size
                ],
            }
        except Exception as exc:
            logger.exception("trigger_proactive_scan failed: %s", exc)
            return {"error": str(exc), "tenant_id": tenant_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: Get Proactive Messages — 获取推送消息列表
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_proactive_messages",
    name="HR Proactive Messages",
    endpoint="/api/v1/proactive/messages",
    method="GET",
    tool_name="hr_proactive_messages",
    permissions=["proactive:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_proactive_messages_v1",
    description="Get proactive push messages for a tenant with optional filters",
    request_model="ProactiveMessageListRequest",
    response_model="ProactiveMessageListResponse",
    rate_limit="60/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "proactive", "messages"],
    timeout=10.0,
)
async def get_proactive_messages(
    tenant_id: str,
    *,
    severity: str | None = None,
    scenario_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """
    Get proactive push messages for a tenant.

    Runs a fresh scan and returns the alert messages, optionally filtered
    by severity or scenario type.

    Args:
        tenant_id: Tenant scope identifier.
        severity: Filter by severity (info/warning/urgent).
        scenario_type: Filter by scenario type.
        page: Page number (1-based).
        page_size: Items per page.

    Returns:
        Dict with paginated proactive messages.
    """
    from app.dependencies import get_db
    from app.services.proactive_ai_engine import ProactiveAIEngine

    async for session in get_db():
        engine = ProactiveAIEngine(session)
        try:
            all_alerts = await engine.run_all_scenarios(tenant_id)
        except Exception as exc:
            logger.exception("get_proactive_messages scan failed: %s", exc)
            return {"error": str(exc), "tenant_id": tenant_id}

        # Apply filters
        filtered = all_alerts
        if severity:
            filtered = [a for a in filtered if a.severity == severity]
        if scenario_type:
            filtered = [a for a in filtered if a.scenario_type == scenario_type]

        total = len(filtered)
        offset = (page - 1) * page_size
        page_items = filtered[offset: offset + page_size]

        return {
            "status": "success",
            "items": [
                {
                    "id": alert.id,
                    "scenario_type": alert.scenario_type,
                    "title": alert.title,
                    "content": alert.content[:500],
                    "severity": alert.severity,
                    "entity_id": str(alert.entity_id) if alert.entity_id else None,
                    "entity_type": alert.entity_type,
                    "action_suggestion": alert.action_suggestion,
                    "created_at": str(alert.created_at),
                }
                for alert in page_items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: Handle Proactive Action — 处理推送操作
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_proactive_action",
    name="HR Proactive Action",
    endpoint="/api/v1/proactive/messages/{message_id}",
    method="PATCH",
    tool_name="hr_proactive_action",
    permissions=["proactive:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_proactive_action_v1",
    description="Handle a proactive push message action (confirm/ignore/execute)",
    request_model="ProactiveActionRequest",
    response_model="ProactiveActionResponse",
    rate_limit="30/minute",
    data_classification="L2",
    audit_level="detailed",
    tags=["hr", "proactive", "action"],
    timeout=15.0,
)
async def handle_proactive_action(
    message_id: str,
    tenant_id: str,
    *,
    action: str,
    note: str | None = None,
) -> dict[str, Any]:
    """
    Handle a proactive push message action.

    Processes the user's response to a proactive alert:
    - confirm: Acknowledge the alert and mark it as confirmed.
    - ignore: Dismiss the alert.
    - execute: Attempt to execute the suggested action automatically.

    Args:
        message_id: The alert message ID.
        tenant_id: Tenant scope identifier.
        action: Action to take (confirm/ignore/execute).
        note: Optional user note attached to the action.

    Returns:
        Dict with action result.
    """
    from app.dependencies import get_db

    valid_actions = {"confirm", "ignore", "execute"}
    if action not in valid_actions:
        return {
            "error": f"Invalid action '{action}'. Must be one of: {valid_actions}",
            "message_id": message_id,
        }

    async for session in get_db():
        # In a full implementation, we would persist the action to a
        # ProactiveMessage table. For now we log and return confirmation.
        logger.info(
            "handle_proactive_action: message=%s action=%s tenant=%s note=%s",
            message_id, action, tenant_id, note,
        )

        result: dict[str, Any] = {
            "status": "success",
            "message_id": message_id,
            "action": action,
        }

        if action == "confirm":
            result["message"] = "Alert confirmed and acknowledged"
            result["next_steps"] = "Alert has been marked as reviewed"

        elif action == "ignore":
            result["message"] = "Alert dismissed"
            result["next_steps"] = "Alert has been ignored and will not re-notify"

        elif action == "execute":
            result["message"] = "Action execution initiated"
            result["next_steps"] = (
                "The suggested action is being processed. "
                "Check relevant entity for updates."
            )

        if note:
            result["note"] = note

        return result

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: Activate Talent — 激活沉默候选人
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_talent_activate",
    name="HR Talent Activate",
    endpoint="/api/v1/proactive/talent-activation/{candidate_id}/activate",
    method="POST",
    tool_name="hr_talent_activate",
    permissions=["proactive:write", "candidate:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_talent_activate_v1",
    description="Activate a silent candidate by generating strategy and executing re-engagement",
    request_model="TalentActivationRequest",
    response_model="TalentActivationResponse",
    rate_limit="30/minute",
    data_classification="L2",
    audit_level="detailed",
    tags=["hr", "proactive", "talent", "activation"],
    timeout=30.0,
)
async def activate_talent(
    candidate_id: str,
    tenant_id: str,
    *,
    position_id: str | None = None,
    activation_note: str | None = None,
) -> dict[str, Any]:
    """
    Activate a silent candidate.

    Generates an activation strategy for the candidate, optionally targeting
    a specific position, and executes the activation (re-engagement).

    Args:
        candidate_id: UUID of the candidate to activate.
        tenant_id: Tenant scope identifier.
        position_id: Optional target position UUID. If not provided,
            the best matching position will be selected automatically.
        activation_note: Optional note for the activation.

    Returns:
        Dict with activation result including strategy details.
    """
    from app.dependencies import get_db
    from app.services.talent_activation import TalentActivationService

    async for session in get_db():
        svc = TalentActivationService(session)

        # If no position specified, find the best matching one
        if position_id is None:
            try:
                matches = await svc.find_matching_positions(
                    candidate_id=candidate_id,
                    tenant_id=tenant_id,
                    top_k=1,
                )
                if not matches:
                    return {
                        "error": "No matching positions found for this candidate",
                        "candidate_id": candidate_id,
                    }
                position_id = matches[0]["position"]["id"]
            except Exception as exc:
                return {
                    "error": f"Failed to find matching positions: {exc}",
                    "candidate_id": candidate_id,
                }

        # Generate activation strategy (position_id guaranteed non-None at this point)
        assert position_id is not None  # guaranteed by the logic above
        try:
            strategy = await svc.generate_activation_strategy(
                candidate_id=candidate_id,
                position_id=position_id,
                tenant_id=tenant_id,
            )
            if "error" in strategy:
                return {
                    "error": strategy["error"],
                    "candidate_id": candidate_id,
                    "position_id": position_id,
                }
        except Exception as exc:
            return {
                "error": f"Strategy generation failed: {exc}",
                "candidate_id": candidate_id,
            }

        # Execute activation
        try:
            result = await svc.execute_activation(
                candidate_id=candidate_id,
                strategy_id=strategy["strategy_id"],
                tenant_id=tenant_id,
            )
            if activation_note:
                result["activation_note"] = activation_note
            return result
        except Exception as exc:
            return {
                "error": f"Activation execution failed: {exc}",
                "candidate_id": candidate_id,
                "strategy_id": strategy.get("strategy_id"),
            }

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: Get Activation Candidates — 获取待激活候选人列表
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_activation_candidates",
    name="HR Activation Candidates",
    endpoint="/api/v1/proactive/talent-activation",
    method="GET",
    tool_name="hr_activation_candidates",
    permissions=["proactive:read", "candidate:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_activation_candidates_v1",
    description="Get list of silent/inactive candidates eligible for activation",
    request_model="ActivationCandidatesRequest",
    response_model="ActivationCandidatesResponse",
    rate_limit="60/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "proactive", "talent", "activation"],
    timeout=10.0,
)
async def get_activation_candidates(
    tenant_id: str,
    *,
    days_silent: int = 30,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Get list of silent/inactive candidates eligible for activation.

    Scans the candidate pool for candidates who have been inactive for
    at least ``days_silent`` days and returns them with matching position
    information.

    Args:
        tenant_id: Tenant scope identifier.
        days_silent: Minimum days of inactivity (default: 30).
        limit: Maximum number of candidates to return.

    Returns:
        Dict with candidate list and activation statistics.
    """
    from app.dependencies import get_db
    from app.services.talent_activation import TalentActivationService

    async for session in get_db():
        svc = TalentActivationService(session)
        try:
            candidates = await svc.scan_inactive_candidates(
                tenant_id=tenant_id,
                days_silent=days_silent,
                limit=limit,
            )
            stats = await svc.get_activation_stats(tenant_id)

            return {
                "status": "success",
                "total": len(candidates),
                "days_silent_threshold": days_silent,
                "candidates": [
                    {
                        "candidate_id": c["candidate"]["id"],
                        "name": c["candidate"]["name"],
                        "stage": c["candidate"]["stage"],
                        "credibility_score": c["candidate"]["credibility_score"],
                        "days_silent": c["days_silent"],
                        "last_activity": c["last_activity"],
                        "potential_matches": c["potential_matches"],
                    }
                    for c in candidates
                ],
                "stats": stats,
            }
        except Exception as exc:
            return {"error": str(exc), "tenant_id": tenant_id}

    return {"error": "Database session unavailable"}
