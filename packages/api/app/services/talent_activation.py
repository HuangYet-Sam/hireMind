"""
TalentActivationService — 沉默候选人激活服务。

扫描沉默候选人库，匹配合适的新岗位，生成个性化激活策略并执行。

核心能力:
  - scan_inactive_candidates: 扫描沉默候选人
  - find_matching_positions: 匹配新岗位
  - generate_activation_strategy: 生成激活策略
  - execute_activation: 执行激活
  - get_activation_stats: 激活统计
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.position import Position
from app.models.resume import Resume

logger = logging.getLogger("hiremind.services.talent_activation")


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── In-memory activation strategy store ──────────────────────────────
_activation_strategies: dict[str, dict[str, Any]] = {}


class TalentActivationService:
    """沉默候选人激活服务 — 发现沉默人才并主动激活。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ══════════════════════════════════════════════════════════════
    # 1. 扫描沉默候选人
    # ══════════════════════════════════════════════════════════════

    async def scan_inactive_candidates(
        self,
        tenant_id: str,
        days_silent: int = 30,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        扫描沉默候选人 — 超过 N 天无互动的活跃候选人。

        Args:
            tenant_id: 租户 ID。
            days_silent: 沉默天数阈值（默认 30）。
            limit: 最大返回数。

        Returns:
            沉默候选人列表，每项包含:
              - candidate: 候选人基本信息
              - days_silent: 沉默天数
              - last_activity: 最后活跃时间
              - potential_matches: 潜在匹配岗位数
        """
        cutoff = _now() - timedelta(days=days_silent)

        # 查询沉默候选人：活跃但长时间未更新，且不在终态
        candidates = (await self.db.execute(
            select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
                Candidate.stage.notin_(["hired", "rejected"]),
                Candidate.updated_at < cutoff,
            ).order_by(Candidate.updated_at.asc()).limit(limit)
        )).scalars().all()

        result: list[dict[str, Any]] = []
        for c in candidates:
            # 计算沉默天数
            updated = c.updated_at
            if updated and updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            days = (_now() - updated).days if updated else days_silent

            # 查找潜在匹配岗位
            match_count = await self._count_matching_positions(c, tenant_id)

            result.append({
                "candidate": {
                    "id": str(c.id),
                    "name": c.name or "未知",
                    "stage": c.stage,
                    "credibility_score": c.credibility_score,
                    "profile": c.profile,
                },
                "days_silent": days,
                "last_activity": updated.isoformat() if updated else None,
                "potential_matches": match_count,
            })

        logger.info(
            "scan_inactive_candidates: tenant=%s silent_days=%d found=%d",
            tenant_id, days_silent, len(result),
        )
        return result

    # ══════════════════════════════════════════════════════════════
    # 2. 匹配新岗位
    # ══════════════════════════════════════════════════════════════

    async def find_matching_positions(
        self,
        candidate_id: str,
        tenant_id: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        为沉默候选人匹配新岗位。

        基于候选人画像（技能、经验、学历）与开放岗位的匹配度评分。

        Args:
            candidate_id: 候选人 UUID。
            tenant_id: 租户 ID。
            top_k: 返回前 K 个匹配。

        Returns:
            匹配岗位列表，每项包含 position + match_score + highlights。
        """
        # 加载候选人
        candidate = await self.db.scalar(
            select(Candidate).where(
                Candidate.id == candidate_id,
                Candidate.tenant_id == tenant_id,
            )
        )
        if candidate is None:
            return []

        # 获取开放岗位
        positions = (await self.db.execute(
            select(Position).where(
                Position.tenant_id == tenant_id,
                Position.status == "open",
            ).order_by(Position.created_at.desc())
        )).scalars().all()

        if not positions:
            return []

        # 计算匹配度
        scored: list[dict[str, Any]] = []
        candidate_profile = candidate.profile or {}
        candidate_skills = set()
        for skill in candidate_profile.get("skills", []):
            if isinstance(skill, dict):
                candidate_skills.add(skill.get("name", "").lower())
            elif isinstance(skill, str):
                candidate_skills.add(skill.lower())

        for pos in positions:
            score, highlights = self._compute_match_score(
                candidate_profile, candidate_skills, pos,
            )
            if score > 0.2:  # 最低匹配度阈值
                scored.append({
                    "position": {
                        "id": str(pos.id),
                        "title": pos.title,
                        "department": pos.department,
                        "location": pos.location,
                        "salary_range": f"{pos.salary_min or 'N/A'}-{pos.salary_max or 'N/A'}",
                        "headcount": pos.headcount,
                        "requirements": pos.requirements,
                    },
                    "match_score": round(score, 3),
                    "highlights": highlights,
                })

        # 按匹配度降序排列
        scored.sort(key=lambda x: x["match_score"], reverse=True)
        return scored[:top_k]

    # ══════════════════════════════════════════════════════════════
    # 3. 生成激活策略
    # ══════════════════════════════════════════════════════════════

    async def generate_activation_strategy(
        self,
        candidate_id: str,
        position_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        生成激活策略 — 分析候选人画像 + 新岗位匹配度，生成个性化激活方案。

        包含: 推荐话术、匹配亮点、联系时机建议。

        Args:
            candidate_id: 候选人 UUID。
            position_id: 岗位 UUID。
            tenant_id: 租户 ID。

        Returns:
            激活策略，包含:
              - strategy_id: 策略 ID
              - candidate_id: 候选人 ID
              - position_id: 岗位 ID
              - match_score: 匹配度
              - highlights: 匹配亮点
              - talking_points: 推荐话术
              - contact_timing: 联系时机建议
              - recommended_channel: 推荐联系渠道
        """
        # 加载候选人
        candidate = await self.db.scalar(
            select(Candidate).where(
                Candidate.id == candidate_id,
                Candidate.tenant_id == tenant_id,
            )
        )
        if candidate is None:
            return {"error": "Candidate not found"}

        # 加载岗位
        position = await self.db.scalar(
            select(Position).where(
                Position.id == position_id,
                Position.tenant_id == tenant_id,
            )
        )
        if position is None:
            return {"error": "Position not found"}

        # 计算匹配度
        profile = candidate.profile or {}
        candidate_skills = set()
        for skill in profile.get("skills", []):
            if isinstance(skill, dict):
                candidate_skills.add(skill.get("name", "").lower())
            elif isinstance(skill, str):
                candidate_skills.add(skill.lower())

        score, highlights = self._compute_match_score(
            profile, candidate_skills, position,
        )

        # 生成话术
        candidate_name = candidate.name or "候选人"
        position_title = position.title or "新岗位"
        talking_points = self._generate_talking_points(
            candidate_name, position_title, highlights, profile,
        )

        # 联系时机建议
        contact_timing = self._suggest_contact_timing(candidate)

        # 推荐渠道
        recommended_channel = self._suggest_channel(profile)

        strategy_id = str(uuid.uuid4())
        strategy = {
            "strategy_id": strategy_id,
            "candidate_id": candidate_id,
            "position_id": position_id,
            "match_score": round(score, 3),
            "highlights": highlights,
            "talking_points": talking_points,
            "contact_timing": contact_timing,
            "recommended_channel": recommended_channel,
            "status": "pending",
            "created_at": _now().isoformat(),
        }

        # 存储
        _activation_strategies[strategy_id] = strategy

        logger.info(
            "generate_activation_strategy: candidate=%s position=%s score=%.3f",
            candidate_id, position_id, score,
        )
        return strategy

    # ══════════════════════════════════════════════════════════════
    # 4. 执行激活
    # ══════════════════════════════════════════════════════════════

    async def execute_activation(
        self,
        candidate_id: str,
        strategy_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        执行激活 — 发送推荐/创建任务。

        Args:
            candidate_id: 候选人 UUID。
            strategy_id: 策略 ID。
            tenant_id: 租户 ID。

        Returns:
            执行结果。
        """
        strategy = _activation_strategies.get(strategy_id)
        if not strategy:
            return {"error": "Strategy not found", "strategy_id": strategy_id}

        if strategy.get("candidate_id") != candidate_id:
            return {"error": "Strategy does not match candidate"}

        # 更新候选人状态（标记为重新激活）
        candidate = await self.db.scalar(
            select(Candidate).where(
                Candidate.id == candidate_id,
                Candidate.tenant_id == tenant_id,
            )
        )
        if candidate is None:
            return {"error": "Candidate not found"}

        # 创建激活记录（存储在候选人 metadata 中）
        if not candidate.metadata_:
            candidate.metadata_ = {}
        candidate.metadata_["last_activation"] = {
            "strategy_id": strategy_id,
            "position_id": strategy.get("position_id"),
            "match_score": strategy.get("match_score"),
            "activated_at": _now().isoformat(),
        }

        # 更新策略状态
        strategy["status"] = "executed"
        strategy["executed_at"] = _now().isoformat()

        await self.db.flush()

        logger.info(
            "execute_activation: candidate=%s strategy=%s position=%s",
            candidate_id, strategy_id, strategy.get("position_id"),
        )

        return {
            "status": "success",
            "candidate_id": candidate_id,
            "strategy_id": strategy_id,
            "position_id": strategy.get("position_id"),
            "match_score": strategy.get("match_score"),
            "message": "激活策略已执行，已创建候选人激活记录",
        }

    # ══════════════════════════════════════════════════════════════
    # 5. 激活统计
    # ══════════════════════════════════════════════════════════════

    async def get_activation_stats(
        self,
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        获取激活统计。

        Args:
            tenant_id: 租户 ID。

        Returns:
            统计数据，包含:
              - total_inactive: 沉默候选人数
              - total_strategies: 已生成策略数
              - executed: 已执行激活数
              - pending: 待执行策略数
              - avg_match_score: 平均匹配度
        """
        # 沉默候选人数
        cutoff_30d = _now() - timedelta(days=30)
        total_inactive = await self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.status == "active",
                Candidate.stage.notin_(["hired", "rejected"]),
                Candidate.updated_at < cutoff_30d,
            )
        ) or 0

        # 策略统计
        tenant_strategies = [
            s for s in _activation_strategies.values()
        ]
        executed = sum(1 for s in tenant_strategies if s.get("status") == "executed")
        pending = sum(1 for s in tenant_strategies if s.get("status") == "pending")
        scores = [s.get("match_score", 0) for s in tenant_strategies if s.get("match_score")]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        return {
            "total_inactive": total_inactive,
            "total_strategies": len(tenant_strategies),
            "executed": executed,
            "pending": pending,
            "avg_match_score": round(avg_score, 3),
        }

    # ── 内部方法 ────────────────────────────────────────────────

    async def _count_matching_positions(
        self, candidate: Candidate, tenant_id: str,
    ) -> int:
        """计算候选人的潜在匹配岗位数。"""
        positions = (await self.db.execute(
            select(Position).where(
                Position.tenant_id == tenant_id,
                Position.status == "open",
            )
        )).scalars().all()

        count = 0
        profile = candidate.profile or {}
        skills = set()
        for skill in profile.get("skills", []):
            if isinstance(skill, dict):
                skills.add(skill.get("name", "").lower())
            elif isinstance(skill, str):
                skills.add(skill.lower())

        for pos in positions:
            score, _ = self._compute_match_score(profile, skills, pos)
            if score > 0.3:
                count += 1

        return count

    def _compute_match_score(
        self,
        profile: dict[str, Any],
        candidate_skills: set[str],
        position: Position,
    ) -> tuple[float, list[str]]:
        """
        计算候选人与岗位的匹配度。

        简化评分逻辑:
          - 技能匹配 (40%)
          - 薪资匹配 (30%)
          - 学历匹配 (20%)
          - 经验匹配 (10%)
        """
        highlights: list[str] = []
        score_parts: list[float] = []

        # 1. 技能匹配
        requirements = position.requirements or {}
        required_skills = set()
        if isinstance(requirements, dict):
            for skill in requirements.get("required_skills", []):
                if isinstance(skill, str):
                    required_skills.add(skill.lower())
                elif isinstance(skill, dict):
                    required_skills.add(skill.get("name", "").lower())

        if required_skills:
            overlap = candidate_skills & required_skills
            skill_score = len(overlap) / len(required_skills) if required_skills else 0
            score_parts.append(0.4 * skill_score)
            if overlap:
                highlights.append(f"技能匹配: {', '.join(list(overlap)[:5])}")
        else:
            score_parts.append(0.2)  # 无明确技能要求时给基础分

        # 2. 薪资匹配
        salary_expectation = (profile.get("basic_info") or {}).get(
            "salary_expectation",
        )
        if salary_expectation and position.salary_max:
            try:
                expected = float(str(salary_expectation).replace("k", "000"))
                if expected <= float(position.salary_max):
                    score_parts.append(0.3)
                    highlights.append(f"薪资期望在范围内")
                elif expected <= float(position.salary_max) * 1.2:
                    score_parts.append(0.15)
                else:
                    score_parts.append(0.05)
            except (ValueError, TypeError):
                score_parts.append(0.15)
        else:
            score_parts.append(0.15)

        # 3. 学历匹配
        required_education = requirements.get("education", "") if isinstance(requirements, dict) else ""
        if required_education:
            edu_list = profile.get("education", [])
            candidate_degrees = set()
            for edu in edu_list:
                if isinstance(edu, dict):
                    deg = edu.get("degree", "")
                    if deg:
                        candidate_degrees.add(deg)
            if candidate_degrees:
                score_parts.append(0.2)
            else:
                score_parts.append(0.1)
        else:
            score_parts.append(0.15)

        # 4. 经验匹配
        required_years = requirements.get("experience_years", 0) if isinstance(requirements, dict) else 0
        work_exp = profile.get("work_experience", [])
        exp_years = len(work_exp) * 2  # 粗略估算
        if required_years and exp_years >= required_years:
            score_parts.append(0.1)
            highlights.append(f"经验年限满足要求")
        elif required_years:
            score_parts.append(0.05)
        else:
            score_parts.append(0.08)

        total_score = min(sum(score_parts), 1.0)
        return total_score, highlights

    def _generate_talking_points(
        self,
        candidate_name: str,
        position_title: str,
        highlights: list[str],
        profile: dict[str, Any],
    ) -> list[str]:
        """生成推荐话术。"""
        points = [
            f"您好 {candidate_name}，我们有一个新的岗位机会想向您推荐：{position_title}。",
        ]

        if highlights:
            points.append(f"您的以下优势与该岗位高度匹配: {'; '.join(highlights[:3])}")

        # 个性化补充
        skills = profile.get("skills", [])
        if skills:
            top_skills = []
            for s in skills[:3]:
                if isinstance(s, dict):
                    top_skills.append(s.get("name", ""))
                elif isinstance(s, str):
                    top_skills.append(s)
            if top_skills:
                points.append(f"您在 {', '.join(top_skills)} 方面的经验正是我们看重的。")

        points.append("如果您对这个机会感兴趣，我们可以安排一次详细沟通。")
        return points

    def _suggest_contact_timing(
        self, candidate: Candidate,
    ) -> dict[str, str]:
        """建议联系时机。"""
        # 基于候选人最后活跃时间推算
        updated = candidate.updated_at
        if updated:
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            weekday = updated.weekday()
            if weekday < 5:
                return {
                    "recommended_time": "工作日上午 10:00-11:00",
                    "reason": "基于候选人历史活跃时间分析，工作日上午是最佳联系时间",
                }
            else:
                return {
                    "recommended_time": "下周一上午 10:00-11:00",
                    "reason": "周末不适合联系，建议周一上午沟通",
                }
        return {
            "recommended_time": "工作日上午 10:00-11:00",
            "reason": "默认推荐工作日上午联系",
        }

    def _suggest_channel(self, profile: dict[str, Any]) -> str:
        """推荐联系渠道。"""
        basic = profile.get("basic_info", {})
        if basic.get("email"):
            return "email"
        if basic.get("phone"):
            return "phone"
        if basic.get("wechat"):
            return "wechat"
        return "email"
