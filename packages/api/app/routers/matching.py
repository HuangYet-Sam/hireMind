"""
Intelligent Matching Router.

AI-powered candidate-position matching endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUserDep, DbSession
from app.schemas.candidate import CandidateListResponse
from app.schemas.position import PositionListResponse

router = APIRouter()


@router.post(
    "/position/{position_id}/candidates",
    summary="Match candidates for a position",
)
async def match_candidates_for_position(
    position_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
    top_k: int = Query(10, ge=1, le=50, description="Number of top matches to return"),
    min_score: float = Query(0.6, ge=0.0, le=1.0, description="Minimum matching score"),
):
    """
    Use AI (Hermes Agent) to find the best-matching candidates for a given position.

    Returns a ranked list of candidates with match scores and explanations.
    """
    # TODO: delegate to matching_service.match_candidates_for_position(...)
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post(
    "/candidate/{candidate_id}/positions",
    summary="Match positions for a candidate",
)
async def match_positions_for_candidate(
    candidate_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
    top_k: int = Query(10, ge=1, le=50),
    min_score: float = Query(0.6, ge=0.0, le=1.0),
):
    """
    Use AI to find the best-matching positions for a given candidate.

    Returns a ranked list of positions with match scores.
    """
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get(
    "/position/{position_id}/result",
    summary="Get latest match result",
)
async def get_match_result(
    position_id: UUID,
    db: DbSession,
    current_user: CurrentUserDep,
):
    """Retrieve the most recent AI matching result for a position."""
    raise HTTPException(status_code=501, detail="Not implemented yet")
