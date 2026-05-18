"""
AI 隐性推理引擎 (M3)。

从候选人的工作经历、技能列表中推断出隐含信息：
  - 隐含技能推断：从职位描述推断候选人可能掌握但未明示的技能
  - 职业方向推断：从职业轨迹推断候选人的发展方向和跳槽倾向

每个推理结果包含:
  - 推理内容
  - 置信度 (0-1)
  - 推理链 (chain-of-thought)
  - 来源引用

使用 @AiCapability 装饰器标记 AI 调用，推理结果持久化到 inference 相关字段。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.decorators.ai_capability import AiCapability
from app.models.candidate import Candidate
from app.services.ai_client import ai_client

logger = logging.getLogger("hiremind.inference_engine")


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------

@dataclass
class InferredSkill:
    """推断出的隐含技能。"""
    name: str
    confidence: float                       # 0-1 置信度
    reasoning_chain: list[str]              # 推理链（步骤描述）
    source_refs: list[str]                  # 来源引用（工作经历索引等）
    category: str = "inferred"              # 分类: inferred / refined / augmented


@dataclass
class CareerDirection:
    """职业方向推断结果。"""
    direction: str                          # 推断方向描述
    confidence: float                       # 0-1 置信度
    reasoning_chain: list[str]              # 推理链
    source_refs: list[str]                  # 来源引用
    trajectory_type: str = "stable"         # stable / upward / lateral / downward / pivoting
    estimated_next_role: str | None = None  # 预测下一个职位
    retention_risk: str = "low"             # low / medium / high


@dataclass
class InferenceResult:
    """完整的推理结果集。"""
    inferred_skills: list[InferredSkill] = field(default_factory=list)
    career_direction: CareerDirection | None = None
    candidate_id: str = ""
    inferred_at: str = ""
    model_used: str = ""


# ---------------------------------------------------------------------------
# 技能推断的领域知识库（规则层）
# ---------------------------------------------------------------------------

# 岗位 → 隐含技能映射（不依赖 AI 的规则推断）
_ROLE_SKILL_MAP: dict[str, list[str]] = {
    "前端": ["HTML", "CSS", "JavaScript", "TypeScript", "Git", "Webpack/Vite"],
    "后端": ["Git", "Linux", "SQL", "REST API", "数据库设计"],
    "全栈": ["HTML", "CSS", "JavaScript", "SQL", "Git", "Linux", "REST API"],
    "产品经理": ["需求分析", "Axure/Figma", "数据分析", "项目管理", "用户研究"],
    "项目经理": ["项目管理", "风险管理", "沟通协调", "进度控制"],
    "测试": ["测试用例设计", "缺陷管理", "自动化测试", "SQL"],
    "运维": ["Linux", "Docker", "CI/CD", "监控告警", "Shell 脚本"],
    "数据": ["SQL", "Python", "数据可视化", "统计分析"],
    "算法": ["Python", "数学建模", "机器学习", "数据分析"],
    "设计": ["Figma/Sketch", "用户研究", "交互设计", "设计规范"],
    "DevOps": ["Docker", "Kubernetes", "CI/CD", "Linux", "云服务"],
    "移动端": ["移动 UI 设计", "API 调用", "性能优化"],
    "架构师": ["系统设计", "架构模式", "性能优化", "技术选型"],
}

# 技术栈关键词 → 可能关联技能
_TECH_CORRELATIONS: dict[str, list[str]] = {
    "React": ["Redux/MobX", "JSX", "组件化", "Hooks"],
    "Vue": ["Vuex/Pinia", "Vue Router", "组件化"],
    "Java": ["Spring", "Maven/Gradle", "JVM 调优"],
    "Python": ["pip", "虚拟环境", "Django/Flask/FastAPI"],
    "Go": ["goroutine", "并发编程", "微服务"],
    "Kubernetes": ["Docker", "Helm", "服务网格"],
    "AWS": ["EC2", "S3", "Lambda", "CloudFormation"],
    "MySQL": ["SQL 优化", "索引设计", "数据库调优"],
    "Redis": ["缓存策略", "数据结构", "高可用"],
    "Docker": ["容器化", "镜像管理", "Docker Compose"],
}


# ---------------------------------------------------------------------------
# AI 隐性推理引擎
# ---------------------------------------------------------------------------

class InferenceEngine:
    """
    AI 隐性推理引擎。

    两层推理:
      1. 规则层: 基于领域知识库的确定性推断（无 AI 调用）
      2. AI 层: 通过 LLM 进行深度推理（@AiCapability 标记）

    推理结果持久化到 candidate.inference_data JSONB 字段。
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    async def infer_skills(
        self,
        work_experiences: list[dict[str, Any]],
        *,
        existing_skills: list[str] | None = None,
    ) -> list[InferredSkill]:
        """
        从工作经历推断隐含技能。

        两阶段:
          1. 规则层: 基于职位名称匹配领域知识库
          2. AI 层: 将工作经历描述发给 LLM 推断

        Args:
            work_experiences: 工作经历列表。
            existing_skills: 候选人已有的显式技能（用于去重）。

        Returns:
            推断出的隐含技能列表，按置信度降序排列。
        """
        existing = set(s.lower() for s in (existing_skills or []))
        all_inferred: dict[str, InferredSkill] = {}

        # --- 阶段 1: 规则层推断 ---
        rule_skills = self._rule_based_skill_inference(work_experiences, existing)
        for skill in rule_skills:
            all_inferred[skill.name.lower()] = skill

        # --- 阶段 2: AI 层推断 ---
        ai_skills = await self._ai_skill_inference(work_experiences, existing)
        for skill in ai_skills:
            key = skill.name.lower()
            if key in all_inferred:
                # AI 和规则层都推断到 → 提升置信度
                all_inferred[key].confidence = min(
                    1.0, all_inferred[key].confidence + 0.15
                )
                all_inferred[key].category = "augmented"
            else:
                all_inferred[key] = skill

        # 过滤掉已存在的技能
        result = [
            s for s in all_inferred.values()
            if s.name.lower() not in existing
        ]
        result.sort(key=lambda s: s.confidence, reverse=True)

        logger.info(
            "infer_skills: rule=%d ai=%d merged=%d (after dedup from %d existing)",
            len(rule_skills), len(ai_skills), len(result), len(existing),
        )
        return result

    async def infer_career_direction(
        self,
        work_experiences: list[dict[str, Any]],
    ) -> CareerDirection:
        """
        从职业轨迹推断发展方向。

        分析维度:
          - 职位层级变化趋势（上升/平稳/横向）
          - 行业/领域变化
          - 跳槽频率
          - 预测下一阶段可能的方向

        Args:
            work_experiences: 按时间排列的工作经历列表。

        Returns:
            CareerDirection 推断结果。
        """
        if not work_experiences:
            return CareerDirection(
                direction="数据不足，无法推断",
                confidence=0.0,
                reasoning_chain=["无工作经历数据"],
                source_refs=[],
            )

        # 规则层分析
        trajectory = self._analyze_trajectory(work_experiences)
        retention = self._analyze_retention_risk(work_experiences)

        # AI 层深度分析
        ai_direction = await self._ai_career_inference(work_experiences, trajectory)

        # 合并结果
        if ai_direction:
            return CareerDirection(
                direction=ai_direction.get("direction", trajectory.get("summary", "")),
                confidence=ai_direction.get("confidence", 0.5),
                reasoning_chain=ai_direction.get("reasoning_chain", []),
                source_refs=ai_direction.get("source_refs", []),
                trajectory_type=trajectory.get("type", "stable"),
                estimated_next_role=ai_direction.get("estimated_next_role"),
                retention_risk=retention.get("risk_level", "low"),
            )

        # AI 不可用时的降级结果
        return CareerDirection(
            direction=trajectory.get("summary", "无法推断"),
            confidence=trajectory.get("confidence", 0.3),
            reasoning_chain=trajectory.get("reasoning_chain", []),
            source_refs=trajectory.get("source_refs", []),
            trajectory_type=trajectory.get("type", "stable"),
            retention_risk=retention.get("risk_level", "low"),
        )

    async def run_full_inference(
        self,
        candidate_id: str,
    ) -> InferenceResult:
        """
        执行完整推理流程：技能推断 + 职业方向推断 + 持久化。

        Args:
            candidate_id: 候选人 UUID。

        Returns:
            InferenceResult 完整推理结果集。
        """
        candidate = await self._load_candidate(UUID(candidate_id))
        if candidate is None:
            raise ValueError(f"Candidate not found: {candidate_id}")

        profile = candidate.profile or {}
        work_experiences: list[dict[str, Any]] = profile.get("work_experience") or []
        existing_skills = [
            s.get("name", s) if isinstance(s, dict) else str(s)
            for s in (profile.get("skills") or [])
        ]

        # 并行执行两种推理
        import asyncio
        skills_task = self.infer_skills(work_experiences, existing_skills=existing_skills)
        direction_task = self.infer_career_direction(work_experiences)
        inferred_skills, career_direction = await asyncio.gather(
            skills_task, direction_task,
        )

        result = InferenceResult(
            inferred_skills=inferred_skills,
            career_direction=career_direction,
            candidate_id=candidate_id,
            inferred_at=datetime.utcnow().isoformat(),
            model_used="rule+ai",
        )

        # 持久化到 candidate.inference_data
        await self._persist_inference(candidate, result)

        logger.info(
            "run_full_inference: candidate=%s skills=%d direction=%s",
            candidate_id, len(inferred_skills),
            career_direction.direction if career_direction else "N/A",
        )
        return result

    # ------------------------------------------------------------------
    # 规则层推断
    # ------------------------------------------------------------------

    def _rule_based_skill_inference(
        self,
        work_experiences: list[dict[str, Any]],
        existing_skills: set[str],
    ) -> list[InferredSkill]:
        """基于领域知识库的规则层技能推断。"""
        inferred: dict[str, InferredSkill] = {}

        for idx, exp in enumerate(work_experiences):
            title = str(exp.get("title") or exp.get("position", "")).lower()
            description = str(exp.get("description", ""))

            # 基于职位名称匹配
            for role_key, skills in _ROLE_SKILL_MAP.items():
                if role_key.lower() in title:
                    for skill_name in skills:
                        if skill_name.lower() not in existing_skills:
                            self._add_inferred_skill(
                                inferred, skill_name, 0.6,
                                [f"基于职位 '{title}' 的领域知识匹配"],
                                [f"work_experience[{idx}]"],
                            )

            # 基于技术栈关联
            for tech, related in _TECH_CORRELATIONS.items():
                if tech.lower() in title or tech.lower() in description.lower():
                    for skill_name in related:
                        if skill_name.lower() not in existing_skills:
                            self._add_inferred_skill(
                                inferred, skill_name, 0.5,
                                [f"基于技术栈 '{tech}' 的关联推断"],
                                [f"work_experience[{idx}]"],
                            )

        return list(inferred.values())

    @staticmethod
    def _add_inferred_skill(
        target: dict[str, InferredSkill],
        name: str,
        confidence: float,
        reasoning: list[str],
        source_refs: list[str],
    ) -> None:
        """添加推断技能到字典，已存在时提升置信度。"""
        key = name.lower()
        if key in target:
            target[key].confidence = min(1.0, target[key].confidence + 0.1)
            target[key].reasoning_chain.extend(reasoning)
            target[key].source_refs.extend(source_refs)
        else:
            target[key] = InferredSkill(
                name=name,
                confidence=confidence,
                reasoning_chain=reasoning,
                source_refs=source_refs,
                category="inferred",
            )

    def _analyze_trajectory(
        self,
        work_experiences: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """分析职业轨迹类型（规则层）。"""
        if len(work_experiences) < 2:
            return {
                "type": "stable",
                "summary": "工作经历不足，难以判断趋势",
                "confidence": 0.3,
                "reasoning_chain": ["仅 1 段或不足 1 段工作经历"],
                "source_refs": [],
            }

        titles = [str(e.get("title") or e.get("position", "")) for e in work_experiences]
        # 简单关键词判断层级趋势
        seniority_scores = []
        for title in titles:
            score = 1  # junior baseline
            for kw in ["高级", "Senior", "Lead", "资深"]:
                if kw.lower() in title.lower():
                    score = 2
            for kw in ["经理", "Manager", "主管", "总监", "Director", "VP", "首席"]:
                if kw.lower() in title.lower():
                    score = 3
            for kw in ["CTO", "CEO", "CIO", "VP", "总裁"]:
                if kw.lower() in title.lower():
                    score = 4
            seniority_scores.append(score)

        # 趋势判断
        increasing = all(
            seniority_scores[i] <= seniority_scores[i + 1]
            for i in range(len(seniority_scores) - 1)
        )
        decreasing = all(
            seniority_scores[i] >= seniority_scores[i + 1]
            for i in range(len(seniority_scores) - 1)
        )

        if increasing and seniority_scores[-1] > seniority_scores[0]:
            t_type = "upward"
            summary = "职业轨迹呈上升趋势，从初级/中级向高级/管理层发展"
        elif decreasing:
            t_type = "downward"
            summary = "职业轨迹呈下降趋势，需关注原因"
        else:
            t_type = "lateral"
            summary = "职业轨迹为横向发展，在不同公司/领域间平调"

        return {
            "type": t_type,
            "summary": summary,
            "confidence": 0.6,
            "reasoning_chain": [
                f"分析了 {len(titles)} 段工作经历的职位层级",
                f"层级分数序列: {seniority_scores}",
            ],
            "source_refs": [f"work_experience[{i}]" for i in range(len(titles))],
        }

    def _analyze_retention_risk(
        self,
        work_experiences: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """分析跳槽频率和留存风险（规则层）。"""
        import re as _re

        durations: list[float] = []
        for exp in work_experiences:
            start = exp.get("start_date")
            end = exp.get("end_date")
            if not start:
                continue
            try:
                s_year = int(_re.search(r"(\d{4})", str(start)).group(1))  # type: ignore[union-attr]
                if end and "present" not in str(end).lower():
                    e_year = int(_re.search(r"(\d{4})", str(end)).group(1))  # type: ignore[union-attr]
                else:
                    e_year = datetime.utcnow().year
                durations.append(float(e_year - s_year))
            except (AttributeError, ValueError, TypeError):
                continue

        if not durations:
            return {"risk_level": "unknown", "avg_duration": 0.0}

        avg_duration = sum(durations) / len(durations)

        if avg_duration < 1.5:
            risk = "high"
        elif avg_duration < 3.0:
            risk = "medium"
        else:
            risk = "low"

        return {"risk_level": risk, "avg_duration": avg_duration}

    # ------------------------------------------------------------------
    # AI 层推断（@AiCapability 标记）
    # ------------------------------------------------------------------

    @AiCapability(
        capability="inference_skills",
        name="AI Skill Inference",
        tool_name="hr_inference_skills",
        llm_model="gpt-4o-mini",
        fallback_model="gpt-3.5-turbo",
        allowed_callers=["api", "agent"],
        ai_capability_id="hr_inference_skills_v1",
        description="从工作经历推断隐含技能",
        data_classification="L2",
        timeout=30.0,
    )
    async def _ai_skill_inference(
        self,
        work_experiences: list[dict[str, Any]],
        existing_skills: set[str],
    ) -> list[InferredSkill]:
        """通过 LLM 推断隐含技能。"""
        if not work_experiences:
            return []

        prompt = self._build_skill_prompt(work_experiences, existing_skills)
        messages = [
            {"role": "system", "content": "你是一名资深猎头，擅长从候选人工作经历中推断其隐含技能。"},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await ai_client.chat_completion(
                messages,
                response_format={"type": "json_object"},
                max_tokens=2048,
            )
        except Exception as exc:
            logger.warning("AI 技能推断失败: %s", exc)
            return []

        if not response:
            return []

        return self._parse_skill_response(response)

    @AiCapability(
        capability="inference_career",
        name="AI Career Direction Inference",
        tool_name="hr_inference_career",
        llm_model="gpt-4o-mini",
        fallback_model="gpt-3.5-turbo",
        allowed_callers=["api", "agent"],
        ai_capability_id="hr_inference_career_v1",
        description="从职业轨迹推断发展方向",
        data_classification="L2",
        timeout=30.0,
    )
    async def _ai_career_inference(
        self,
        work_experiences: list[dict[str, Any]],
        trajectory_hint: dict[str, Any],
    ) -> dict[str, Any] | None:
        """通过 LLM 推断职业方向。"""
        if not work_experiences:
            return None

        prompt = self._build_career_prompt(work_experiences, trajectory_hint)
        messages = [
            {"role": "system", "content": "你是一名资深猎头，擅长分析候选人的职业发展轨迹。"},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await ai_client.chat_completion(
                messages,
                response_format={"type": "json_object"},
                max_tokens=1024,
            )
        except Exception as exc:
            logger.warning("AI 职业方向推断失败: %s", exc)
            return None

        if not response:
            return None

        try:
            content = response.get("content", "{}")
            if isinstance(content, str):
                return json.loads(content)
            return content  # type: ignore[return-value]
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("AI 职业方向推断响应解析失败: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Prompt 构建
    # ------------------------------------------------------------------

    def _build_skill_prompt(
        self,
        work_experiences: list[dict[str, Any]],
        existing_skills: set[str],
    ) -> str:
        """构建技能推断 Prompt。"""
        exp_text = json.dumps(work_experiences, ensure_ascii=False, indent=2)
        existing_text = ", ".join(sorted(existing_skills)) if existing_skills else "无"

        return f"""请分析以下工作经历，推断候选人可能掌握但未明示的隐含技能。

工作经历:
{exp_text}

已有显式技能: {existing_text}

请返回 JSON 格式:
{{
  "inferred_skills": [
    {{
      "name": "技能名称",
      "confidence": 0.7,
      "reasoning": "推断理由",
      "source": "来源工作经历索引"
    }}
  ]
}}

要求:
1. 仅推断合理的隐含技能，置信度在 0.3-0.9 之间
2. 每个技能必须给出推断理由
3. 不要包含已有显式技能
4. 最多推断 15 个技能"""

    def _build_career_prompt(
        self,
        work_experiences: list[dict[str, Any]],
        trajectory_hint: dict[str, Any],
    ) -> str:
        """构建职业方向推断 Prompt。"""
        exp_text = json.dumps(work_experiences, ensure_ascii=False, indent=2)
        hint_text = json.dumps(trajectory_hint, ensure_ascii=False)

        return f"""请分析以下候选人的工作经历，推断其职业发展方向。

工作经历:
{exp_text}

规则层分析提示: {hint_text}

请返回 JSON 格式:
{{
  "direction": "一句话描述职业发展方向",
  "confidence": 0.7,
  "reasoning_chain": ["推理步骤1", "推理步骤2", "推理步骤3"],
  "source_refs": ["work_experience[0]", "work_experience[1]"],
  "estimated_next_role": "预测的下一个职位",
  "trajectory_type": "upward/stable/lateral/downward/pivoting"
}}

要求:
1. reasoning_chain 必须包含 2-5 个推理步骤
2. confidence 在 0.3-0.9 之间
3. 结合行业趋势给出判断"""

    # ------------------------------------------------------------------
    # 响应解析
    # ------------------------------------------------------------------

    def _parse_skill_response(self, response: dict[str, Any]) -> list[InferredSkill]:
        """解析 AI 技能推断响应。"""
        content = response.get("content", "{}")
        try:
            if isinstance(content, str):
                data = json.loads(content)
            else:
                data = content
        except (json.JSONDecodeError, TypeError):
            logger.warning("技能推断响应非有效 JSON")
            return []

        raw_skills: list[dict[str, Any]] = data.get("inferred_skills") or []
        result: list[InferredSkill] = []

        for raw in raw_skills:
            name = raw.get("name", "").strip()
            if not name:
                continue
            confidence = float(raw.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))

            result.append(InferredSkill(
                name=name,
                confidence=confidence,
                reasoning_chain=[raw.get("reasoning", "")],
                source_refs=[raw.get("source", "")],
                category="inferred",
            ))

        return result

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------

    async def _load_candidate(self, candidate_id: UUID) -> Candidate | None:
        """加载候选人记录。"""
        stmt = select(Candidate).where(Candidate.id == candidate_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _persist_inference(
        self,
        candidate: Candidate,
        result: InferenceResult,
    ) -> None:
        """将推理结果持久化到 candidate.inference_data。"""
        inference_data = {
            "inferred_skills": [
                {
                    "name": s.name,
                    "confidence": s.confidence,
                    "reasoning_chain": s.reasoning_chain,
                    "source_refs": s.source_refs,
                    "category": s.category,
                }
                for s in result.inferred_skills
            ],
            "career_direction": {
                "direction": result.career_direction.direction if result.career_direction else None,
                "confidence": result.career_direction.confidence if result.career_direction else None,
                "reasoning_chain": result.career_direction.reasoning_chain if result.career_direction else [],
                "trajectory_type": result.career_direction.trajectory_type if result.career_direction else None,
                "estimated_next_role": result.career_direction.estimated_next_role if result.career_direction else None,
                "retention_risk": result.career_direction.retention_risk if result.career_direction else None,
            } if result.career_direction else None,
            "inferred_at": result.inferred_at,
            "model_used": result.model_used,
        }

        candidate.inference_data = inference_data
        candidate.version += 1
        await self.db.flush()

        logger.info(
            "persist_inference: candidate=%s skills=%d",
            candidate.id, len(result.inferred_skills),
        )
