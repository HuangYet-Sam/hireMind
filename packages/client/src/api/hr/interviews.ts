import { hrGet, hrPost, hrPatch, hrDelete } from './client'
import type { PaginatedResponse } from './client'

export interface Interview {
  id: string
  candidate_id: string
  position_id: string | null
  round_number: number
  interview_type: string
  status: string
  scheduled_at: string | null
  duration_minutes: number
  location: string | null
  interviewer_ids: string[] | null
  overall_score: number | null
  recommendation: string | null
  summary: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface CreateInterviewRequest {
  candidate_id: string
  position_id?: string | null
  round_number?: number
  interview_type?: string
  scheduled_at?: string | null
  duration_minutes?: number
  location?: string | null
  interviewer_ids?: string[] | null
}

export interface UpdateInterviewRequest {
  scheduled_at?: string | null
  duration_minutes?: number
  location?: string | null
  interviewer_ids?: string[] | null
  status?: string
  round_number?: number
  interview_type?: string
}

export interface SubmitFeedbackRequest {
  score: number
  recommendation: string
  strengths?: string | null
  weaknesses?: string | null
  comments?: string | null
  skill_ratings?: Record<string, number> | null
}

export interface InterviewListParams {
  page?: number
  page_size?: number
  candidate_id?: string
  position_id?: string
  interviewer_id?: string
  status?: string
  date_from?: string
  date_to?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface InterviewCalendarParams {
  date_from: string
  date_to: string
  interviewer_id?: string
}

export interface InterviewStats {
  total: number
  by_status: Record<string, number>
  by_type: Record<string, number>
  avg_score: number | null
  interviewer_workload: InterviewerWorkloadItem[]
}

export interface InterviewerWorkloadItem {
  interviewer_id: string
  total_interviews: number
  pending_feedback: number
  avg_score: number | null
}

export type CalendarViewMode = 'month' | 'week' | 'day'
export type BoardStatusColumn = 'pending' | 'scheduled' | 'in_progress' | 'pending_feedback' | 'completed'

export const INTERVIEW_STATUS_LABELS: Record<string, string> = {
  scheduled: '已安排',
  confirmed: '已确认',
  in_progress: '进行中',
  completed: '已完成',
  cancelled: '已取消',
  no_show: '未到',
  pending: '待确认',
  pending_feedback: '待反馈',
}

export const INTERVIEW_TYPE_LABELS: Record<string, string> = {
  phone_screen: '电话筛选',
  technical: '技术面试',
  behavioral: '行为面试',
  hr: 'HR面试',
  final: '终面',
  panel: '小组面试',
  case_study: '案例面试',
}

export async function listInterviews(params?: InterviewListParams): Promise<PaginatedResponse<Interview>> {
  return hrGet<PaginatedResponse<Interview>>('/interviews', params as Record<string, string | number>)
}

export async function getInterview(id: string): Promise<Interview> {
  return hrGet<Interview>(`/interviews/${id}`)
}

export async function createInterview(data: CreateInterviewRequest): Promise<Interview> {
  return hrPost<Interview>('/interviews', data)
}

export async function updateInterview(id: string, data: UpdateInterviewRequest): Promise<Interview> {
  return hrPatch<Interview>(`/interviews/${id}`, data)
}

export async function cancelInterview(id: string, reason?: string): Promise<void> {
  const params = reason ? `?reason=${encodeURIComponent(reason)}` : ''
  return hrDelete(`/interviews/${id}${params}`)
}

export async function submitFeedback(id: string, feedback: SubmitFeedbackRequest): Promise<Interview> {
  return hrPost<Interview>(`/interviews/${id}/feedback`, feedback)
}

export async function getInterviewCalendar(params: InterviewCalendarParams): Promise<Interview[]> {
  return hrGet<Interview[]>('/interviews/calendar', params as Record<string, string>)
}

export async function batchUpdateInterviewStatus(
  ids: string[],
  status: string,
): Promise<Interview[]> {
  return hrPatch<Interview[]>('/interviews/batch/status', { ids, status })
}

export async function getInterviewStats(params?: {
  interviewer_id?: string
  date_from?: string
  date_to?: string
}): Promise<InterviewStats> {
  return hrGet<InterviewStats>('/interviews/stats', params as Record<string, string>)
}

export async function generateAiQuestions(payload: {
  position: Record<string, unknown>
  candidate: Record<string, unknown>
  interview_type?: string
  num_questions?: number
}): Promise<unknown> {
  return hrPost('/interviews/ai/questions', payload)
}

// ─── Calendar ────────────────────────────────────────────────────

export interface InterviewCalendarEvent {
  id: string
  title: string
  candidate_id: string
  candidate_name: string
  position_id: string | null
  position_title: string | null
  interview_type: string
  status: string
  scheduled_at: string
  duration_minutes: number
  interviewer_ids: string[]
  interviewer_names: string[]
  overall_score: number | null
}

export async function fetchInterviewCalendar(
  dateFrom: string,
  dateTo: string,
): Promise<InterviewCalendarEvent[]> {
  return hrGet<InterviewCalendarEvent[]>('/interviews/calendar', {
    date_from: dateFrom,
    date_to: dateTo,
  })
}

// ─── Workload Stats ──────────────────────────────────────────────

export interface WorkloadStats {
  interviewer_id: string
  interviewer_name: string
  total_interviews: number
  pending_feedback: number
  completed_interviews: number
  avg_score: number | null
  weekly_hours: number
  available_slots: number
}

export async function fetchWorkloadStats(): Promise<WorkloadStats[]> {
  return hrGet<WorkloadStats[]>('/interviews/workload')
}

// ─── Batch Create ────────────────────────────────────────────────

export interface BatchCreateInterviewItem {
  candidate_id: string
  position_id?: string | null
  round_number?: number
  interview_type?: string
  scheduled_at?: string | null
  duration_minutes?: number
  location?: string | null
  interviewer_ids?: string[] | null
}

export async function batchCreateInterviews(
  data: BatchCreateInterviewItem[],
): Promise<Interview[]> {
  return hrPost<Interview[]>('/interviews/batch', { interviews: data })
}

// ─── AI Briefing ─────────────────────────────────────────────────

export interface InterviewBriefingResponse {
  id: string
  interview_id: string
  position_requirements: string[]
  candidate_strengths: string[]
  candidate_gaps: string[]
  verification_points: string[]
  focus_areas: string[]
  suggested_questions: string[]
  generated_at: string
}

export async function generateBriefing(
  interviewId: string,
): Promise<InterviewBriefingResponse> {
  return hrPost<InterviewBriefingResponse>(
    `/interviews/${interviewId}/briefing`,
  )
}

// ─── AI Questions (per-interview) ────────────────────────────────

export interface InterviewQuestionsResponse {
  id: string
  interview_id: string
  questions: string[]
  generated_at: string
}

export async function generateQuestions(
  interviewId: string,
): Promise<InterviewQuestionsResponse> {
  return hrPost<InterviewQuestionsResponse>(
    `/interviews/${interviewId}/questions`,
  )
}

// ─── Recommend Slots ────────────────────────────────────────────

export interface RecommendedSlot {
  start_at: string
  end_at: string
  interviewer_ids: string[]
  score: number
  reason: string
}

export async function recommendSlots(
  interviewId: string,
): Promise<RecommendedSlot[]> {
  return hrPost<RecommendedSlot[]>(
    `/interviews/${interviewId}/recommend-slots`,
  )
}

// ─── Analyze Feedback ────────────────────────────────────────────

export interface FeedbackAnalysisResponse {
  summary: string
  sentiment: string
  key_points: string[]
  recommendation: string
}

export async function analyzeFeedback(
  interviewId: string,
): Promise<FeedbackAnalysisResponse> {
  return hrPost<FeedbackAnalysisResponse>(
    `/interviews/${interviewId}/analyze-feedback`,
  )
}

// ─── Advance Round ───────────────────────────────────────────────

export async function advanceRound(
  interviewId: string,
): Promise<Interview> {
  return hrPost<Interview>(
    `/interviews/${interviewId}/advance-round`,
  )
}
