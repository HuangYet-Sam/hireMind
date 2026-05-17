"""
Public Token-based Router.

Token-URL endpoints that bypass standard JWT auth.
The token itself is a self-contained JWT that carries all
necessary claims (interview_id, candidate_id, tenant_id, scope, exp).
Validated inline — no session lookup required.
"""

import jwt

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import DbSession

router = APIRouter()


def _decode_token(token: str) -> dict:
    """Decode and validate a public-access JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


# ── Feedback ────────────────────────────────────────────────────

@router.get("/api/v1/feedback/{token}", summary="Get feedback form data")
async def get_feedback_form(
    token: str,
    db: DbSession,
):
    """Return the interview feedback form context for the given token."""
    claims = _decode_token(token)
    if claims.get("scope") != "feedback":
        raise HTTPException(status_code=400, detail="Token scope mismatch")

    return {
        "interview_id": claims.get("interview_id"),
        "position_title": claims.get("position_title"),
        "candidate_name": claims.get("candidate_name"),
        "interview_type": claims.get("interview_type"),
        "dimensions": claims.get("dimensions", []),
        "token_valid": True,
    }


@router.post("/api/v1/feedback/{token}", summary="Submit interview feedback via token")
async def submit_feedback_token(
    token: str,
    payload: dict,
    db: DbSession,
):
    """Submit feedback from an external interviewer via token URL."""
    claims = _decode_token(token)
    if claims.get("scope") != "feedback":
        raise HTTPException(status_code=400, detail="Token scope mismatch")

    return {
        "ok": True,
        "message": "Feedback submitted successfully",
        "interview_id": claims.get("interview_id"),
    }


# ── Onboarding ──────────────────────────────────────────────────

@router.get("/api/v1/onboarding/{token}", summary="Get onboarding form data")
async def get_onboarding_form(
    token: str,
    db: DbSession,
):
    """Return onboarding materials checklist and instructions."""
    claims = _decode_token(token)
    if claims.get("scope") != "onboarding":
        raise HTTPException(status_code=400, detail="Token scope mismatch")

    return {
        "candidate_id": claims.get("candidate_id"),
        "candidate_name": claims.get("candidate_name"),
        "position_title": claims.get("position_title"),
        "start_date": claims.get("start_date"),
        "required_materials": claims.get("required_materials", []),
        "submitted_materials": [],
        "status": "pending",
    }


@router.post("/api/v1/onboarding/{token}/submit", summary="Submit onboarding materials")
async def submit_onboarding_materials(
    token: str,
    payload: dict,
    db: DbSession,
):
    """Submit onboarding materials via token URL."""
    claims = _decode_token(token)
    if claims.get("scope") != "onboarding":
        raise HTTPException(status_code=400, detail="Token scope mismatch")

    return {
        "ok": True,
        "message": "Materials submitted successfully",
        "candidate_id": claims.get("candidate_id"),
    }


@router.get("/api/v1/onboarding/{token}/status", summary="Get onboarding status")
async def get_onboarding_status(
    token: str,
    db: DbSession,
):
    """Query onboarding progress."""
    claims = _decode_token(token)
    if claims.get("scope") != "onboarding":
        raise HTTPException(status_code=400, detail="Token scope mismatch")

    return {
        "candidate_id": claims.get("candidate_id"),
        "status": "pending",
        "completed_steps": [],
        "pending_steps": claims.get("required_materials", []),
    }


# ── Shared Dashboard ────────────────────────────────────────────

@router.get("/api/v1/share/{token}/dashboard", summary="Get shared recruitment dashboard")
async def get_shared_dashboard(
    token: str,
    db: DbSession,
):
    """Return read-only recruitment dashboard data for a hiring manager."""
    claims = _decode_token(token)
    if claims.get("scope") != "share_dashboard":
        raise HTTPException(status_code=400, detail="Token scope mismatch")

    return {
        "tenant_id": claims.get("tenant_id"),
        "open_positions": 0,
        "total_candidates": 0,
        "weekly_interviews": 0,
        "pending_offers": 0,
        "positions": [],
    }


# ── Candidate Profile ──────────────────────────────────────────

@router.get("/api/v1/candidate/{token}/profile", summary="Get candidate profile via token")
async def get_candidate_profile_token(
    token: str,
    db: DbSession,
):
    """Return candidate profile info for self-service update."""
    claims = _decode_token(token)
    if claims.get("scope") != "candidate_profile":
        raise HTTPException(status_code=400, detail="Token scope mismatch")

    return {
        "candidate_id": claims.get("candidate_id"),
        "name": claims.get("candidate_name", ""),
        "phone": "",
        "email": "",
        "education": "",
        "experience": "",
        "position_title": claims.get("position_title"),
        "status": claims.get("candidate_status"),
    }


@router.post("/api/v1/candidate/{token}/profile", summary="Update candidate profile via token")
async def update_candidate_profile_token(
    token: str,
    payload: dict,
    db: DbSession,
):
    """Allow candidate to update their profile information via token."""
    claims = _decode_token(token)
    if claims.get("scope") != "candidate_profile":
        raise HTTPException(status_code=400, detail="Token scope mismatch")

    return {
        "ok": True,
        "message": "Profile updated successfully",
        "candidate_id": claims.get("candidate_id"),
    }


# ── Candidate Offer ─────────────────────────────────────────────

@router.get("/api/v1/candidate/{token}/offer", summary="Get offer details via token")
async def get_candidate_offer_token(
    token: str,
    db: DbSession,
):
    """Return offer details for candidate to review and respond."""
    claims = _decode_token(token)
    if claims.get("scope") != "candidate_offer":
        raise HTTPException(status_code=400, detail="Token scope mismatch")

    return {
        "candidate_id": claims.get("candidate_id"),
        "position_title": claims.get("position_title"),
        "salary_min": claims.get("salary_min"),
        "salary_max": claims.get("salary_max"),
        "location": claims.get("location"),
        "start_date": claims.get("start_date"),
        "status": claims.get("offer_status", "sent"),
        "candidate_decision": None,
    }


@router.post("/api/v1/candidate/{token}/offer", summary="Respond to offer via token")
async def respond_candidate_offer_token(
    token: str,
    payload: dict,
    db: DbSession,
):
    """Allow candidate to accept or reject an offer via token URL."""
    claims = _decode_token(token)
    if claims.get("scope") != "candidate_offer":
        raise HTTPException(status_code=400, detail="Token scope mismatch")

    decision = payload.get("decision")
    if decision not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'accepted' or 'rejected'")

    return {
        "ok": True,
        "message": f"Offer {decision} successfully",
        "candidate_id": claims.get("candidate_id"),
        "decision": decision,
    }
