import { hrGet, hrPost } from './client'
import type { PaginatedResponse } from './client'

export interface AiTask {
  id: string
  type: string
  status: string
  progress: number
  input_summary: string
  result: unknown
  error: string | null
  created_by: string
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface AiTaskListParams {
  page?: number
  page_size?: number
  status?: string
  type?: string
}

export interface CreateAiTaskRequest {
  type: string
  input: Record<string, unknown>
}

export async function listAiTasks(params?: AiTaskListParams): Promise<PaginatedResponse<AiTask>> {
  try {
    return await hrGet<PaginatedResponse<AiTask>>('/ai-tasks', params as Record<string, string | number>)
  } catch {
    return { items: [], total: 0, page: 1, page_size: 20, pages: 0 }
  }
}

export async function getAiTask(id: string): Promise<AiTask> {
  return hrGet<AiTask>(`/ai-tasks/${id}`)
}

export async function createAiTask(data: CreateAiTaskRequest): Promise<AiTask> {
  return hrPost<AiTask>('/ai-tasks', data)
}

export async function cancelAiTask(id: string): Promise<{ ok: boolean }> {
  return hrPost<{ ok: boolean }>(`/ai-tasks/${id}/cancel`)
}

export async function retryAiTask(id: string): Promise<AiTask> {
  return hrPost<AiTask>(`/ai-tasks/${id}/retry`)
}
