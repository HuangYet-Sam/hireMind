"""
候选人画像构建引擎 (M3)。

将同一候选人的多份简历聚合为统一的标准化画像，按「最新 + 最高可信度」
优先级进行字段合并，集成 resume_credibility.py 的评分结果。

核心能力:
  - 多源聚合：关联同一候选人的多份简历，按时间倒序 + 可信度加权
  - 字段冲突处理：值不同时取最新 / 取最完整 / 取可信度最高
  - 标准化画像输出：基本信息、工作经历时间轴、教育背景、技能标签云
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.resume import Resume
from app.services.resume_credibility import resume_credibility_service

logger = logging.getLogger("hiremind.candidate_profile_builder")


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------

@dataclass
class SkillTag:
    """技能标签，含来源和置信度。"""
    name: str
    proficiency: str | None = None
    years_of_experience: float | None = None
    source_count: int = 1               # 在多少份简历中出现
    credibility_weight: float = 1.0     # 可信度加权


@dataclass
class TimelineEntry:
    """工作/教育时间线条目。"""
    company: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    source_resume_id: str | None = None


@dataclass
class EducationEntry:
    """教育背景条目。"""
    school: str
    degree: str | None = None
    major: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    source_resume_id: str | None = None


@dataclass
class MergedProfile:
    """
    合并后的候选人画像。

    由 merge_resume_data() 输出，包含去重后的标准化数据。
    """
    basic_info: dict[str, Any] = field(default_factory=dict)
    work_timeline: list[TimelineEntry] = field(default_factory=list)
    education: list[EducationEntry] = field(default_factory=list)
    skill_cloud: list[SkillTag] = field(default_factory=list)
    certifications: list[dict[str, Any]] = field(default_factory=list)
    projects: list[dict[str, Any]] = field(default_factory=list)
    languages: list[dict[str, Any]] = field(default_factory=list)
    credibility_scores: dict[str, float] = field(default_factory=dict)
    merge_meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateProfile:
    """
    完整的候选人画像（面向前端 / Agent 输出）。

    由 build_profile() 输出。
    """
    candidate_id: str
    merged: MergedProfile
    overall_credibility: float = 0.0
    credibility_grade: str = "D"
    resume_count: int = 0
    last_updated: str | None = None
    source_refs: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 候选人画像构建引擎
# ---------------------------------------------------------------------------

class CandidateProfileBuilder:
    """
    候选人画像构建引擎。

    多源聚合策略:
      1. 查询候选人关联的全部简历（parse_status=completed）
      2. 按「最新 + 最高可信度」排序
      3. 调用 merge_resume_data() 合并字段冲突
      4. 集成 credibility 评分，输出 CandidateProfile
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    async def build_profile(self, candidate_id: str) -> CandidateProfile:
        """
        为指定候选人构建完整的标准化画像。

        Args:
            candidate_id: 候选人 UUID。

        Returns:
            CandidateProfile 包含合并后的画像、可信度评分等。

        Raises:
            ValueError: 候选人不存在。
        """
        # 1. 加载候选人
        candidate = await self._load_candidate(UUID(candidate_id))
        if candidate is None:
            raise ValueError(f"Candidate not found: {candidate_id}")

        # 2. 加载关联的全部已完成简历
        resumes = await self._load_resumes(UUID(candidate_id))

        if not resumes:
            logger.info("build_profile: 候选人 %s 无已完成简历，返回空画像", candidate_id)
            return self._empty_profile(candidate)

        # 3. 排序：最新 + 最高可信度优先
        sorted_resumes = self._sort_resumes(resumes)

        # 4. 合并简历数据
        merged = await self.merge_resume_data(sorted_resumes)

        # 5. 计算综合可信度
        overall_credibility = self._compute_overall_credibility(merged, candidate)

        # 6. 写回候选人 profile（持久化）
        await self._persist_profile(candidate, merged, overall_credibility)

        # 7. 组装输出
        profile = CandidateProfile(
            candidate_id=candidate_id,
            merged=merged,
            overall_credibility=overall_credibility,
            credibility_grade=self._credibility_grade(overall_credibility),
            resume_count=len(resumes),
            last_updated=datetime.utcnow().isoformat(),
            source_refs=candidate.source_refs or [],
        )

        logger.info(
            "build_profile: candidate=%s resumes=%d credibility=%.1f grade=%s",
            candidate_id, len(resumes), overall_credibility, profile.credibility_grade,
        )
        return profile

    async def merge_resume_data(self, resumes: list[Resume]) -> MergedProfile:
        """
        合并多份简历数据，处理字段冲突。

        策略:
          - 基本信息字段：取最新非空值；冲突时取可信度最高的简历
          - 工作经历：去重合并，按时间倒序排列
          - 教育背景：去重合并
          - 技能：多源聚合为标签云，累计 source_count

        Args:
            resumes: 已按优先级排序的 Resume 列表（优先级高 → 低）。

        Returns:
            MergedProfile 合并后的标准化画像。
        """
        if not resumes:
            return MergedProfile()

        merged = MergedProfile(
            merge_meta={
                "resume_count": len(resumes),
                "resume_ids": [str(r.id) for r in resumes],
            }
        )

        # 收集每份简历的可信度评分
        for idx, resume in enumerate(resumes):
            parsed = resume.parsed_data or {}
            score = await self._score_single_resume(parsed)
            merged.credibility_scores[str(resume.id)] = score

        # 基本信息合并（第一份优先级最高）
        merged.basic_info = self._merge_basic_info(resumes)

        # 工作经历时间轴
        merged.work_timeline = self._merge_work_timeline(resumes)

        # 教育背景
        merged.education = self._merge_education(resumes)

        # 技能标签云
        merged.skill_cloud = self._merge_skills(resumes)

        # 证书（去重）
        merged.certifications = self._merge_list_field(resumes, "certifications", "name")

        # 项目经历（去重）
        merged.projects = self._merge_list_field(resumes, "projects", "name")

        # 语言（去重）
        merged.languages = self._merge_list_field(resumes, "languages", "language")

        return merged

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    async def _load_candidate(self, candidate_id: UUID) -> Candidate | None:
        """加载候选人记录。"""
        stmt = select(Candidate).where(Candidate.id == candidate_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _load_resumes(self, candidate_id: UUID) -> list[Resume]:
        """加载候选人关联的全部已完成简历。"""
        stmt = (
            select(Resume)
            .where(
                Resume.candidate_id == candidate_id,
                Resume.parse_status == "completed",
                Resume.parsed_data.isnot(None),
            )
            .order_by(Resume.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def _sort_resumes(self, resumes: list[Resume]) -> list[Resume]:
        """
        排序简历列表：最新 + 最高可信度优先。

        排序权重: 0.6 * 时间新近度 + 0.4 * 可信度
        """
        def _priority_key(r: Resume) -> float:
            # 时间新近度：用创建时间的秒级时间戳归一化
            ts = r.created_at.timestamp() if r.created_at else 0.0
            # 可信度
            cred = (r.credibility or {}).get("score", 50.0)
            return 0.6 * ts + 0.4 * cred

        return sorted(resumes, key=_priority_key, reverse=True)

    async def _score_single_resume(self, parsed_data: dict[str, Any]) -> float:
        """对单份简历进行可信度评分。"""
        if not parsed_data:
            return 0.0
        try:
            result = await resume_credibility_service.score_credibility(parsed_data)
            return result.get("score", 0.0)
        except Exception as exc:
            logger.warning("可信度评分失败: %s", exc)
            return 0.0

    # ------------------------------------------------------------------
    # 字段合并策略
    # ------------------------------------------------------------------

    def _merge_basic_info(self, resumes: list[Resume]) -> dict[str, Any]:
        """
        合并基本信息。

        策略：按优先级（已排序），取第一个非空值。
        对于冲突字段，记录所有值供冲突检测器使用。
        """
        merged: dict[str, Any] = {}
        # 按优先级从低到高覆盖，确保最高优先级最终生效
        for resume in reversed(resumes):
            parsed = resume.parsed_data or {}
            basic = parsed.get("basic_info") or {}
            for key, value in basic.items():
                if value is not None and str(value).strip():
                    merged[key] = value
        return merged

    def _merge_work_timeline(self, resumes: list[Resume]) -> list[TimelineEntry]:
        """
        合并工作经历为统一时间轴。

        去重策略：company + title + start_date 三元组相同视为同一经历。
        优先保留可信度最高简历的描述。
        """
        seen: dict[str, TimelineEntry] = {}
        for resume in resumes:
            parsed = resume.parsed_data or {}
            work_list: list[dict[str, Any]] = parsed.get("work_experience") or []
            for exp in work_list:
                company = str(exp.get("company", "")).strip()
                title = str(exp.get("title") or exp.get("position", "")).strip()
                start = str(exp.get("start_date", "")).strip()
                # 去重键
                dedup_key = f"{company}|{title}|{start}"
                if dedup_key in seen:
                    # 如果已有记录但当前缺少描述，补充
                    existing = seen[dedup_key]
                    if not existing.description and exp.get("description"):
                        existing.description = str(exp.get("description", "")).strip()
                    continue

                entry = TimelineEntry(
                    company=company,
                    title=title,
                    start_date=start or None,
                    end_date=str(exp.get("end_date", "")).strip() or None,
                    description=str(exp.get("description", "")).strip() or None,
                    source_resume_id=str(resume.id),
                )
                seen[dedup_key] = entry

        # 按开始时间倒序排列
        entries = list(seen.values())
        entries.sort(key=lambda e: e.start_date or "", reverse=True)
        return entries

    def _merge_education(self, resumes: list[Resume]) -> list[EducationEntry]:
        """
        合并教育背景。

        去重策略：school + degree + major 三元组相同视为重复。
        """
        seen: dict[str, EducationEntry] = {}
        for resume in resumes:
            parsed = resume.parsed_data or {}
            edu_list: list[dict[str, Any]] = parsed.get("education") or []
            for edu in edu_list:
                school = str(edu.get("school", "")).strip()
                degree = str(edu.get("degree", "")).strip()
                major = str(edu.get("major", "")).strip()
                dedup_key = f"{school}|{degree}|{major}"
                if dedup_key in seen:
                    continue
                seen[dedup_key] = EducationEntry(
                    school=school,
                    degree=degree or None,
                    major=major or None,
                    start_date=str(edu.get("start_date", "")).strip() or None,
                    end_date=str(edu.get("end_date", "")).strip() or None,
                    source_resume_id=str(resume.id),
                )

        return list(seen.values())

    def _merge_skills(self, resumes: list[Resume]) -> list[SkillTag]:
        """
        合并技能为标签云。

        同名技能合并 source_count 和最大可信度权重。
        """
        skill_map: dict[str, SkillTag] = {}
        for resume in resumes:
            parsed = resume.parsed_data or {}
            skills: list[dict[str, Any]] = parsed.get("skills") or []
            resume_cred = (resume.credibility or {}).get("score", 50.0) / 100.0

            for skill in skills:
                if isinstance(skill, str):
                    name = skill.strip()
                    extra: dict[str, Any] = {}
                elif isinstance(skill, dict):
                    name = str(skill.get("name", "")).strip()
                    extra = skill
                else:
                    continue

                if not name:
                    continue

                if name in skill_map:
                    tag = skill_map[name]
                    tag.source_count += 1
                    tag.credibility_weight = max(tag.credibility_weight, resume_cred)
                    # 保留更完整的 proficiency / years 信息
                    if not tag.proficiency and extra.get("proficiency"):
                        tag.proficiency = str(extra["proficiency"])
                    if tag.years_of_experience is None and extra.get("years_of_experience"):
                        try:
                            tag.years_of_experience = float(str(extra["years_of_experience"]))
                        except (ValueError, TypeError):
                            pass
                else:
                    tag = SkillTag(
                        name=name,
                        proficiency=extra.get("proficiency"),
                        years_of_experience=None,
                        source_count=1,
                        credibility_weight=resume_cred,
                    )
                    if extra.get("years_of_experience"):
                        try:
                            tag.years_of_experience = float(str(extra["years_of_experience"]))
                        except (ValueError, TypeError):
                            pass
                    skill_map[name] = tag

        # 按 source_count 降序 → credibility_weight 降序
        tags = list(skill_map.values())
        tags.sort(key=lambda t: (t.source_count, t.credibility_weight), reverse=True)
        return tags

    def _merge_list_field(
        self,
        resumes: list[Resume],
        field_name: str,
        dedup_key: str,
    ) -> list[dict[str, Any]]:
        """
        通用列表字段合并（证书/项目/语言）。

        根据 dedup_key 字段去重，保留优先级最高的简历中的记录。
        """
        seen_keys: set[str] = set()
        result: list[dict[str, Any]] = []

        for resume in resumes:
            parsed = resume.parsed_data or {}
            items: list[dict[str, Any]] = parsed.get(field_name) or []
            for item in items:
                if not isinstance(item, dict):
                    continue
                key_val = str(item.get(dedup_key, "")).strip().lower()
                if not key_val or key_val in seen_keys:
                    continue
                seen_keys.add(key_val)
                item["_source_resume_id"] = str(resume.id)
                result.append(item)

        return result

    # ------------------------------------------------------------------
    # 可信度计算
    # ------------------------------------------------------------------

    def _compute_overall_credibility(
        self,
        merged: MergedProfile,
        candidate: Candidate,
    ) -> float:
        """
        计算综合可信度。

        加权平均所有简历的可信度，权重按简历数量占比。
        若候选人已有 credibility_score，则与新计算的值取平均。
        """
        scores = list(merged.credibility_scores.values())
        if not scores:
            return candidate.credibility_score or 0.0

        # 加权平均：每份简历权重相等
        avg_score = sum(scores) / len(scores)

        # 如果候选人已有评分，取加权平均（新值权重更高）
        existing = candidate.credibility_score or 0.0
        if existing > 0:
            overall = 0.6 * avg_score + 0.4 * existing
        else:
            overall = avg_score

        return round(overall, 1)

    @staticmethod
    def _credibility_grade(score: float) -> str:
        """将可信度分数映射为等级 (A/B/C/D)。"""
        if score >= 80:
            return "A"
        if score >= 60:
            return "B"
        if score >= 40:
            return "C"
        return "D"

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------

    async def _persist_profile(
        self,
        candidate: Candidate,
        merged: MergedProfile,
        overall_credibility: float,
    ) -> None:
        """
        将合并后的画像写回候选人记录。

        更新 profile JSONB、credibility_score、credibility_grade。
        """
        profile_data = {
            "basic_info": merged.basic_info,
            "work_experience": [
                {
                    "company": e.company,
                    "title": e.title,
                    "start_date": e.start_date,
                    "end_date": e.end_date,
                    "description": e.description,
                }
                for e in merged.work_timeline
            ],
            "education": [
                {
                    "school": e.school,
                    "degree": e.degree,
                    "major": e.major,
                    "start_date": e.start_date,
                    "end_date": e.end_date,
                }
                for e in merged.education
            ],
            "skills": [
                {
                    "name": t.name,
                    "proficiency": t.proficiency,
                    "years_of_experience": t.years_of_experience,
                    "source_count": t.source_count,
                }
                for t in merged.skill_cloud
            ],
            "certifications": merged.certifications,
            "projects": merged.projects,
            "languages": merged.languages,
        }

        candidate.profile = profile_data
        candidate.credibility_score = overall_credibility
        candidate.credibility_grade = self._credibility_grade(overall_credibility)
        candidate.version += 1
        candidate.source_refs = merged.merge_meta.get("resume_ids", [])

        await self.db.flush()
        logger.info(
            "persist_profile: candidate=%s credibility=%.1f grade=%s",
            candidate.id, overall_credibility, candidate.credibility_grade,
        )

    def _empty_profile(self, candidate: Candidate) -> CandidateProfile:
        """返回空画像（候选人无已完成简历时的降级输出）。"""
        return CandidateProfile(
            candidate_id=str(candidate.id),
            merged=MergedProfile(basic_info=(candidate.profile or {}).get("basic_info", {})),
            overall_credibility=candidate.credibility_score or 0.0,
            credibility_grade=candidate.credibility_grade or "D",
            resume_count=0,
            last_updated=None,
            source_refs=[],
        )
