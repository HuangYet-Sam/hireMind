import { hrGet, hrPost, hrPatch, hrDelete } from './client'
import type { PaginatedResponse } from './client'

// ─── Types ──────────────────────────────────────────────

export interface Candidate {
  id: string
  name: string
  email: string
  phone: string | null
  position_id: string | null
  stage: 'applied' | 'screened' | 'interviewed' | 'offered' | 'hired' | 'rejected'
  status: 'active' | 'inactive'
  source: 'resume_upload' | 'referral' | 'linkedin' | 'website' | 'headhunting' | 'other'
  current_company: string | null
  current_title: string | null
  years_of_experience: number | null
  education: string | null
  location: string | null
  expected_salary: number | null
  skills: string[]
  summary: string | null
  applied_at: string | null
  assigned_recruiter: string | null
  tags: string[]
  created_at: string
  updated_at: string
}

export interface CreateCandidateRequest {
  name: string
  email: string
  phone?: string
  source?: Candidate['source']
  position_id?: string
  location?: string
  source_detail?: string
  tags?: string[]
  current_company?: string
  current_title?: string
  years_of_experience?: number
  education?: string
  expected_salary?: number
}

export interface UpdateCandidateRequest {
  name?: string
  email?: string
  phone?: string | null
  source?: Candidate['source']
  status?: Candidate['status']
  stage?: Candidate['stage']
  position_id?: string | null
  tags?: string[]
  current_company?: string | null
  current_title?: string | null
  years_of_experience?: number | null
  education?: string | null
  location?: string | null
  expected_salary?: number | null
}

export interface CandidateListParams {
  page?: number
  page_size?: number
  status?: Candidate['status']
  stage?: Candidate['stage']
  position_id?: string
  source?: Candidate['source']
  keyword?: string
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

export async function advanceStage(id: string, stage: string): Promise<Candidate> {
  return hrPost<Candidate>(`/candidates/${id}/stage`, { stage })
}

// TODO: backend not yet implemented
// export async function getCandidateTimeline(id: string): Promise<CandidateTimelineEvent[]> {
//   return hrGet<CandidateTimelineEvent[]>(`/candidates/${id}/timeline`)
// }
//
// export async function addCandidateNote(id: string, note: string): Promise<{ ok: boolean }> {
//   return hrPost<{ ok: boolean }>(`/candidates/${id}/notes`, { note })
// }
