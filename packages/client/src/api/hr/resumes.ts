import { hrGet, hrPost, hrDelete } from './client'
import type { PaginatedResponse } from './client'

// ─── Types ──────────────────────────────────────────────

export interface Resume {
  id: string
  candidate_id: string | null
  candidate_name?: string
  filename: string
  file_url: string
  file_size: number
  mime_type: string
  parse_status: 'pending' | 'processing' | 'completed' | 'failed'
  parsed_content: string | null
  parsed_skills: string[]
  parsed_education: ParsedEducation[]
  parsed_experience: ParsedExperience[]
  ai_summary: string | null
  ai_tags: string[]
  source: 'upload' | 'email' | 'referral' | 'linkedin'
  tags: string[]
  created_at: string
  updated_at: string
}

export interface ParsedEducation {
  school: string
  degree: string
  major: string
  start_date: string | null
  end_date: string | null
}

export interface ParsedExperience {
  company: string
  title: string
  start_date: string | null
  end_date: string | null
  description: string
}

export interface UploadResumeRequest {
  source?: Resume['source']
  candidate_id?: string
  tags?: string[]
}

export interface ResumeListParams {
  page?: number
  page_size?: number
  keyword?: string
  tags?: string[]
  parse_status?: Resume['parse_status']
  candidate_id?: string
}

// ─── API Functions ──────────────────────────────────────

export async function listResumes(params?: ResumeListParams): Promise<PaginatedResponse<Resume>> {
  return hrGet<PaginatedResponse<Resume>>('/resumes', params as Record<string, string | number>)
}

export async function getResume(id: string): Promise<Resume> {
  return hrGet<Resume>(`/resumes/${id}`)
}

export async function deleteResume(id: string): Promise<{ ok: boolean }> {
  return hrDelete('/resumes/' + id)
}

export async function reparseResume(id: string): Promise<Resume> {
  return hrPost<Resume>(`/resumes/${id}/reparse`)
}

export async function linkResumeToCandidate(resumeId: string, candidateId: string): Promise<{ ok: boolean }> {
  return hrPost<{ ok: boolean }>(`/resumes/${resumeId}/link`, { candidate_id: candidateId })
}

export async function addResumeTags(id: string, tags: string[]): Promise<{ ok: boolean }> {
  return hrPost<{ ok: boolean }>(`/resumes/${id}/tags`, { tags })
}
