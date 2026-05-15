"""Matching Service — Phase 1 skill/experience scoring algorithm."""

from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.matching import Match, MatchFeedback
from app.models.position import Position
from app.models.candidate import Candidate


class MatchingService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Public API ────────────────────────────────────────────────

    async def match_candidates_for_position(
        self,
        position_id: UUID,
        tenant_id: str,
        top_k: int = 10,
        min_score: float = 0.6,
    ) -> list[dict]:
        position = await self._get_position(position_id, tenant_id)
        if position is None:
            return []

        candidates = await self._get_active_candidates(tenant_id)
        position_skills = position.required_skills or []
        exp_min = position.required_exp_min
        exp_max = position.required_exp_max

        actual_min = min_score * 100
        results: list[dict] = []

        for cand in candidates:
            profile = cand.profile or {}
            cand_skills = profile.get("skills", [])
            if isinstance(cand_skills, dict):
                cand_skills = list(cand_skills.keys())

            skill_score, matched, missing = self._calculate_skill_score(
                position_skills, cand_skills
            )
            exp_years = self._extract_experience_years(profile)
            experience_score = self._calculate_experience_score(exp_years, exp_min, exp_max)
            education_score = self._calculate_education_score(profile)
            overall = skill_score * 0.4 + experience_score * 0.3 + education_score * 0.2 + 10.0
            overall = min(100.0, overall)

            # Try AI-enhanced scoring
            ai_score = 0.0
            ai_reasoning = ""
            ai_result = None
            try:
                from app.services.ai_client import ai_client
                position_info = {
                    "title": position.title,
                    "required_skills": position_skills,
                    "description": getattr(position, 'description', None),
                }
                candidate_info = {
                    "skills": cand_skills,
                    "profile": profile,
                }
                ai_result = await ai_client.score_candidate_match(position_info, candidate_info)
                if ai_result is not None:
                    ai_score = ai_result.get("ai_score", 0)
                    ai_reasoning = ai_result.get("ai_reasoning", "")
                    # Blend: 70% algorithmic + 30% AI
                    overall = overall * 0.7 + ai_score * 0.3
                    overall = min(100.0, overall)
            except Exception:
                pass  # AI unavailable, use algorithmic score

            if overall < actual_min:
                continue

            result = {
                "candidate_id": cand.id,
                "candidate_name": self._extract_candidate_name(cand),
                "overall_score": round(overall, 2),
                "skill_score": round(skill_score, 2),
                "experience_score": round(experience_score, 2),
                "education_score": round(education_score, 2),
                "matched_skills": matched,
                "missing_skills": missing,
                "explanation": self._build_explanation(matched, missing, overall),
                "bonus_score": round(ai_score if ai_result else 10.0, 2),
                "ai_reasoning": ai_reasoning,
            }
            results.append(result)
            await self.save_match_result(
                position_id=position_id,
                candidate_id=cand.id,
                results=result,
                tenant_id=tenant_id,
            )

        results.sort(key=lambda r: r["overall_score"], reverse=True)
        await self.db.flush()
        return results[:top_k]

    async def match_positions_for_candidate(
        self,
        candidate_id: UUID,
        tenant_id: str,
        top_k: int = 10,
        min_score: float = 0.6,
    ) -> list[dict]:
        candidate = await self._get_candidate(candidate_id, tenant_id)
        if candidate is None:
            return []

        profile = candidate.profile or {}
        cand_skills = profile.get("skills", [])
        if isinstance(cand_skills, dict):
            cand_skills = list(cand_skills.keys())

        positions = await self._get_open_positions(tenant_id)
        actual_min = min_score * 100
        results: list[dict] = []

        for pos in positions:
            pos_skills = pos.required_skills or []
            exp_min = pos.required_exp_min
            exp_max = pos.required_exp_max

            skill_score, matched, missing = self._calculate_skill_score(
                pos_skills, cand_skills
            )
            exp_years = self._extract_experience_years(profile)
            experience_score = self._calculate_experience_score(exp_years, exp_min, exp_max)
            education_score = self._calculate_education_score(profile)
            overall = skill_score * 0.4 + experience_score * 0.3 + education_score * 0.2 + 10.0
            overall = min(100.0, overall)

            # Try AI-enhanced scoring
            ai_score = 0.0
            ai_reasoning = ""
            ai_result = None
            try:
                from app.services.ai_client import ai_client
                position_info = {
                    "title": pos.title,
                    "required_skills": pos_skills,
                    "description": getattr(pos, 'description', None),
                }
                candidate_info = {
                    "skills": cand_skills,
                    "profile": profile,
                }
                ai_result = await ai_client.score_candidate_match(position_info, candidate_info)
                if ai_result is not None:
                    ai_score = ai_result.get("ai_score", 0)
                    ai_reasoning = ai_result.get("ai_reasoning", "")
                    # Blend: 70% algorithmic + 30% AI
                    overall = overall * 0.7 + ai_score * 0.3
                    overall = min(100.0, overall)
            except Exception:
                pass  # AI unavailable, use algorithmic score

            if overall < actual_min:
                continue

            result = {
                "position_id": pos.id,
                "position_title": pos.title,
                "overall_score": round(overall, 2),
                "skill_score": round(skill_score, 2),
                "matched_skills": matched,
                "missing_skills": missing,
                "explanation": self._build_explanation(matched, missing, overall),
                "bonus_score": round(ai_score if ai_result else 10.0, 2),
                "ai_reasoning": ai_reasoning,
            }
            results.append(result)
            await self.save_match_result(
                position_id=pos.id,
                candidate_id=candidate_id,
                results=result,
                tenant_id=tenant_id,
            )

        results.sort(key=lambda r: r["overall_score"], reverse=True)
        await self.db.flush()
        return results[:top_k]

    async def get_latest_result(self, position_id: UUID, tenant_id: str) -> list[Match]:
        stmt = (
            select(Match)
            .where(Match.position_id == position_id, Match.tenant_id == tenant_id)
            .order_by(Match.overall_score.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def save_match_result(
        self,
        position_id: UUID,
        candidate_id: UUID,
        results: dict,
        tenant_id: str,
    ) -> None:
        score_breakdown = {
            "skill_score": results.get("skill_score"),
            "experience_score": results.get("experience_score"),
            "education_score": results.get("education_score"),
        }
        match_details = {
            "matched_skills": results.get("matched_skills", []),
            "missing_skills": results.get("missing_skills", []),
            "explanation": results.get("explanation"),
        }

        stmt = pg_insert(Match).values(
            position_id=position_id,
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            status="pending",
            overall_score=results.get("overall_score"),
            skill_score=results.get("skill_score"),
            experience_score=results.get("experience_score"),
            education_score=results.get("education_score"),
            score_breakdown=score_breakdown,
            match_details=match_details,
            initiated_by="system",
        ).on_conflict_do_update(
            index_elements=["position_id", "candidate_id"],
            set_={
                "status": "pending",
                "overall_score": results.get("overall_score"),
                "skill_score": results.get("skill_score"),
                "experience_score": results.get("experience_score"),
                "education_score": results.get("education_score"),
                "score_breakdown": score_breakdown,
                "match_details": match_details,
            },
        )
        await self.db.execute(stmt)

    async def add_feedback(
        self,
        match_id: UUID,
        user_id: str,
        feedback_type: str,
        reason: str | None,
        tenant_id: str,
    ) -> MatchFeedback:
        feedback = MatchFeedback(
            tenant_id=tenant_id,
            match_id=match_id,
            user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
            feedback_type=feedback_type,
            reason=reason,
        )
        self.db.add(feedback)
        await self.db.flush()
        return feedback

    # ── Scoring helpers ──────────────────────────────────────────

    def _calculate_skill_score(
        self, position_skills: list, candidate_skills: list
    ) -> tuple[float, list[str], list[str]]:
        if not position_skills:
            return 50.0, [], []

        required = [s for s in position_skills if s.get("level") == "required"]
        bonus = [s for s in position_skills if s.get("level") == "bonus"]
        cand_lower = [c.lower() for c in candidate_skills]

        matched_required = [
            s["skill"] for s in required if s["skill"].lower() in cand_lower
        ]
        matched_bonus = [
            s["skill"] for s in bonus if s["skill"].lower() in cand_lower
        ]
        matched = matched_required + matched_bonus

        all_skill_names = [s["skill"] for s in position_skills]
        missing = [name for name in all_skill_names if name not in matched]

        score = 0.0
        if required:
            score += (len(matched_required) / len(required)) * 70
        if bonus:
            score += (len(matched_bonus) / len(bonus)) * 30
        elif not required:
            score = 50.0

        return min(100.0, score), matched, missing

    def _calculate_experience_score(
        self,
        candidate_years: float | None,
        exp_min: int | None,
        exp_max: int | None,
    ) -> float:
        if candidate_years is None:
            return 40.0
        if exp_min is None and exp_max is None:
            return 50.0

        score = 50.0
        if exp_min is not None:
            if candidate_years >= exp_min:
                score += 25.0
            else:
                ratio = candidate_years / exp_min if exp_min > 0 else 0
                score += ratio * 25.0
        if exp_max is not None:
            if candidate_years <= exp_max:
                score += 25.0
            else:
                overshoot = candidate_years - exp_max
                score += max(0, 25.0 - overshoot * 5)
        return min(100.0, max(0.0, score))

    def _calculate_education_score(self, profile: dict) -> float:
        education = profile.get("education", [])
        if not education:
            return 40.0
        return 60.0

    def _extract_experience_years(self, profile: dict) -> float | None:
        work_exp = profile.get("work_experience", [])
        if isinstance(work_exp, list) and work_exp:
            total = 0.0
            for exp in work_exp:
                if isinstance(exp, dict):
                    duration = exp.get("duration_years")
                    if duration is not None:
                        try:
                            total += float(duration)
                        except (ValueError, TypeError):
                            pass
            return total if total > 0 else None
        return None

    def _extract_candidate_name(self, candidate: Candidate) -> str | None:
        profile = candidate.profile or {}
        basic = profile.get("basic_info", {})
        if isinstance(basic, dict):
            return basic.get("name")
        return None

    def _build_explanation(
        self, matched: list[str], missing: list[str], overall: float
    ) -> str:
        parts: list[str] = []
        if matched:
            parts.append(f"Matched skills: {', '.join(matched)}")
        if missing:
            parts.append(f"Missing skills: {', '.join(missing)}")
        parts.append(f"Overall score: {overall:.1f}/100")
        return "; ".join(parts)

    # ── Data access ──────────────────────────────────────────────

    async def _get_position(self, position_id: UUID, tenant_id: str) -> Position | None:
        stmt = select(Position).where(
            Position.id == position_id,
            Position.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_candidate(self, candidate_id: UUID, tenant_id: str) -> Candidate | None:
        stmt = select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_active_candidates(self, tenant_id: str) -> list[Candidate]:
        stmt = select(Candidate).where(
            Candidate.tenant_id == tenant_id,
            Candidate.status == "active",
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_open_positions(self, tenant_id: str) -> list[Position]:
        stmt = select(Position).where(
            Position.tenant_id == tenant_id,
            Position.status == "open",
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
