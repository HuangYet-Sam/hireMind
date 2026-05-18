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

    # ------------------------------------------------------------------
    # M10: 记忆注入 & 学术式画像
    # ------------------------------------------------------------------

    async def inject_memories(
        self,
        candidate_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        记忆注入画像 — 查找与该候选人相关的记忆，将偏好/历史决策注入画像上下文。

        从记忆系统中检索与候选人相关的所有记忆（偏好、决策、洞察），
        整合到画像上下文中，供后续 AI 分析使用。

        Args:
            candidate_id: 候选人 UUID。
            tenant_id: 租户 ID。

        Returns:
            包含注入记忆的画像上下文字典。
        """
        from app.models.memory import Memory
        from sqlalchemy import and_

        # 加载候选人
        candidate = await self._load_candidate(UUID(candidate_id))
        if candidate is None:
            raise ValueError(f"Candidate not found: {candidate_id}")

        # 查找与该候选人直接相关的记忆（source_id = candidate_id）
        direct_memories = (await self.db.execute(
            select(Memory).where(
                Memory.tenant_id == tenant_id,
                Memory.is_active == True,  # noqa: E712
                Memory.source_id == candidate_id,
            ).order_by(Memory.importance.desc(), Memory.created_at.desc()).limit(20)
        )).scalars().all()

        # 查找招聘偏好类记忆（全局偏好）
        preference_memories = (await self.db.execute(
            select(Memory).where(
                Memory.tenant_id == tenant_id,
                Memory.is_active == True,  # noqa: E712
                Memory.memory_type.in_(["preference", "pattern"]),
                Memory.category.in_(["candidate", "recruitment"]),
            ).order_by(Memory.importance.desc()).limit(10)
        )).scalars().all()

        # 构建注入上下文
        memory_context: dict[str, Any] = {
            "candidate_id": candidate_id,
            "candidate_name": candidate.name or "未知",
            "direct_memories": [
                {
                    "id": str(m.id),
                    "type": m.memory_type,
                    "category": m.category,
                    "content": m.content,
                    "confidence": m.confidence,
                    "importance": m.importance,
                    "source": m.source,
                    "tags": m.tags,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in direct_memories
            ],
            "global_preferences": [
                {
                    "id": str(m.id),
                    "type": m.memory_type,
                    "content": m.content,
                    "confidence": m.confidence,
                    "tags": m.tags,
                }
                for m in preference_memories
            ],
            "memory_count": len(direct_memories) + len(preference_memories),
            "injected_at": datetime.utcnow().isoformat(),
        }

        # 分析偏好决策趋势
        decision_memories = [m for m in direct_memories if m.memory_type == "decision"]
        if decision_memories:
            accept_count = sum(
                1 for m in decision_memories
                if "accept" in (m.tags or []) or "通过" in m.content
            )
            reject_count = sum(
                1 for m in decision_memories
                if "reject" in (m.tags or []) or "拒绝" in m.content
            )
            memory_context["decision_trend"] = {
                "total_decisions": len(decision_memories),
                "accepted": accept_count,
                "rejected": reject_count,
                "trend": "positive" if accept_count > reject_count else "negative",
            }

        logger.info(
            "inject_memories: candidate=%s direct=%d preferences=%d",
            candidate_id, len(direct_memories), len(preference_memories),
        )
        return memory_context

    async def generate_academic_profile(
        self,
        candidate_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        论文式画像生成 — 多源引用格式、AI推理标签、置信度分层。

        将候选人画像以学术引用格式输出，每个数据点标注来源，
        附带 AI 推理引擎的推理标签，并按置信度高/中/低分层。

        Args:
            candidate_id: 候选人 UUID。
            tenant_id: 租户 ID。

        Returns:
            学术式画像，结构如下:
              - abstract: 摘要
              - sections: 各维度分析（含引用标注）
              - inference_labels: AI推理标签
              - confidence_layers: {high/medium/low} 分层
              - references: 引用来源列表
        """
        # 构建基础画像
        profile = await self.build_profile(candidate_id)

        # 注入记忆
        memory_context = await self.inject_memories(candidate_id, tenant_id)

        # 生成 AI 推理标签
        inference_labels = await self._generate_inference_labels(
            profile, memory_context,
        )

        # 按置信度分层
        confidence_layers = self._stratify_confidence(profile)

        # 构建引用格式 sections
        sections: list[dict[str, Any]] = []
        sections.append(self._build_basic_info_section(profile))
        sections.append(self._build_work_experience_section(profile))
        sections.append(self._build_skills_section(profile))
        sections.append(self._build_education_section(profile))

        # 记忆引用 section
        if memory_context.get("direct_memories"):
            sections.append({
                "title": "历史决策记录",
                "citations": [
                    {
                        "content": m["content"],
                        "source": m["source"],
                        "confidence": m["confidence"],
                        "reference": f"[M{i+1}]",
                    }
                    for i, m in enumerate(memory_context["direct_memories"][:10])
                ],
            })

        # 全局偏好引用
        if memory_context.get("global_preferences"):
            sections.append({
                "title": "组织招聘偏好",
                "citations": [
                    {
                        "content": p["content"],
                        "type": p["type"],
                        "confidence": p["confidence"],
                        "reference": f"[P{i+1}]",
                    }
                    for i, p in enumerate(memory_context["global_preferences"][:5])
                ],
            })

        # 引用来源列表
        references: list[dict[str, str]] = []
        for i, resume_ref in enumerate(profile.source_refs):
            references.append({
                "id": f"[R{i+1}]",
                "type": "resume",
                "source_id": resume_ref,
                "description": f"简历来源 {resume_ref[:8]}...",
            })
        for i, mem in enumerate(memory_context.get("direct_memories", [])[:10]):
            references.append({
                "id": f"[M{i+1}]",
                "type": "memory",
                "source_id": mem.get("id", ""),
                "description": f"记忆 {mem.get('type', '')}: {mem.get('content', '')[:50]}...",
            })
        for i, pref in enumerate(memory_context.get("global_preferences", [])[:5]):
            references.append({
                "id": f"[P{i+1}]",
                "type": "preference",
                "source_id": pref.get("id", ""),
                "description": f"偏好: {pref.get('content', '')[:50]}...",
            })

        # 构建摘要
        skill_count = len(profile.merged.skill_cloud)
        work_count = len(profile.merged.work_timeline)
        edu_count = len(profile.merged.education)
        memory_count = memory_context.get("memory_count", 0)

        abstract = (
            f"候选人画像报告 — {profile.merged.basic_info.get('name', '未知')} "
            f"[可信度: {profile.credibility_grade} ({profile.overall_credibility:.1f})]\n"
            f"数据来源: {profile.resume_count} 份简历, {memory_count} 条相关记忆\n"
            f"画像维度: {skill_count} 项技能, {work_count} 段工作经历, {edu_count} 条教育记录"
        )

        academic_profile = {
            "candidate_id": candidate_id,
            "abstract": abstract,
            "sections": sections,
            "inference_labels": inference_labels,
            "confidence_layers": confidence_layers,
            "references": references,
            "meta": {
                "resume_count": profile.resume_count,
                "memory_count": memory_count,
                "credibility_grade": profile.credibility_grade,
                "credibility_score": profile.overall_credibility,
                "generated_at": datetime.utcnow().isoformat(),
            },
        }

        logger.info(
            "generate_academic_profile: candidate=%s grade=%s sections=%d refs=%d",
            candidate_id, profile.credibility_grade, len(sections), len(references),
        )
        return academic_profile

    # ── 学术画像辅助方法 ────────────────────────────────────────

    async def _generate_inference_labels(
        self,
        profile: CandidateProfile,
        memory_context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        生成 AI 推理标签 — 基于画像数据和记忆上下文推断隐含信息。

        标签类型: skill_gap / overqualified / career_shift / salary_mismatch 等。
        """
        labels: list[dict[str, Any]] = []

        # 技能缺口检测
        skills = [t.name.lower() for t in profile.merged.skill_cloud]
        if len(skills) < 3:
            labels.append({
                "label": "skill_sparse",
                "description": "技能标签稀少，可能简历信息不完整",
                "confidence": 0.6,
                "layer": "medium",
            })

        # 职业转型检测
        work = profile.merged.work_timeline
        if len(work) >= 2:
            companies = set(w.company for w in work if w.company)
            titles = set(w.title for w in work if w.title)
            if len(titles) >= 3:
                labels.append({
                    "label": "career_diverse",
                    "description": "职业经历涉及多个方向，可能是复合型人才",
                    "confidence": 0.5,
                    "layer": "medium",
                })

        # 决策趋势标签
        decision_trend = memory_context.get("decision_trend", {})
        if decision_trend:
            trend = decision_trend.get("trend", "")
            if trend == "positive":
                labels.append({
                    "label": "historically_favored",
                    "description": "历史决策记录偏正面，表明HR曾对该候选人有好感",
                    "confidence": 0.7,
                    "layer": "high",
                })
            elif trend == "negative":
                labels.append({
                    "label": "historically_declined",
                    "description": "历史决策记录偏负面，需关注拒因是否仍然成立",
                    "confidence": 0.7,
                    "layer": "high",
                })

        # 可信度标签
        if profile.overall_credibility >= 80:
            labels.append({
                "label": "high_credibility",
                "description": "画像可信度高（A级），简历信息充分且一致",
                "confidence": 0.9,
                "layer": "high",
            })
        elif profile.overall_credibility < 40:
            labels.append({
                "label": "low_credibility",
                "description": "画像可信度较低（D级），建议补充材料验证",
                "confidence": 0.9,
                "layer": "high",
            })

        return labels

    def _stratify_confidence(
        self, profile: CandidateProfile,
    ) -> dict[str, list[dict[str, Any]]]:
        """按置信度高/中/低分层。"""
        layers: dict[str, list[dict[str, Any]]] = {
            "high": [],
            "medium": [],
            "low": [],
        }

        # 技能分层
        for tag in profile.merged.skill_cloud:
            entry = {
                "type": "skill",
                "name": tag.name,
                "source_count": tag.source_count,
                "credibility_weight": tag.credibility_weight,
            }
            if tag.source_count >= 2 and tag.credibility_weight >= 0.7:
                layers["high"].append(entry)
            elif tag.source_count >= 1 and tag.credibility_weight >= 0.5:
                layers["medium"].append(entry)
            else:
                layers["low"].append(entry)

        # 工作经历分层
        for exp in profile.merged.work_timeline:
            entry = {
                "type": "work_experience",
                "company": exp.company,
                "title": exp.title,
            }
            if exp.start_date and exp.description:
                layers["high"].append(entry)
            elif exp.start_date:
                layers["medium"].append(entry)
            else:
                layers["low"].append(entry)

        # 教育分层
        for edu in profile.merged.education:
            entry = {
                "type": "education",
                "school": edu.school,
                "degree": edu.degree,
                "major": edu.major,
            }
            if edu.degree and edu.major:
                layers["high"].append(entry)
            elif edu.school:
                layers["medium"].append(entry)
            else:
                layers["low"].append(entry)

        return layers

    def _build_basic_info_section(
        self, profile: CandidateProfile,
    ) -> dict[str, Any]:
        """构建基本信息 section（含引用标注）。"""
        basic = profile.merged.basic_info
        return {
            "title": "基本信息",
            "fields": [
                {"key": k, "value": v, "reference": f"[R1]"}
                for k, v in basic.items()
                if v is not None
            ],
        }

    def _build_work_experience_section(
        self, profile: CandidateProfile,
    ) -> dict[str, Any]:
        """构建工作经历 section。"""
        entries = []
        for exp in profile.merged.work_timeline:
            ref = f"[R_source:{exp.source_resume_id[:8]}...]" if exp.source_resume_id else "[R?]"
            entries.append({
                "company": exp.company,
                "title": exp.title,
                "period": f"{exp.start_date or '?'} - {exp.end_date or '至今'}",
                "description": exp.description,
                "reference": ref,
            })
        return {"title": "工作经历", "entries": entries}

    def _build_skills_section(
        self, profile: CandidateProfile,
    ) -> dict[str, Any]:
        """构建技能 section。"""
        skills = []
        for tag in profile.merged.skill_cloud:
            skills.append({
                "name": tag.name,
                "proficiency": tag.proficiency,
                "years_of_experience": tag.years_of_experience,
                "source_count": tag.source_count,
                "credibility_weight": round(tag.credibility_weight, 2),
            })
        return {"title": "技能标签云", "skills": skills}

    def _build_education_section(
        self, profile: CandidateProfile,
    ) -> dict[str, Any]:
        """构建教育背景 section。"""
        entries = []
        for edu in profile.merged.education:
            ref = f"[R_source:{edu.source_resume_id[:8]}...]" if edu.source_resume_id else "[R?]"
            entries.append({
                "school": edu.school,
                "degree": edu.degree,
                "major": edu.major,
                "reference": ref,
            })
        return {"title": "教育背景", "entries": entries}
