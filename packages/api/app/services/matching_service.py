"""
Matching Service.

AI-powered candidate-position matching via Hermes Agent integration.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class MatchingService:
    """
    Orchestrates intelligent matching between candidates and positions.

    Uses Hermes Agent for semantic similarity scoring and recommendation
    explanations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def match_candidates_for_position(
        self,
        position_id: UUID,
        tenant_id: str,
        top_k: int = 10,
        min_score: float = 0.6,
    ) -> list[dict]:
        """
        Find the best-matching candidates for a position.

        Algorithm:
        1. Load position requirements (skills, experience, education).
        2. Load candidate profiles / parsed resumes.
        3. Call Hermes Agent for semantic matching.
        4. Return ranked results with scores and explanations.

        Returns:
            List of dicts: {candidate_id, score, explanation, matched_skills}
        """
        # TODO: implement with Hermes Agent integration
        raise NotImplementedError

    async def match_positions_for_candidate(
        self,
        candidate_id: UUID,
        tenant_id: str,
        top_k: int = 10,
        min_score: float = 0.6,
    ) -> list[dict]:
        """
        Find the best-matching positions for a candidate.

        Returns:
            List of dicts: {position_id, score, explanation}
        """
        raise NotImplementedError

    async def get_latest_result(self, position_id: UUID, tenant_id: str) -> dict | None:
        """Retrieve the most recent matching result for a position."""
        return None

    async def save_match_result(self, position_id: UUID, results: list[dict], tenant_id: str) -> None:
        """Persist matching results to DB for later retrieval."""
        raise NotImplementedError
