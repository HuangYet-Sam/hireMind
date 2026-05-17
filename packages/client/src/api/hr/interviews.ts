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
  date_from?: string
  date_to?: string
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

export async function getInterviewCalendar(startDate: string, endDate: string): Promise<Interview[]> {
  return hrGet<Interview[]>('/interviews/calendar', { date_from: startDate, date_to: endDate })
}

export async function generateAiQuestions(payload: {
  position: Record<string, unknown>
  candidate: Record<string, unknown>
  interview_type?: string
  num_questions?: number
}): Promise<unknown> {
  return hrPost('/interviews/ai/questions', payload)
}
