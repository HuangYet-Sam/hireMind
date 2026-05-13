import { hrGet, hrPost, hrPatch, hrDelete } from './client'
import type { PaginatedResponse } from './client'

// ─── Types ──────────────────────────────────────────────

export interface Candidate {
  id: string
  name: string
  email: string
  phone: string | null
  source: 'resume_upload' | 'referral' | 'linkedin' | 'website' | 'headhunting' | 'other'
  status: 'new' | 'screening' | 'interviewing' | 'offered' | 'hired' | 'rejected' | 'withdrawn'
  position_id: string | null
  position_title?: string
  resume_id: string | null
  avatar_url: string | null
  tags: string[]
  match_score: number | null
  current_company: string | null
  current_title: string | null
  years_of_experience: number | null
  education: string | null
  expected_salary: number | null
  notes: string
  ai_summary: string | null
  ai_tags: string[]
  created_at: string
  updated_at: string
}

export interface CreateCandidateRequest {
  name: string
  email: string
  phone?: string
  source?: Candidate['source']
  position_id?: string
  resume_id?: string
  tags?: string[]
  current_company?: string
  current_title?: string
  years_of_experience?: number
  education?: string
  expected_salary?: number
  notes?: string
}

export interface UpdateCandidateRequest {
  name?: string
  email?: string
  phone?: string | null
  source?: Candidate['source']
  status?: Candidate['status']
  position_id?: string | null
  tags?: string[]
  current_company?: string | null
  current_title?: string | null
  years_of_experience?: number | null
  education?: string | null
  expected_salary?: number | null
  notes?: string
}

export interface CandidateListParams {
  page?: number
  page_size?: number
  status?: Candidate['status']
  position_id?: string
  source?: Candidate['source']
  keyword?: string
  tags?: string[]
  min_match_score?: number
}

// ─── API Functions ──────────────────────────────────────

export async function listCandidates(params?: CandidateListParams): Promise<PaginatedResponse<Candidate>> {
  return hrGet<PaginatedResponse<Candidate>>('/candidates', params as Record<string, string | number>)
}

export async function getCandidate(id: string): Promise<Candidate> {
  return hrGet<Candidate>(`/candidates/${id}`)
}

export async function createCandidate(data: CreateCandidateRequest): Promise<Candidate> {
  return hrPost<Candidate>('/candidates', data)
}

export async function updateCandidate(id: string, data: UpdateCandidateRequest): Promise<Candidate> {
  return hrPatch<Candidate>(`/candidates/${id}`, data)
}

export async function deleteCandidate(id: string): Promise<{ ok: boolean }> {
  return hrDelete('/candidates/' + id)
}

export async function getCandidateTimeline(id: string): Promise<CandidateTimelineEvent[]> {
  return hrGet<CandidateTimelineEvent[]>(`/candidates/${id}/timeline`)
}

export async function addCandidateNote(id: string, note: string): Promise<{ ok: boolean }> {
  return hrPost<{ ok: boolean }>(`/candidates/${id}/notes`, { note })
}

export interface CandidateTimelineEvent {
  id: string
  candidate_id: string
  event_type: 'status_change' | 'note' | 'interview' | 'offer' | 'resume_upload' | 'ai_analysis'
  title: string
  description: string
  performed_by: string
  created_at: string
}
