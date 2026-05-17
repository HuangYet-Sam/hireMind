import { hrGet, hrPost, hrDelete } from './client'
import type { PaginatedResponse } from './client'

export interface Resume {
  id: string
  candidate_id: string | null
  original_filename: string
  file_size: number
  content_type: string
  parse_status: string
  parsed_data: Record<string, unknown> | null
  language: string | null
  page_count: number | null
  uploaded_by: string | null
  created_at: string
  updated_at: string
}

export interface ResumeParseResult {
  resume_id: string
  parse_status: string
  parsed_data: Record<string, unknown> | null
  skills: string[] | null
  education: Record<string, unknown>[] | null
  work_experience: Record<string, unknown>[] | null
  error: string | null
}

export interface ResumeListParams {
  page?: number
  page_size?: number
  candidate_id?: string
  status?: string
}

export async function listResumes(params?: ResumeListParams): Promise<PaginatedResponse<Resume>> {
  return hrGet<PaginatedResponse<Resume>>('/resumes', params as Record<string, string | number>)
}

export async function getResume(id: string): Promise<Resume> {
  return hrGet<Resume>(`/resumes/${id}`)
}

export async function deleteResume(id: string): Promise<void> {
  return hrDelete(`/resumes/${id}`)
}

export async function reparseResume(id: string): Promise<ResumeParseResult> {
  return hrPost<ResumeParseResult>(`/resumes/${id}/parse`)
}

export async function uploadResume(file: File, candidateId?: string, positionId?: string, source?: string): Promise<Resume> {
  const HR_API_BASE = 'http://127.0.0.1:8000/api/v1'

  const formData = new FormData()
  formData.append('file', file)
  if (candidateId) formData.append('candidate_id', candidateId)
  if (positionId) formData.append('position_id', positionId)
  if (source) formData.append('source', source)

  const token = localStorage.getItem('hermes_api_key') || ''
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const tenantId = localStorage.getItem('hr_tenant_id')
  if (tenantId) headers['X-Tenant-Id'] = tenantId

  const res = await fetch(`${HR_API_BASE}/resumes/upload`, {
    method: 'POST',
    headers,
    body: formData,
  })
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  return res.json()
}

export async function linkResumeToCandidate(resumeId: string, candidateId: string): Promise<{ ok: boolean }> {
  return hrPost<{ ok: boolean }>(`/resumes/${resumeId}/link`, { candidate_id: candidateId })
}

export async function addResumeTags(id: string, tags: string[]): Promise<{ ok: boolean }> {
  return hrPost<{ ok: boolean }>(`/resumes/${id}/tags`, { tags })
}
