import { hrGet, hrPost } from './client'
import type { PaginatedResponse } from './client'

export interface ScheduledTask {
  id: string
  name: string
  type: 'scheduled' | 'one_time'
  skill_name: string
  schedule: string | null
  input_params: Record<string, unknown>
  status: 'active' | 'paused' | 'completed' | 'failed'
  last_run_at: string | null
  next_run_at: string | null
  last_result: TaskResult | null
  created_at: string
}

export interface TaskResult {
  task_id: string
  status: string
  output: unknown
  error: string | null
  started_at: string
  completed_at: string | null
  duration_ms: number | null
}

export interface CreateScheduledTaskRequest {
  name: string
  type: 'scheduled' | 'one_time'
  skill_name: string
  schedule?: string
  input_params?: Record<string, unknown>
  run_at?: string
}

export interface ScheduledTaskListParams {
  page?: number
  page_size?: number
  type?: string
  status?: string
}

export async function listScheduledTasks(params?: ScheduledTaskListParams): Promise<PaginatedResponse<ScheduledTask>> {
  try {
    return await hrGet<PaginatedResponse<ScheduledTask>>('/scheduled-tasks', params as Record<string, string | number>)
  } catch {
    return { items: [], total: 0, page: 1, page_size: 20, pages: 0 }
  }
}

export async function getScheduledTask(id: string): Promise<ScheduledTask> {
  return hrGet<ScheduledTask>(`/scheduled-tasks/${id}`)
}

export async function createScheduledTask(data: CreateScheduledTaskRequest): Promise<ScheduledTask> {
  return hrPost<ScheduledTask>('/scheduled-tasks', data)
}

export async function pauseScheduledTask(id: string): Promise<{ ok: boolean }> {
  return hrPost<{ ok: boolean }>(`/scheduled-tasks/${id}/pause`)
}

export async function resumeScheduledTask(id: string): Promise<{ ok: boolean }> {
  return hrPost<{ ok: boolean }>(`/scheduled-tasks/${id}/resume`)
}

export async function cancelScheduledTask(id: string): Promise<{ ok: boolean }> {
  return hrPost<{ ok: boolean }>(`/scheduled-tasks/${id}/cancel`)
}

export async function getTaskResult(id: string): Promise<TaskResult> {
  return hrGet<TaskResult>(`/scheduled-tasks/${id}/result`)
}
