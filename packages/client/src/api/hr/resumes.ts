import { hrGet, hrPost, hrDelete } from './client'
import type { PaginatedResponse } from './client'

// ─── Types ──────────────────────────────────────────────

export interface Resume {
  id: string
  candidate_id: string | null
  filename: string
  file_path: string
  file_size: number
  file_type: string
  file_hash: string | null
  parse_status: 'pending' | 'processing' | 'completed' | 'failed'
  parsed_data: Record<string, unknown> | null
  source: 'upload' | 'email' | 'referral' | 'linkedin'
  tags: string[]
  uploaded_by: string | null
  created_at: string
  updated_at: string
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
  return hrPost<Resume>(`/resumes/${id}/parse`)
}

export async function uploadResume(file: File, candidateId?: string, source?: string): Promise<Resume> {
  const HR_API_BASE = 'http://127.0.0.1:8000/api/v1'

  const formData = new FormData()
  formData.append('file', file)
  if (candidateId) formData.append('candidate_id', candidateId)
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

// TODO: backend not yet implemented
export async function linkResumeToCandidate(resumeId: string, candidateId: string): Promise<{ ok: boolean }> {
  return hrPost<{ ok: boolean }>(`/resumes/${resumeId}/link`, { candidate_id: candidateId })
}

// TODO: backend not yet implemented
export async function addResumeTags(id: string, tags: string[]): Promise<{ ok: boolean }> {
  return hrPost<{ ok: boolean }>(`/resumes/${id}/tags`, { tags })
}
