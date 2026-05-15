"""Matching Router — AI-powered candidate-position matching endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.dependencies import CurrentUserDep, DbSession
from app.models.position import Position
from app.schemas.matching import (
    CandidateMatchResult,
    CandidateMatchResultItem,
    MatchDetailResponse,
    MatchListResponse,
    MatchResultItem,
    PositionMatchResult,
)
from app.services.matching_service import MatchingService

router = APIRouter()


@router.post(
    "/position/{position_id}/candidates",
    response_model=PositionMatchResult,
    summary="Match candidates for a position",
)
async def match_candidates_for_position(
    position_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
    top_k: int = Query(10, ge=1, le=50, description="Number of top matches to return"),
    min_score: float = Query(0.6, ge=0.0, le=1.0, description="Minimum matching score"),
):
    pos_stmt = select(Position).where(
        Position.id == position_id,
        Position.tenant_id == current_user.tenant_id,
    )
    pos_row = await db.execute(pos_stmt)
    position = pos_row.scalar_one_or_none()
    if position is None:
        raise HTTPException(status_code=404, detail="Position not found")

    service = MatchingService(db)
    results = await service.match_candidates_for_position(
        position_id=position_id,
        tenant_id=current_user.tenant_id,
        top_k=top_k,
        min_score=min_score,
    )

    matches = [
        MatchResultItem(
            candidate_id=r["candidate_id"],
            candidate_name=r.get("candidate_name"),
            overall_score=r["overall_score"],
            skill_score=r.get("skill_score"),
            experience_score=r.get("experience_score"),
            education_score=r.get("education_score"),
            matched_skills=r.get("matched_skills", []),
            missing_skills=r.get("missing_skills", []),
            explanation=r.get("explanation"),
        )
        for r in results
    ]

    return PositionMatchResult(
        position_id=position_id,
        position_title=position.title,
        total_candidates=len(matches),
        matches=matches,
    )


@router.post(
    "/candidate/{candidate_id}/positions",
    response_model=CandidateMatchResult,
    summary="Match positions for a candidate",
)
async def match_positions_for_candidate(
    candidate_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
    top_k: int = Query(10, ge=1, le=50),
    min_score: float = Query(0.6, ge=0.0, le=1.0),
):
    service = MatchingService(db)
    results = await service.match_positions_for_candidate(
        candidate_id=candidate_id,
        tenant_id=current_user.tenant_id,
        top_k=top_k,
        min_score=min_score,
    )

    matches = [
        CandidateMatchResultItem(
            position_id=r["position_id"],
            position_title=r.get("position_title"),
            overall_score=r["overall_score"],
            skill_score=r.get("skill_score"),
            matched_skills=r.get("matched_skills", []),
            missing_skills=r.get("missing_skills", []),
            explanation=r.get("explanation"),
        )
        for r in results
    ]

    return CandidateMatchResult(
        candidate_id=candidate_id,
        total_positions=len(matches),
        matches=matches,
    )


@router.get(
    "/position/{position_id}/result",
    response_model=MatchListResponse,
    summary="Get latest match result",
)
async def get_match_result(
    position_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    service = MatchingService(db)
    records = await service.get_latest_result(
        position_id=position_id,
        tenant_id=current_user.tenant_id,
    )

    items = [
        MatchDetailResponse(
            id=r.id,
            position_id=r.position_id,
            candidate_id=r.candidate_id,
            status=r.status,
            overall_score=r.overall_score,
            skill_score=r.skill_score,
            experience_score=r.experience_score,
            education_score=r.education_score,
            score_breakdown=r.score_breakdown,
            match_details=r.match_details,
            matched_at=r.matched_at,
        )
        for r in records
    ]

    return MatchListResponse(items=items, total=len(items), pages=1 if items else 0)
