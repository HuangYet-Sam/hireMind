"""
HR 候选人画像 Agent Tool。

暴露候选人画像查询/构建、AI 推理、冲突检测与裁决能力为 Agent Tool，
通过 ``@AiCapability`` 装饰器注册。

注册能力:
  - ``hr_profile_query``       — 查询候选人画像
  - ``hr_profile_build``       — 构建候选人画像（触发多源聚合）
  - ``hr_inference_trigger``   — 触发 AI 隐性推理
  - ``hr_inference_query``     — 查询推理结果
  - ``hr_conflict_detect``     — 检测数据冲突
  - ``hr_conflict_resolve``    — HR 裁决冲突
"""

from __future__ import annotations

import logging
from typing import Any

from app.decorators.ai_capability import AiCapability

logger = logging.getLogger("hiremind.tools.hr_profile")


# ---------------------------------------------------------------------------
# Tool: HR Profile Query — 查询候选人画像
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_profile_query",
    name="HR Profile Query",
    endpoint="/api/v1/candidates/{candidate_id}/profile",
    method="GET",
    tool_name="hr_profile_query",
    permissions=["candidate:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_profile_query_v1",
    description="查询候选人的标准化画像，包含基本信息、工作经历时间轴、教育背景、技能标签云",
    request_model="ProfileQueryRequest",
    response_model="CandidateProfile",
    rate_limit="100/minute",
    data_classification="L3",
    audit_level="standard",
    tags=["hr", "candidate", "profile", "query"],
    timeout=10.0,
)
async def hr_profile_query(
    candidate_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    查询候选人画像。

    直接从 candidate.profile JSONB 字段返回已构建的画像。
    如需重新构建，请使用 hr_profile_build。

    Args:
        candidate_id: 候选人 UUID。
        tenant_id: 租户标识。

    Returns:
        包含候选人画像信息的字典。
    """
    from app.dependencies import get_db
    from app.services.candidate_service import CandidateService
    from uuid import UUID

    async for session in get_db():
        svc = CandidateService(session)
        candidate = await svc.get_by_id(UUID(candidate_id), tenant_id)
        if candidate is None:
            return {"error": "Candidate not found", "candidate_id": candidate_id}

        profile = candidate.profile or {}
        return {
            "candidate_id": str(candidate.id),
            "name": candidate.name_encrypted,
            "email": candidate.email,
            "phone": candidate.phone,
            "stage": candidate.stage,
            "status": candidate.status,
            "credibility_score": candidate.credibility_score,
            "credibility_grade": candidate.credibility_grade,
            "profile": profile,
            "inference_data": candidate.inference_data,
            "resume_count": len(candidate.resumes) if candidate.resumes else 0,
            "source_refs": candidate.source_refs,
            "tags": candidate.tags,
            "version": candidate.version,
        }

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Profile Build — 构建候选人画像
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_profile_build",
    name="HR Profile Build",
    endpoint="/api/v1/candidates/{candidate_id}/profile/build",
    method="POST",
    tool_name="hr_profile_build",
    permissions=["candidate:write"],
    llm_model="gpt-4o-mini",
    fallback_model="gpt-3.5-turbo",
    prompt_version="v1",
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_profile_build_v1",
    description="触发候选人画像构建，多源聚合多份简历，输出标准化画像",
    request_model="ProfileBuildRequest",
    response_model="CandidateProfile",
    rate_limit="10/minute",
    data_classification="L3",
    audit_level="detailed",
    tags=["hr", "candidate", "profile", "build"],
    timeout=30.0,
)
async def hr_profile_build(
    candidate_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    触发候选人画像构建。

    关联候选人的多份简历，按「最新 + 最高可信度」优先级聚合，
    输出标准化画像：基本信息、工作经历时间轴、教育背景、技能标签云。

    Args:
        candidate_id: 候选人 UUID。
        tenant_id: 租户标识。

    Returns:
        构建后的完整候选人画像。
    """
    from app.dependencies import get_db
    from app.services.candidate_profile_builder import CandidateProfileBuilder

    async for session in get_db():
        builder = CandidateProfileBuilder(session)
        try:
            profile = await builder.build_profile(candidate_id)
            return {
                "status": "success",
                "candidate_id": profile.candidate_id,
                "merged": {
                    "basic_info": profile.merged.basic_info,
                    "work_timeline": [
                        {
                            "company": e.company,
                            "title": e.title,
                            "start_date": e.start_date,
                            "end_date": e.end_date,
                            "description": e.description,
                        }
                        for e in profile.merged.work_timeline
                    ],
                    "education": [
                        {
                            "school": e.school,
                            "degree": e.degree,
                            "major": e.major,
                        }
                        for e in profile.merged.education
                    ],
                    "skill_cloud": [
                        {
                            "name": t.name,
                            "source_count": t.source_count,
                            "credibility_weight": t.credibility_weight,
                        }
                        for t in profile.merged.skill_cloud
                    ],
                    "certifications": profile.merged.certifications,
                    "projects": profile.merged.projects,
                },
                "overall_credibility": profile.overall_credibility,
                "credibility_grade": profile.credibility_grade,
                "resume_count": profile.resume_count,
                "last_updated": profile.last_updated,
            }
        except ValueError as exc:
            return {"error": str(exc), "candidate_id": candidate_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Inference Trigger — 触发 AI 隐性推理
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_inference_trigger",
    name="HR Inference Trigger",
    endpoint="/api/v1/candidates/{candidate_id}/inference",
    method="POST",
    tool_name="hr_inference",
    permissions=["candidate:read", "ai:use"],
    llm_model="gpt-4o-mini",
    fallback_model="gpt-3.5-turbo",
    prompt_version="v1",
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_inference_trigger_v1",
    description="触发 AI 隐性推理：从工作经历推断隐含技能和职业发展方向",
    request_model="InferenceTriggerRequest",
    response_model="InferenceResult",
    rate_limit="10/minute",
    data_classification="L2",
    audit_level="detailed",
    tags=["hr", "candidate", "inference", "ai"],
    timeout=60.0,
)
async def hr_inference_trigger(
    candidate_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    触发候选人的 AI 隐性推理。

    执行完整推理流程：技能推断（规则+AI）和职业方向推断。
    推理结果自动持久化到 candidate.inference_data。

    Args:
        candidate_id: 候选人 UUID。
        tenant_id: 租户标识。

    Returns:
        推理结果集，包含推断技能和职业方向。
    """
    from app.dependencies import get_db
    from app.services.inference_engine import InferenceEngine

    async for session in get_db():
        engine = InferenceEngine(session)
        try:
            result = await engine.run_full_inference(candidate_id)
            return {
                "status": "success",
                "candidate_id": result.candidate_id,
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
                    "direction": result.career_direction.direction,
                    "confidence": result.career_direction.confidence,
                    "reasoning_chain": result.career_direction.reasoning_chain,
                    "trajectory_type": result.career_direction.trajectory_type,
                    "estimated_next_role": result.career_direction.estimated_next_role,
                    "retention_risk": result.career_direction.retention_risk,
                } if result.career_direction else None,
                "inferred_at": result.inferred_at,
                "model_used": result.model_used,
            }
        except ValueError as exc:
            return {"error": str(exc), "candidate_id": candidate_id}

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Inference Query — 查询推理结果
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_inference_query",
    name="HR Inference Query",
    endpoint="/api/v1/candidates/{candidate_id}/inference",
    method="GET",
    tool_name="hr_inference_query",
    permissions=["candidate:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_inference_query_v1",
    description="查询候选人已有的 AI 推理结果",
    request_model="InferenceQueryRequest",
    response_model="InferenceResult",
    rate_limit="100/minute",
    data_classification="L2",
    audit_level="standard",
    tags=["hr", "candidate", "inference", "query"],
    timeout=10.0,
)
async def hr_inference_query(
    candidate_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    查询候选人已有的 AI 推理结果。

    从 candidate.inference_data JSONB 字段返回。
    如无推理结果，返回空数据并提示触发推理。

    Args:
        candidate_id: 候选人 UUID。
        tenant_id: 租户标识。

    Returns:
        推理结果字典。
    """
    from app.dependencies import get_db
    from app.services.candidate_service import CandidateService
    from uuid import UUID

    async for session in get_db():
        svc = CandidateService(session)
        candidate = await svc.get_by_id(UUID(candidate_id), tenant_id)
        if candidate is None:
            return {"error": "Candidate not found", "candidate_id": candidate_id}

        inference = candidate.inference_data
        if not inference:
            return {
                "status": "no_data",
                "candidate_id": candidate_id,
                "message": "暂无推理结果，请使用 hr_inference_trigger 触发推理",
                "inferred_skills": [],
                "career_direction": None,
            }

        return {
            "status": "success",
            "candidate_id": candidate_id,
            "inferred_skills": inference.get("inferred_skills", []),
            "career_direction": inference.get("career_direction"),
            "inferred_at": inference.get("inferred_at"),
            "model_used": inference.get("model_used"),
        }

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Conflict Detect — 检测数据冲突
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_conflict_detect",
    name="HR Conflict Detect",
    endpoint="/api/v1/candidates/{candidate_id}/conflicts",
    method="GET",
    tool_name="hr_conflict_detect",
    permissions=["candidate:read"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_conflict_detect_v1",
    description="检测候选人多份简历之间的数据冲突",
    request_model="ConflictDetectRequest",
    response_model="ConflictReport",
    rate_limit="30/minute",
    data_classification="L3",
    audit_level="standard",
    tags=["hr", "candidate", "conflict", "detect"],
    timeout=15.0,
)
async def hr_conflict_detect(
    candidate_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """
    检测候选人多份简历之间的数据冲突。

    比较同名字段值，检测值冲突、格式冲突和时间线冲突。
    返回冲突列表，标注哪些可自动解决、哪些需要 HR 裁决。

    Args:
        candidate_id: 候选人 UUID。
        tenant_id: 租户标识。

    Returns:
        冲突检测报告。
    """
    from app.dependencies import get_db
    from app.services.conflict_detector import ConflictDetector

    async for session in get_db():
        detector = ConflictDetector(session)
        report = await detector.detect_and_report(candidate_id)
        return {
            "status": "success",
            "candidate_id": report.candidate_id,
            "conflicts": [
                {
                    "field_path": c.field_path,
                    "conflict_type": c.conflict_type.value if hasattr(c.conflict_type, "value") else str(c.conflict_type),
                    "values": [
                        {"resume_id": v.resume_id, "value": v.value, "credibility_score": v.credibility_score}
                        for v in c.values
                    ],
                    "auto_merge_strategy": c.auto_merge_strategy.value if hasattr(c.auto_merge_strategy, "value") else str(c.auto_merge_strategy),
                    "auto_merged_value": c.auto_merged_value,
                    "needs_manual_review": c.needs_manual_review,
                    "reason": c.reason,
                }
                for c in report.conflicts
            ],
            "auto_resolved_count": report.auto_resolved_count,
            "manual_review_count": report.manual_review_count,
            "total_resumes_compared": report.total_resumes_compared,
        }

    return {"error": "Database session unavailable"}


# ---------------------------------------------------------------------------
# Tool: HR Conflict Resolve — HR 裁决冲突
# ---------------------------------------------------------------------------

@AiCapability(
    capability="hr_conflict_resolve",
    name="HR Conflict Resolve",
    endpoint="/api/v1/candidates/{candidate_id}/conflicts/resolve",
    method="POST",
    tool_name="hr_conflict_resolve",
    permissions=["candidate:write"],
    allowed_callers=["api", "agent"],
    requires_tenant_isolation=True,
    ai_capability_id="hr_conflict_resolve_v1",
    description="HR 手动裁决候选人数据冲突",
    request_model="ConflictResolveRequest",
    response_model="ConflictResolveResult",
    rate_limit="30/minute",
    data_classification="L3",
    audit_level="detailed",
    tags=["hr", "candidate", "conflict", "resolve"],
    timeout=10.0,
)
async def hr_conflict_resolve(
    candidate_id: str,
    tenant_id: str,
    *,
    field_path: str,
    chosen_value: Any,
    resolved_by: str,
) -> dict[str, Any]:
    """
    HR 手动裁决数据冲突。

    选择一个值写入候选人画像，覆盖冲突字段的自动合并结果。

    Args:
        candidate_id: 候选人 UUID。
        tenant_id: 租户标识。
        field_path: 冲突字段路径 (如 "basic_info.name")。
        chosen_value: HR 选择的值。
        resolved_by: 裁决人 ID。

    Returns:
        裁决确认结果。
    """
    from app.dependencies import get_db
    from app.services.conflict_detector import ConflictDetector

    async for session in get_db():
        detector = ConflictDetector(session)
        try:
            result = await detector.resolve_conflict(
                candidate_id=candidate_id,
                field_path=field_path,
                chosen_value=chosen_value,
                resolved_by=resolved_by,
            )
            return {"status": "success", **result}
        except ValueError as exc:
            return {"error": str(exc), "candidate_id": candidate_id}

    return {"error": "Database session unavailable"}
