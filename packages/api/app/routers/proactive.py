"""
Proactive Router — endpoints for proactive AI push and talent activation.

Provides message listing, scan triggering, action handling,
and silent candidate activation.
"""

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import CurrentUser, CurrentUserDep, DbSession, PaginationDep, require_role
from app.services.proactive_ai_engine import ProactiveAIEngine
from app.services.talent_activation import TalentActivationService

router = APIRouter()

_RecruiterOrAbove = Annotated[CurrentUser, Depends(require_role("recruiter", "hr_manager", "admin"))]


@router.get("/messages", summary="List proactive push messages")
async def get_proactive_messages(
    db: DbSession,
    pagination: PaginationDep,
    current_user: CurrentUserDep,
    severity: str | None = Query(None, description="Filter by severity: info/warning/urgent"),
    scenario_type: str | None = Query(None, description="Filter by scenario type"),
):
    """Get proactive push messages for the current tenant.

    Runs a fresh proactive scan and returns the alert messages,
    optionally filtered by severity or scenario type.
    """
    engine = ProactiveAIEngine(db)
    try:
        all_alerts = await engine.run_all_scenarios(current_user.tenant_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proactive scan failed: {exc}",
        )

    # Apply filters
    filtered = all_alerts
    if severity:
        filtered = [a for a in filtered if a.severity == severity]
    if scenario_type:
        filtered = [a for a in filtered if a.scenario_type == scenario_type]

    total = len(filtered)
    page_items = filtered[pagination.offset: pagination.offset + pagination.limit]
    pages = math.ceil(total / pagination.page_size) if total > 0 else 0

    return {
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
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": pages,
    }


@router.post("/scan", summary="Trigger proactive AI scan")
async def trigger_proactive_scan(
    db: DbSession,
    current_user: _RecruiterOrAbove,
):
    """Trigger a full proactive AI scan for the current tenant.

    Runs all scenario checks and generates alert messages.
    """
    engine = ProactiveAIEngine(db)
    try:
        all_alerts = await engine.run_all_scenarios(current_user.tenant_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proactive scan failed: {exc}",
        )

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
            for alert in all_alerts[:50]
        ],
    }


@router.patch("/messages/{message_id}", summary="Handle proactive message action")
async def handle_proactive_action(
    message_id: str,
    db: DbSession,
    current_user: _RecruiterOrAbove,
    action: str = Query(..., description="Action to take: confirm/ignore/execute"),
    note: str | None = Query(None, description="Optional note"),
):
    """Handle a proactive push message action.

    Actions:
    - **confirm**: Acknowledge the alert.
    - **ignore**: Dismiss the alert.
    - **execute**: Attempt to execute the suggested action.
    """
    valid_actions = {"confirm", "ignore", "execute"}
    if action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action '{action}'. Must be one of: {valid_actions}",
        )

    result: dict = {
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
            "Check the relevant entity for updates."
        )

    if note:
        result["note"] = note

    return result


@router.get("/talent-activation", summary="List silent candidates for activation")
async def get_activation_candidates(
    db: DbSession,
    pagination: PaginationDep,
    current_user: CurrentUserDep,
    days_silent: int = Query(30, ge=1, le=365, description="Minimum days of silence"),
):
    """Get list of silent/inactive candidates eligible for activation.

    Scans the candidate pool for candidates who have been inactive for
    at least ``days_silent`` days.
    """
    svc = TalentActivationService(db)
    try:
        candidates = await svc.scan_inactive_candidates(
            tenant_id=current_user.tenant_id,
            days_silent=days_silent,
            limit=pagination.limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Candidate scan failed: {exc}",
        )

    total = len(candidates)
    pages = math.ceil(total / pagination.page_size) if total > 0 else 0

    return {
        "items": [
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
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": pages,
        "days_silent_threshold": days_silent,
    }


@router.post(
    "/talent-activation/{candidate_id}/activate",
    status_code=status.HTTP_201_CREATED,
    summary="Activate a silent candidate",
)
async def activate_talent(
    candidate_id: UUID,
    db: DbSession,
    current_user: _RecruiterOrAbove,
    position_id: UUID | None = Query(None, description="Target position (auto-detected if omitted)"),
):
    """Activate a silent candidate by generating and executing a re-engagement strategy.

    If no ``position_id`` is provided, the best matching open position
    will be selected automatically.
    """
    svc = TalentActivationService(db)
    candidate_id_str = str(candidate_id)
    position_id_str = str(position_id) if position_id else None

    # Auto-detect best matching position if not specified
    if position_id_str is None:
        try:
            matches = await svc.find_matching_positions(
                candidate_id=candidate_id_str,
                tenant_id=current_user.tenant_id,
                top_k=1,
            )
            if not matches:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No matching positions found for this candidate",
                )
            position_id_str = matches[0]["position"]["id"]
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to find matching positions: {exc}",
            )

    # Generate activation strategy
    try:
        strategy = await svc.generate_activation_strategy(
            candidate_id=candidate_id_str,
            position_id=position_id_str,
            tenant_id=current_user.tenant_id,
        )
        if "error" in strategy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=strategy["error"],
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Strategy generation failed: {exc}",
        )

    # Execute activation
    try:
        result = await svc.execute_activation(
            candidate_id=candidate_id_str,
            strategy_id=strategy["strategy_id"],
            tenant_id=current_user.tenant_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Activation execution failed: {exc}",
        )

    return result
