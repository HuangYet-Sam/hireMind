"""
Resume Credibility Scoring Engine (M2).

Performs internal-consistency checks on parsed resume data and returns a
credibility score with per-check details.

Checks implemented:
  1. Date cross-validation   — work/education date overlaps & gaps
  2. Salary reasonableness   — salary range vs. experience years & title
  3. Education-title match   — degree level vs. claimed job title seniority
  4. Work duration sanity    — unreasonably short tenures
  5. Skill consistency       — skill years vs. total work years

All checks are rule-based (no LLM call).  Returns a 0–100 score.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("hiremind.resume_credibility")

# ---------------------------------------------------------------------------
# Constants & lookup tables
# ---------------------------------------------------------------------------

# Expected salary ranges (K CNY/month) by experience years
_SALARY_BANDS: list[tuple[int, int, tuple[float, float]]] = [
    # (min_years, max_years, (low_K, high_K))
    (0, 1, (3.0, 20.0)),
    (1, 3, (5.0, 35.0)),
    (3, 5, (8.0, 50.0)),
    (5, 8, (12.0, 70.0)),
    (8, 10, (15.0, 90.0)),
    (10, 15, (20.0, 120.0)),
    (15, 100, (25.0, 200.0)),
]

# Degree level hierarchy (0 = lowest)
_DEGREE_LEVELS: dict[str, int] = {
    "高中": 1,
    "中专": 1,
    "技校": 1,
    "大专": 2,
    "专科": 2,
    "本科": 3,
    "学士": 3,
    "硕士": 4,
    "研究生": 4,
    "博士": 5,
    "博士后": 6,
    "high school": 1,
    "associate": 2,
    "bachelor": 3,
    "master": 4,
    "phd": 5,
    "postdoc": 6,
}

# Senior title keywords that typically require higher education
_SENIOR_KEYWORDS = frozenset({
    "总监", "VP", "副总裁", "首席", "CIO", "CTO", "CFO", "COO", "CEO",
    "合伙人", "董事", "总经理", "head", "chief", "vp", "director",
    "senior director", "principal", "staff",
})

# Mid-level keywords
_MID_KEYWORDS = frozenset({
    "经理", "主管", "主任", "科长", "高级", "senior", "manager",
    "lead", "leader",
})


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _parse_year(date_str: str | None) -> int | None:
    """Extract 4-digit year from a date string."""
    if not date_str:
        return None
    m = re.search(r"(\d{4})", str(date_str))
    return int(m.group(1)) if m else None


def _estimate_total_work_years(
    work_experiences: list[dict[str, Any]],
) -> float:
    """Estimate total years of work experience by merging date ranges."""
    ranges: list[tuple[int, int]] = []
    for exp in work_experiences:
        start = _parse_year(exp.get("start_date"))
        end = _parse_year(exp.get("end_date"))  # may be None = present
        if start is None:
            continue
        import datetime
        end = end or datetime.date.today().year
        if end > start:
            ranges.append((start, end))

    if not ranges:
        return 0.0

    # Merge overlapping ranges
    ranges.sort()
    merged: list[tuple[int, int]] = [ranges[0]]
    for start, end in ranges[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))

    return float(sum(e - s for s, e in merged))


def _max_degree_level(education: list[dict[str, Any]]) -> int:
    """Return the highest degree level from education entries."""
    max_level = 0
    for edu in education:
        degree = str(edu.get("degree", "")).strip().lower()
        for key, level in _DEGREE_LEVELS.items():
            if key in degree:
                max_level = max(max_level, level)
                break
    return max_level


def _check_title_seniority(title: str) -> str:
    """Classify a job title as 'senior', 'mid', or 'junior'."""
    title_lower = title.lower()
    for kw in _SENIOR_KEYWORDS:
        if kw.lower() in title_lower:
            return "senior"
    for kw in _MID_KEYWORDS:
        if kw.lower() in title_lower:
            return "mid"
    return "junior"


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------

def _check_date_overlap(
    work_experiences: list[dict[str, Any]],
    education: list[dict[str, Any]],
) -> dict[str, Any]:
    """Check for suspicious full-time work overlaps (>3 months)."""
    issues: list[str] = []
    date_ranges: list[tuple[int, int, str]] = []

    for exp in work_experiences:
        start = _parse_year(exp.get("start_date"))
        end = _parse_year(exp.get("end_date"))
        company = exp.get("company", "Unknown")
        if start is not None:
            import datetime
            end = end or datetime.date.today().year
            date_ranges.append((start, end, str(company)))

    # Check pairwise overlaps
    for i in range(len(date_ranges)):
        for j in range(i + 1, len(date_ranges)):
            s1, e1, c1 = date_ranges[i]
            s2, e2, c2 = date_ranges[j]
            overlap_start = max(s1, s2)
            overlap_end = min(e1, e2)
            if overlap_end - overlap_start >= 1:  # ≥1 year overlap
                issues.append(
                    f"'{c1}' ({s1}-{e1}) 与 '{c2}' ({s2}-{e2}) 存在 {overlap_end - overlap_start} 年重叠"
                )

    passed = len(issues) == 0
    return {
        "name": "date_cross_validation",
        "passed": passed,
        "detail": (
            "工作经历日期无异常交叉" if passed
            else f"发现 {len(issues)} 处日期交叉: " + "; ".join(issues[:3])
        ),
    }


def _check_salary_reasonableness(
    resume_data: dict[str, Any],
) -> dict[str, Any]:
    """Validate salary expectations against experience years."""
    basic = resume_data.get("basic_info", {}) or {}
    salary_raw = basic.get("expected_salary") or basic.get("salary")
    if salary_raw is None:
        return {
            "name": "salary_reasonableness",
            "passed": True,
            "detail": "未提供薪资信息，跳过检查",
        }

    # Parse salary to monthly K CNY
    try:
        salary_str = str(salary_raw).replace(",", "").replace("，", "")
        numbers = re.findall(r"[\d.]+", salary_str)
        if not numbers:
            return {
                "name": "salary_reasonableness",
                "passed": True,
                "detail": "无法解析薪资数值，跳过",
            }
        # If range like "15K-25K" or "15000-25000", take midpoint
        nums = [float(n) for n in numbers]
        # Detect unit: if any number > 500, assume raw CNY not K
        if any(n > 500 for n in nums):
            nums = [n / 1000 for n in nums]
        salary_k = sum(nums) / len(nums)
    except (ValueError, IndexError):
        return {
            "name": "salary_reasonableness",
            "passed": True,
            "detail": "薪资格式异常，跳过检查",
        }

    work_years = _estimate_total_work_years(
        resume_data.get("work_experience", []) or []
    )

    low, high = 3.0, 200.0
    for min_y, max_y, (lo, hi) in _SALARY_BANDS:
        if min_y <= work_years < max_y:
            low, high = lo, hi
            break

    passed = low <= salary_k <= high
    detail = (
        f"薪资 {salary_k:.0f}K 在合理范围内 ({low:.0f}K-{high:.0f}K, 经验 {work_years:.0f} 年)"
        if passed
        else f"薪资 {salary_k:.0f}K 超出合理范围 ({low:.0f}K-{high:.0f}K, 经验 {work_years:.0f} 年)"
    )

    return {"name": "salary_reasonableness", "passed": passed, "detail": detail}


def _check_education_title_match(
    resume_data: dict[str, Any],
) -> dict[str, Any]:
    """Check if education level is consistent with seniority of job titles."""
    education = resume_data.get("education", []) or []
    work = resume_data.get("work_experience", []) or []

    if not education or not work:
        return {
            "name": "education_title_match",
            "passed": True,
            "detail": "学历或工作经历信息不完整，跳过检查",
        }

    degree_level = _max_degree_level(education)

    # Find the most senior title
    max_seniority = "junior"
    for exp in work:
        title = str(exp.get("title", ""))
        s = _check_title_seniority(title)
        if s == "senior":
            max_seniority = s
            break
        if s == "mid":
            max_seniority = s

    # Senior titles typically need ≥ bachelor (level 3)
    passed = True
    detail = "学历与岗位级别匹配"
    if max_seniority == "senior" and degree_level < 3:
        passed = False
        detail = f"高级管理岗位但学历等级偏低 (degree_level={degree_level})"
    elif max_seniority == "mid" and degree_level < 2:
        passed = False
        detail = f"中级管理岗位但学历等级偏低 (degree_level={degree_level})"

    return {"name": "education_title_match", "passed": passed, "detail": detail}


def _check_work_duration_sanity(
    work_experiences: list[dict[str, Any]],
) -> dict[str, Any]:
    """Flag very short tenures (< 3 months)."""
    short_tenures: list[str] = []
    for exp in work_experiences:
        start = _parse_year(exp.get("start_date"))
        end = _parse_year(exp.get("end_date"))
        if start is None or end is None:
            continue
        months = (end - start) * 12
        company = exp.get("company", "Unknown")
        if 0 < months < 3:
            short_tenures.append(f"'{company}' 约 {months} 个月")

    if not short_tenures:
        return {
            "name": "work_duration_sanity",
            "passed": True,
            "detail": "工作经历时长均在合理范围内",
        }

    return {
        "name": "work_duration_sanity",
        "passed": False,
        "detail": f"发现 {len(short_tenures)} 段极短任期: " + "; ".join(short_tenures[:3]),
    }


def _check_skill_consistency(
    resume_data: dict[str, Any],
) -> dict[str, Any]:
    """Validate that claimed skill years don't exceed total work years."""
    skills: list[dict[str, Any]] = resume_data.get("skills", []) or []
    work_years = _estimate_total_work_years(
        resume_data.get("work_experience", []) or []
    )

    overstated: list[str] = []
    for skill in skills:
        years_raw = skill.get("years_of_experience") or skill.get("years")
        if years_raw is None:
            continue
        try:
            skill_years = float(str(years_raw).replace("+", ""))
        except (ValueError, TypeError):
            continue
        if skill_years > work_years + 1:  # +1 year tolerance
            name = skill.get("name", "Unknown")
            overstated.append(f"'{name}' {skill_years}年 > 总工作 {work_years:.0f}年")

    if not overstated:
        return {
            "name": "skill_consistency",
            "passed": True,
            "detail": "技能年限与总工作年限一致",
        }

    return {
        "name": "skill_consistency",
        "passed": False,
        "detail": f"发现 {len(overstated)} 项技能年限超出总工作年限: " + "; ".join(overstated[:3]),
    }


# ---------------------------------------------------------------------------
# ResumeCredibilityService
# ---------------------------------------------------------------------------

class ResumeCredibilityService:
    """
    Rule-based credibility scoring for parsed resume data.

    Returns a 0–100 score with detailed per-check breakdown and a list of
    flagged field paths.
    """

    # Weight per check (must sum to 1.0)
    _WEIGHTS: dict[str, float] = {
        "date_cross_validation": 0.30,
        "salary_reasonableness": 0.15,
        "education_title_match": 0.20,
        "work_duration_sanity": 0.20,
        "skill_consistency": 0.15,
    }

    async def score_credibility(self, resume_data: dict[str, Any]) -> dict[str, Any]:
        """
        Score resume credibility.

        Args:
            resume_data: Structured resume dict (output of SmartResumeParser).

        Returns::

            {
                "score": float,           # 0–100
                "checks": [
                    {"name": str, "passed": bool, "detail": str},
                    ...
                ],
                "flagged_fields": [str],   # e.g. ["basic_info.expected_salary"]
            }
        """
        work: list[dict[str, Any]] = resume_data.get("work_experience", []) or []
        education: list[dict[str, Any]] = resume_data.get("education", []) or []

        checks: list[dict[str, Any]] = [
            _check_date_overlap(work, education),
            _check_salary_reasonableness(resume_data),
            _check_education_title_match(resume_data),
            _check_work_duration_sanity(work),
            _check_skill_consistency(resume_data),
        ]

        # Compute weighted score
        weighted_sum = 0.0
        for check in checks:
            weight = self._WEIGHTS.get(check["name"], 0.1)
            weighted_sum += weight if check["passed"] else 0.0

        score = round(weighted_sum * 100, 1)

        # Collect flagged fields
        flagged_fields: list[str] = []
        for check in checks:
            if not check["passed"]:
                flagged_fields.append(_check_to_field_path(check["name"]))

        logger.info(
            "credibility_score=%.1f checks_passed=%d/%d flagged=%s",
            score,
            sum(1 for c in checks if c["passed"]),
            len(checks),
            flagged_fields,
        )

        return {
            "score": score,
            "checks": checks,
            "flagged_fields": flagged_fields,
        }


def _check_to_field_path(check_name: str) -> str:
    """Map check name to the most relevant field path."""
    mapping = {
        "date_cross_validation": "work_experience.date_range",
        "salary_reasonableness": "basic_info.expected_salary",
        "education_title_match": "education.degree",
        "work_duration_sanity": "work_experience.duration",
        "skill_consistency": "skills.years_of_experience",
    }
    return mapping.get(check_name, check_name)


# Singleton (no DB needed — pure logic)
resume_credibility_service = ResumeCredibilityService()
