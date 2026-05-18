"""
数据冲突检测引擎 (M3)。

比较同一候选人不同简历中的同名字段值，检测并处理数据冲突。

冲突类型:
  - 值冲突 (value_conflict): 同一字段在不同简历中的值不同
  - 格式冲突 (format_conflict): 同一信息格式不一致（如日期格式）
  - 时间线冲突 (timeline_conflict): 工作经历时间线存在矛盾

合并策略:
  - take_newest:     取最新简历的值
  - take_most_complete: 取最完整（非空字段最多）的值
  - take_highest_credibility: 取可信度最高简历的值
  - manual:          无法自动合并，返回 HR 裁决
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.resume import Resume

logger = logging.getLogger("hiremind.conflict_detector")


# ---------------------------------------------------------------------------
# 冲突类型与合并策略枚举
# ---------------------------------------------------------------------------

class ConflictType(str, Enum):
    """冲突类型。"""
    VALUE = "value_conflict"          # 值不同
    FORMAT = "format_conflict"        # 格式不同
    TIMELINE = "timeline_conflict"    # 时间线矛盾


class MergeStrategy(str, Enum):
    """自动合并策略。"""
    NEWEST = "take_newest"                        # 取最新
    MOST_COMPLETE = "take_most_complete"          # 取最完整
    HIGHEST_CREDIBILITY = "take_highest_credibility"  # 取可信度最高
    MANUAL = "manual"                             # 需 HR 裁决


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------

@dataclass
class ConflictValue:
    """冲突中的一方值。"""
    resume_id: str
    value: Any
    credibility_score: float = 0.0
    created_at: str | None = None


@dataclass
class Conflict:
    """检测到的数据冲突。"""
    field_path: str                          # 冲突字段路径 (如 "basic_info.name")
    conflict_type: ConflictType              # 冲突类型
    values: list[ConflictValue]              # 所有冲突值
    auto_merge_strategy: MergeStrategy       # 推荐合并策略
    auto_merged_value: Any | None = None     # 自动合并后的值（如可自动合并）
    needs_manual_review: bool = False        # 是否需要 HR 裁决
    reason: str = ""                         # 冲突原因描述


@dataclass
class ConflictReport:
    """完整冲突检测报告。"""
    candidate_id: str
    conflicts: list[Conflict] = field(default_factory=list)
    auto_resolved_count: int = 0
    manual_review_count: int = 0
    total_resumes_compared: int = 0


# ---------------------------------------------------------------------------
# 数据冲突检测引擎
# ---------------------------------------------------------------------------

class ConflictDetector:
    """
    数据冲突检测引擎。

    比较同一候选人不同简历中的同名字段值，自动检测冲突并尝试合并。
    无法自动合并的冲突返回给 HR 裁决。
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    async def detect_conflicts(self, candidate_id: str) -> list[Conflict]:
        """
        检测候选人所有简历之间的数据冲突。

        Args:
            candidate_id: 候选人 UUID。

        Returns:
            冲突列表，按严重程度排序（时间线冲突 > 值冲突 > 格式冲突）。
        """
        resumes = await self._load_resumes(UUID(candidate_id))

        if len(resumes) < 2:
            logger.info("detect_conflicts: 候选人 %s 简历不足 2 份，无需检测", candidate_id)
            return []

        logger.info(
            "detect_conflicts: 候选人 %s 共 %d 份简历，开始检测",
            candidate_id, len(resumes),
        )

        conflicts: list[Conflict] = []

        # 1. 基本信息字段冲突检测
        conflicts.extend(self._detect_basic_info_conflicts(resumes))

        # 2. 时间线冲突检测
        conflicts.extend(self._detect_timeline_conflicts(resumes))

        # 3. 格式一致性检测
        conflicts.extend(self._detect_format_conflicts(resumes))

        # 按严重程度排序
        severity_order = {
            ConflictType.TIMELINE: 0,
            ConflictType.VALUE: 1,
            ConflictType.FORMAT: 2,
        }
        conflicts.sort(key=lambda c: severity_order.get(c.conflict_type, 99))

        # 统计
        auto_resolved = sum(1 for c in conflicts if not c.needs_manual_review)
        manual_count = sum(1 for c in conflicts if c.needs_manual_review)

        logger.info(
            "detect_conflicts: 候选人 %s 检测到 %d 个冲突 (自动解决=%d, 需裁决=%d)",
            candidate_id, len(conflicts), auto_resolved, manual_count,
        )
        return conflicts

    async def detect_and_report(self, candidate_id: str) -> ConflictReport:
        """
        检测冲突并返回完整报告。

        Args:
            candidate_id: 候选人 UUID。

        Returns:
            ConflictReport 包含冲突列表和统计信息。
        """
        conflicts = await self.detect_conflicts(candidate_id)
        resumes = await self._load_resumes(UUID(candidate_id))

        return ConflictReport(
            candidate_id=candidate_id,
            conflicts=conflicts,
            auto_resolved_count=sum(1 for c in conflicts if not c.needs_manual_review),
            manual_review_count=sum(1 for c in conflicts if c.needs_manual_review),
            total_resumes_compared=len(resumes),
        )

    async def resolve_conflict(
        self,
        candidate_id: str,
        field_path: str,
        chosen_value: Any,
        resolved_by: str,
    ) -> dict[str, Any]:
        """
        HR 手动裁决冲突。

        Args:
            candidate_id: 候选人 UUID。
            field_path: 冲突字段路径。
            chosen_value: HR 选择的值。
            resolved_by: 裁决人 ID。

        Returns:
            裁决结果确认。
        """
        candidate = await self._load_candidate(UUID(candidate_id))
        if candidate is None:
            raise ValueError(f"Candidate not found: {candidate_id}")

        # 更新候选人 profile 中对应字段的值
        profile = candidate.profile or {}
        self._set_nested_value(profile, field_path, chosen_value)
        candidate.profile = profile
        candidate.version += 1
        await self.db.flush()

        logger.info(
            "resolve_conflict: candidate=%s field=%s resolved_by=%s",
            candidate_id, field_path, resolved_by,
        )
        return {
            "status": "resolved",
            "candidate_id": candidate_id,
            "field_path": field_path,
            "chosen_value": chosen_value,
            "resolved_by": resolved_by,
        }

    # ------------------------------------------------------------------
    # 基本信息冲突检测
    # ------------------------------------------------------------------

    # 需要检测的基本信息字段
    _BASIC_INFO_FIELDS = [
        "name", "email", "phone", "location",
        "current_company", "current_title",
        "years_of_experience", "gender", "age",
    ]

    def _detect_basic_info_conflicts(self, resumes: list[Resume]) -> list[Conflict]:
        """检测基本信息字段的值冲突。"""
        conflicts: list[Conflict] = []

        for field_name in self._BASIC_INFO_FIELDS:
            field_values: dict[str, ConflictValue] = {}
            has_meaningful_diff = False
            first_normalized: str | None = None

            for resume in resumes:
                parsed = resume.parsed_data or {}
                basic = parsed.get("basic_info") or {}
                raw_value = basic.get(field_name)

                if raw_value is None or str(raw_value).strip() == "":
                    continue

                value_str = str(raw_value).strip()
                normalized = self._normalize_value(field_name, value_str)

                resume_id = str(resume.id)
                credibility = (resume.credibility or {}).get("score", 50.0)

                if first_normalized is None:
                    first_normalized = normalized

                if normalized != first_normalized and first_normalized is not None:
                    has_meaningful_diff = True

                field_values[resume_id] = ConflictValue(
                    resume_id=resume_id,
                    value=raw_value,
                    credibility_score=credibility,
                    created_at=str(resume.created_at) if resume.created_at else None,
                )

            if has_meaningful_diff and len(field_values) >= 2:
                conflict = self._create_value_conflict(
                    f"basic_info.{field_name}",
                    list(field_values.values()),
                    resumes,
                )
                conflicts.append(conflict)

        return conflicts

    def _create_value_conflict(
        self,
        field_path: str,
        values: list[ConflictValue],
        resumes: list[Resume],
    ) -> Conflict:
        """创建值冲突并尝试自动合并。"""
        # 尝试自动合并
        merged_value, strategy, needs_manual = self._auto_merge(field_path, values, resumes)

        return Conflict(
            field_path=field_path,
            conflict_type=ConflictType.VALUE,
            values=values,
            auto_merge_strategy=strategy,
            auto_merged_value=merged_value,
            needs_manual_review=needs_manual,
            reason=f"字段 '{field_path}' 在 {len(values)} 份简历中存在不同值",
        )

    # ------------------------------------------------------------------
    # 时间线冲突检测
    # ------------------------------------------------------------------

    def _detect_timeline_conflicts(self, resumes: list[Resume]) -> list[Conflict]:
        """检测工作经历时间线的矛盾。"""
        conflicts: list[Conflict] = []

        # 收集所有简历中的工作经历
        all_work: list[tuple[str, dict[str, Any], float]] = []  # (resume_id, exp, cred)
        for resume in resumes:
            parsed = resume.parsed_data or {}
            work_list: list[dict[str, Any]] = parsed.get("work_experience") or []
            cred = (resume.credibility or {}).get("score", 50.0)
            for exp in work_list:
                all_work.append((str(resume.id), exp, cred))

        # 检测同一公司的重叠时间段
        company_periods: dict[str, list[tuple[str, str, str, str]]] = {}  # company -> [(resume_id, start, end, title)]
        for resume_id, exp, _ in all_work:
            company = str(exp.get("company", "")).strip()
            start = str(exp.get("start_date", "")).strip()
            end = str(exp.get("end_date", "")).strip()
            title = str(exp.get("title") or exp.get("position", "")).strip()

            if not company:
                continue
            if company not in company_periods:
                company_periods[company] = []
            company_periods[company].append((resume_id, start, end, title))

        # 检查同公司不同简历的时间矛盾
        for company, periods in company_periods.items():
            if len(periods) < 2:
                continue

            # 检查来自不同简历的时间冲突
            for i in range(len(periods)):
                for j in range(i + 1, len(periods)):
                    rid_i, start_i, end_i, title_i = periods[i]
                    rid_j, start_j, end_j, title_j = periods[j]

                    if rid_i == rid_j:
                        continue  # 同一简历不检查

                    # 检查相同职位但不同时间段
                    if title_i and title_j and self._normalize_value("title", title_i) == self._normalize_value("title", title_j):
                        if start_i != start_j or end_i != end_j:
                            cred_i = next((c for rid, _, c in all_work if rid == rid_i), 0.0)
                            cred_j = next((c for rid, _, c in all_work if rid == rid_j), 0.0)

                            conflicts.append(Conflict(
                                field_path=f"work_experience.{company}.{title_i}.date_range",
                                conflict_type=ConflictType.TIMELINE,
                                values=[
                                    ConflictValue(resume_id=rid_i, value=f"{start_i} ~ {end_i}", credibility_score=cred_i),
                                    ConflictValue(resume_id=rid_j, value=f"{start_j} ~ {end_j}", credibility_score=cred_j),
                                ],
                                auto_merge_strategy=MergeStrategy.MANUAL,
                                auto_merged_value=None,
                                needs_manual_review=True,
                                reason=f"公司 '{company}' 职位 '{title_i}' 在不同简历中时间不一致",
                            ))

        return conflicts

    # ------------------------------------------------------------------
    # 格式冲突检测
    # ------------------------------------------------------------------

    def _detect_format_conflicts(self, resumes: list[Resume]) -> list[Conflict]:
        """检测格式一致性问题（如日期格式不统一）。"""
        conflicts: list[Conflict] = []

        # 收集所有日期字段
        date_fields = [
            ("work_experience", "start_date"),
            ("work_experience", "end_date"),
            ("education", "start_date"),
            ("education", "end_date"),
        ]

        for category, date_field in date_fields:
            date_formats: dict[str, list[str]] = {}  # normalized_format -> [resume_ids]

            for resume in resumes:
                parsed = resume.parsed_data or {}
                items: list[dict[str, Any]] = parsed.get(category) or []
                for item in items:
                    date_val = str(item.get(date_field, "")).strip()
                    if not date_val:
                        continue
                    fmt = self._detect_date_format(date_val)
                    if fmt not in date_formats:
                        date_formats[fmt] = []
                    date_formats[fmt].append(str(resume.id))

            # 如果有不止一种格式，记录冲突
            if len(date_formats) > 1:
                format_values: list[ConflictValue] = []
                for fmt, resume_ids in date_formats.items():
                    for rid in resume_ids:
                        resume = next((r for r in resumes if str(r.id) == rid), None)
                        cred = (resume.credibility or {}).get("score", 50.0) if resume else 0.0
                        format_values.append(ConflictValue(
                            resume_id=rid,
                            value=f"格式: {fmt}",
                            credibility_score=cred,
                        ))

                if format_values:
                    conflicts.append(Conflict(
                        field_path=f"{category}.{date_field}",
                        conflict_type=ConflictType.FORMAT,
                        values=format_values,
                        auto_merge_strategy=MergeStrategy.NEWEST,
                        auto_merged_value=f"统一为 {next(iter(date_formats.keys()))} 格式",
                        needs_manual_review=False,
                        reason=f"{category}.{date_field} 存在 {len(date_formats)} 种不同日期格式",
                    ))

        return conflicts

    # ------------------------------------------------------------------
    # 自动合并策略
    # ------------------------------------------------------------------

    def _auto_merge(
        self,
        field_path: str,
        values: list[ConflictValue],
        resumes: list[Resume],
    ) -> tuple[Any, MergeStrategy, bool]:
        """
        尝试自动合并冲突值。

        Returns:
            (merged_value, strategy_used, needs_manual_review)
        """
        if len(values) == 0:
            return None, MergeStrategy.MANUAL, True

        if len(values) == 1:
            return values[0].value, MergeStrategy.NEWEST, False

        # 策略选择基于字段类型
        field_name = field_path.rsplit(".", 1)[-1]

        # 联系方式类：取最新
        if field_name in ("phone", "email", "location"):
            return self._merge_by_newest(values), MergeStrategy.NEWEST, False

        # 经验年限：取最大值（通常更完整）
        if field_name == "years_of_experience":
            return self._merge_by_max(values), MergeStrategy.MOST_COMPLETE, False

        # 姓名/公司/职位：取可信度最高
        if field_name in ("name", "current_company", "current_title"):
            merged = self._merge_by_credibility(values)
            # 如果差异太大则需人工裁决
            unique_vals = set(str(v.value).strip() for v in values)
            needs_manual = len(unique_vals) > 2  # 超过 2 种不同值，自动合并风险高
            return merged, MergeStrategy.HIGHEST_CREDIBILITY, needs_manual

        # 默认：取可信度最高，如差异显著需人工
        merged = self._merge_by_credibility(values)
        unique_vals = set(str(v.value).strip() for v in values)
        needs_manual = len(unique_vals) > 2
        return merged, MergeStrategy.HIGHEST_CREDIBILITY, needs_manual

    @staticmethod
    def _merge_by_newest(values: list[ConflictValue]) -> Any:
        """取最新简历的值。"""
        sorted_vals = sorted(values, key=lambda v: v.created_at or "", reverse=True)
        return sorted_vals[0].value

    @staticmethod
    def _merge_by_credibility(values: list[ConflictValue]) -> Any:
        """取可信度最高简历的值。"""
        sorted_vals = sorted(values, key=lambda v: v.credibility_score, reverse=True)
        return sorted_vals[0].value

    @staticmethod
    def _merge_by_max(values: list[ConflictValue]) -> Any:
        """取数值最大的值（用于年限等单调递增字段）。"""
        best = values[0]
        for v in values[1:]:
            try:
                if float(str(v.value)) > float(str(best.value)):
                    best = v
            except (ValueError, TypeError):
                pass
        return best.value

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    async def _load_resumes(self, candidate_id: UUID) -> list[Resume]:
        """加载候选人的全部已完成简历。"""
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

    async def _load_candidate(self, candidate_id: UUID) -> Candidate | None:
        """加载候选人记录。"""
        stmt = select(Candidate).where(Candidate.id == candidate_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _normalize_value(field_name: str, value: str) -> str:
        """标准化字段值用于比较（去空格、统一大小写等）。"""
        normalized = value.strip().lower()
        # 电话号码：只保留数字
        if field_name in ("phone",):
            normalized = re.sub(r"\D", "", normalized)
        # 邮箱：统一小写
        if field_name == "email":
            normalized = normalized.replace(" ", "")
        return normalized

    @staticmethod
    def _detect_date_format(date_str: str) -> str:
        """检测日期字符串的格式类型。"""
        if re.match(r"^\d{4}$", date_str):
            return "YYYY"
        if re.match(r"^\d{4}-\d{2}$", date_str):
            return "YYYY-MM"
        if re.match(r"^\d{4}/\d{2}$", date_str):
            return "YYYY/MM"
        if re.match(r"^\d{4}\.\d{2}$", date_str):
            return "YYYY.MM"
        if re.match(r"^\d{4}年\d{1,2}月", date_str):
            return "YYYY年MM月"
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            return "YYYY-MM-DD"
        return "other"

    @staticmethod
    def _set_nested_value(data: dict, path: str, value: Any) -> None:
        """设置嵌套字典中指定路径的值。"""
        keys = path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
