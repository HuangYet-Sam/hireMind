import { hrGet, hrPost, hrPatch, hrDelete } from './client'
import type { PaginatedResponse } from './client'

// ─── Types ──────────────────────────────────────────────

export interface Department {
  id: string
  name: string
  parent_id: string | null
  parent_name?: string
  description: string
  head_name: string | null
  head_count: number
  open_positions: number
  children: Department[]
  created_at: string
  updated_at: string
}

export interface CreateDepartmentRequest {
  name: string
  parent_id?: string
  description?: string
  head_name?: string
}

export interface UpdateDepartmentRequest {
  name?: string
  parent_id?: string | null
  description?: string
  head_name?: string | null
}

// ─── API Functions ──────────────────────────────────────

export async function listDepartments(): Promise<Department[]> {
  return hrGet<Department[]>('/departments')
}

export async function getDepartmentTree(): Promise<Department[]> {
  return hrGet<Department[]>('/departments/tree')
}

export async function getDepartment(id: string): Promise<Department> {
  return hrGet<Department>(`/departments/${id}`)
}

export async function createDepartment(data: CreateDepartmentRequest): Promise<Department> {
  return hrPost<Department>('/departments', data)
}

export async function updateDepartment(id: string, data: UpdateDepartmentRequest): Promise<Department> {
  return hrPatch<Department>(`/departments/${id}`, data)
}

export async function deleteDepartment(id: string): Promise<{ ok: boolean }> {
  return hrDelete('/departments/' + id)
}
