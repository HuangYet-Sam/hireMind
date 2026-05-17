import { hrGet, hrPost, hrPatch, hrDelete } from './client'
import type { PaginatedResponse } from './client'

export interface Department {
  id: string
  name: string
  code: string | null
  parent_id: string | null
  description: string | null
  head_user_id: string | null
  headcount_limit: number | null
  current_headcount: number
  status: string
  sort_order: number
  tree_path: string | null
  manager_name: string | null
  created_at: string
  updated_at: string
  children: DepartmentTreeNode[]
}

export interface DepartmentTreeNode {
  id: string
  name: string
  code: string | null
  parent_id: string | null
  description: string | null
  head_user_id: string | null
  headcount_limit: number | null
  current_headcount: number
  status: string
  sort_order: number
  tree_path: string | null
  manager_name: string | null
  created_at: string
  updated_at: string
  children: DepartmentTreeNode[]
}

export interface DepartmentTreeResponse {
  tree: DepartmentTreeNode[]
}

export interface CreateDepartmentRequest {
  name: string
  code?: string | null
  parent_id?: string | null
  description?: string | null
  head_user_id?: string | null
  headcount_limit?: number | null
  sort_order?: number
}

export interface UpdateDepartmentRequest {
  name?: string
  code?: string | null
  parent_id?: string | null
  description?: string | null
  head_user_id?: string | null
  headcount_limit?: number | null
  status?: string | null
  sort_order?: number | null
}

export interface DepartmentListParams {
  page?: number
  page_size?: number
  parent_id?: string
}

export async function listDepartments(params?: DepartmentListParams): Promise<PaginatedResponse<Department>> {
  return hrGet<PaginatedResponse<Department>>('/departments', params as Record<string, string | number>)
}

export async function getDepartmentTree(): Promise<DepartmentTreeNode[]> {
  const res = await hrGet<DepartmentTreeResponse>('/departments/tree')
  return res.tree
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
