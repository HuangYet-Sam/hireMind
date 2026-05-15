import { hrGet, hrPost, hrPatch, hrDelete } from './client'
import type { PaginatedResponse } from './client'

// ─── Types ──────────────────────────────────────────────

export interface Interview {
  id: string
  candidate_id: string
  position_id: string
  round_number: number
  interview_type: 'phone_screen' | 'technical' | 'behavioral' | 'case_study' | 'panel' | 'final'
  status: 'scheduled' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'no_show'
  scheduled_at: string
  duration_minutes: number
  location: string
  interviewer_ids: string[]
  overall_score: number | null
  recommendation: string | null
  summary: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface CreateInterviewRequest {
  candidate_id: string
  position_id: string
  round_number?: number
  interview_type: Interview['interview_type']
  scheduled_at: string
  duration_minutes?: number
  location?: string
  interviewer_ids: string[]
}

export interface UpdateInterviewRequest {
  scheduled_at?: string
  duration_minutes?: number
  location?: string
  status?: Interview['status']
  interviewer_ids?: string[]
}

export interface SubmitFeedbackRequest {
  score: number
  recommendation: string
  strengths?: string
  weaknesses?: string
  comments?: string
  skill_ratings?: Record<string, number>
}

export interface InterviewListParams {
  page?: number
  page_size?: number
  status?: Interview['status']
  candidate_id?: string
  position_id?: string
  interview_type?: Interview['interview_type']
  date_from?: string
  date_to?: string
}

// ─── API Functions ──────────────────────────────────────

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

// TODO: backend not yet implemented
export async function getInterviewCalendar(startDate: string, endDate: string): Promise<Interview[]> {
  return hrGet<Interview[]>('/interviews/calendar', { date_from: startDate, date_to: endDate })
}
