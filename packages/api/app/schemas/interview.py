"""
Interview Pydantic Schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class InterviewCreate(BaseModel):
    """Schema for scheduling a new interview."""

    candidate_id: UUID = Field(...)
    position_id: UUID | None = None
    round_number: int = Field(1, ge=1)
    interview_type: str = Field("technical", description="technical / behavioral / hr / final / phone_screen")
    scheduled_at: datetime | None = Field(None, description="Scheduled start time")
    duration_minutes: int = Field(60, ge=15, le=480)
    location: str | None = Field(None, description="Physical location or meeting link")
    interviewer_ids: list[str] | None = Field(None, description="List of interviewer user IDs")


class InterviewUpdate(BaseModel):
    """Schema for updating interview details."""

    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    location: str | None = None
    interviewer_ids: list[str] | None = None
    status: str | None = None
    round_number: int | None = None
    interview_type: str | None = None


class InterviewFeedbackCreate(BaseModel):
    """Schema for submitting interview feedback."""

    score: float = Field(..., ge=0, le=10, description="Score (0-10)")
    recommendation: str = Field(..., description="strong_yes / yes / no / strong_no")
    strengths: str | None = None
    weaknesses: str | None = None
    comments: str | None = None
    skill_ratings: dict | None = None


class InterviewResponse(BaseModel):
    """Interview response schema."""

    id: UUID
    candidate_id: UUID
    position_id: UUID | None
    round_number: int
    interview_type: str
    status: str
    scheduled_at: datetime | None
    duration_minutes: int
    location: str | None
    interviewer_ids: list | None
    overall_score: float | None
    recommendation: str | None
    summary: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InterviewListResponse(BaseModel):
    """Paginated interview list."""

    items: list[InterviewResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ---------------------------------------------------------------------------
# M5 Extended Schemas — AI briefing, questions, analysis, calendar, workload
# ---------------------------------------------------------------------------


class InterviewRoundConfig(BaseModel):
    """面试轮次配置"""

    round_number: int
    interview_type: str  # technical/behavioral/hr/final
    interviewer_role: str  # 建议面试官角色
    duration_minutes: int = 60
    required: bool = True


class InterviewBriefingResponse(BaseModel):
    """AI考察清单"""

    interview_id: UUID
    position_requirements: list[str]  # 岗位关键要求
    candidate_strengths: list[str]  # 候选人优势
    candidate_gaps: list[str]  # 差距点
    verification_points: list[str]  # 需面试验证项
    focus_areas: list[str]  # 重点考察方向
    suggested_questions: list[str]  # 建议问题


class InterviewQuestionGroup(BaseModel):
    """按能力维度分组的面试题"""

    dimension: str  # 能力维度名称
    difficulty: str  # easy/medium/hard
    questions: list[dict]  # [{question, follow_ups, evaluation_criteria}]


class InterviewQuestionsResponse(BaseModel):
    """AI面试题生成结果"""

    interview_id: UUID
    question_groups: list[InterviewQuestionGroup]
    total_questions: int


class TimeSlotRecommendation(BaseModel):
    """推荐时间段"""

    start: datetime
    end: datetime
    score: float  # 推荐分数
    reason: str  # 推荐理由
    conflicts: list[str]  # 冲突信息


class InterviewAnalysisResponse(BaseModel):
    """AI面试反馈分析"""

    interview_id: UUID
    overall_score: float
    score_breakdown: dict  # {dimension: score}
    strengths: list[str]
    concerns: list[str]
    recommendation: str  # strong_yes/yes/no/strong_no
    recommendation_reason: str
    improvement_suggestions: list[str]
    candidate_fit_score: float  # 岗位匹配度


class InterviewerWorkload(BaseModel):
    """面试官工作量"""

    interviewer_id: str
    interviewer_name: str
    total_interviews: int
    pending_feedback: int
    completed_feedback: int
    average_score: float | None
    upcoming_interviews: int


class InterviewCalendarEvent(BaseModel):
    """日历事件"""

    id: UUID
    title: str
    start: datetime
    end: datetime
    status: str
    candidate_name: str
    position_title: str | None
    interview_type: str
    interviewer_ids: list[str]


class InterviewCalendarResponse(BaseModel):
    """日历视图响应"""

    events: list[InterviewCalendarEvent]
    date_from: datetime
    date_to: datetime
