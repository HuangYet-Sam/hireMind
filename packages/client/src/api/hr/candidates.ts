import { hrGet, hrPost, hrPatch, hrDelete } from './client'
import type { PaginatedResponse } from './client'

export interface Candidate {
  id: string
  name: string
  email: string | null
  phone: string | null
  position_id: string | null
  stage: string
  status: string
  source: string | null
  current_company: string | null
  current_title: string | null
  years_of_experience: number | null
  education: string | null
  location: string | null
  expected_salary: number | null
  skills: Record<string, unknown> | null
  summary: string | null
  applied_at: string | null
  assigned_recruiter: string | null
  tags: string[] | null
  created_at: string
  updated_at: string
}

export interface CreateCandidateRequest {
  name: string
  email: string
  phone?: string | null
  position_id?: string | null
  source?: string | null
  source_detail?: string | null
  current_company?: string | null
  current_title?: string | null
  years_of_experience?: number | null
  education?: string | null
  location?: string | null
  expected_salary?: number | null
  tags?: string[] | null
}

export interface UpdateCandidateRequest {
  name?: string | null
  email?: string | null
  phone?: string | null
  position_id?: string | null
  stage?: string | null
  status?: string | null
  source?: string | null
  current_company?: string | null
  current_title?: string | null
  years_of_experience?: number | null
  education?: string | null
  location?: string | null
  expected_salary?: number | null
  assigned_recruiter?: string | null
  tags?: string[] | null
}

export interface CandidateListParams {
  page?: number
  page_size?: number
  position_id?: string
  status?: string
  stage?: string
  keyword?: string
}

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

export async function deleteCandidate(id: string): Promise<void> {
  return hrDelete(`/candidates/${id}`)
}

export async function advanceStage(id: string, stage: string): Promise<Candidate> {
  return hrPost<Candidate>(`/candidates/${id}/stage`, { stage })
}
