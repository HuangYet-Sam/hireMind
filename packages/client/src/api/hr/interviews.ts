import { hrGet, hrPost, hrPatch, hrDelete } from './client'
import type { PaginatedResponse } from './client'

// ─── Types ──────────────────────────────────────────────

export interface Interview {
  id: string
  candidate_id: string
  candidate_name?: string
  position_id: string
  position_title?: string
  round: number
  type: 'phone_screen' | 'technical' | 'behavioral' | 'case_study' | 'panel' | 'final'
  status: 'scheduled' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'no_show'
  scheduled_at: string
  duration_minutes: number
  location: string
  meeting_url: string | null
  interviewers: Interviewer[]
  feedback: InterviewFeedback | null
  score: number | null
  ai_summary: string | null
  notes: string
  created_at: string
  updated_at: string
}

export interface Interviewer {
  user_id: string
  name: string
  role: 'lead' | 'panelist' | 'observer'
}

export interface InterviewFeedback {
  interviewer_id: string
  interviewer_name: string
  rating: number
  strengths: string[]
  concerns: string[]
  recommendation: 'strong_yes' | 'yes' | 'neutral' | 'no' | 'strong_no'
  comment: string
  submitted_at: string
}

export interface CreateInterviewRequest {
  candidate_id: string
  position_id: string
  round?: number
  type: Interview['type']
  scheduled_at: string
  duration_minutes?: number
  location?: string
  meeting_url?: string
  interviewer_ids: string[]
  notes?: string
}

export interface UpdateInterviewRequest {
  scheduled_at?: string
  duration_minutes?: number
  location?: string
  meeting_url?: string | null
  status?: Interview['status']
  interviewer_ids?: string[]
  notes?: string
}

export interface InterviewListParams {
  page?: number
  page_size?: number
  status?: Interview['status']
  candidate_id?: string
  position_id?: string
  type?: Interview['type']
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

export async function cancelInterview(id: string): Promise<Interview> {
  return hrPost<Interview>(`/interviews/${id}/cancel`)
}

export async function submitFeedback(id: string, feedback: Omit<InterviewFeedback, 'submitted_at'>): Promise<{ ok: boolean }> {
  return hrPost<{ ok: boolean }>(`/interviews/${id}/feedback`, feedback)
}

export async function getInterviewCalendar(startDate: string, endDate: string): Promise<Interview[]> {
  return hrGet<Interview[]>('/interviews/calendar', { date_from: startDate, date_to: endDate })
}
