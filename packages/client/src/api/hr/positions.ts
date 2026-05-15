import { hrGet, hrPost, hrPatch, hrDelete } from './client'
import type { PaginatedResponse } from './client'

// ─── Types ──────────────────────────────────────────────

export interface Position {
  id: string
  title: string
  department_id: string
  location: string
  employment_type: 'full_time' | 'part_time' | 'contract' | 'intern'
  status: 'draft' | 'open' | 'paused' | 'closed' | 'filled'
  salary_min: number | null
  salary_max: number | null
  headcount: number
  priority: 'low' | 'medium' | 'high' | 'urgent'
  description: string
  requirements: string[]
  benefits: string[]
  required_skills: string[]
  preferred_skills: string[]
  education_requirement: string | null
  experience_years_min: number | null
  is_remote: boolean
  created_by: string
  created_at: string
  updated_at: string
}

export interface CreatePositionRequest {
  title: string
  department_id: string
  location?: string
  employment_type?: Position['employment_type']
  salary_min?: number
  salary_max?: number
  headcount?: number
  description?: string
  requirements?: string[]
  benefits?: string[]
  required_skills?: string[]
  preferred_skills?: string[]
  education_requirement?: string
  experience_years_min?: number
  is_remote?: boolean
  priority?: Position['priority']
}

export interface UpdatePositionRequest {
  title?: string
  department_id?: string
  location?: string
  employment_type?: Position['employment_type']
  status?: Position['status']
  salary_min?: number | null
  salary_max?: number | null
  headcount?: number
  description?: string
  requirements?: string[]
  benefits?: string[]
  required_skills?: string[]
  preferred_skills?: string[]
  education_requirement?: string | null
  experience_years_min?: number | null
  is_remote?: boolean
  priority?: Position['priority']
}

export interface PositionListParams {
  page?: number
  page_size?: number
  status?: Position['status']
  department_id?: string
  keyword?: string
  priority?: Position['priority']
}

// ─── API Functions ──────────────────────────────────────

export async function listPositions(params?: PositionListParams): Promise<PaginatedResponse<Position>> {
  return hrGet<PaginatedResponse<Position>>('/positions', params as Record<string, string | number>)
}

export async function getPosition(id: string): Promise<Position> {
  return hrGet<Position>(`/positions/${id}`)
}

export async function createPosition(data: CreatePositionRequest): Promise<Position> {
  return hrPost<Position>('/positions', data)
}

export async function updatePosition(id: string, data: UpdatePositionRequest): Promise<Position> {
  return hrPatch<Position>(`/positions/${id}`, data)
}

export async function deletePosition(id: string): Promise<{ ok: boolean }> {
  return hrDelete('/positions/' + id)
}

export async function closePosition(id: string): Promise<Position> {
  return hrPatch<Position>(`/positions/${id}`, { status: 'closed' })
}

export async function reopenPosition(id: string): Promise<Position> {
  return hrPatch<Position>(`/positions/${id}`, { status: 'open' })
}
