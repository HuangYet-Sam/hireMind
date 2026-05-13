import { hrGet, hrPost } from './client'

// ─── Types ──────────────────────────────────────────────

export interface AiTask {
  id: string
  type: 'resume_parsing' | 'candidate_matching' | 'batch_scoring' | 'report_generation' | 'candidate_summary'
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  input_summary: string
  result: unknown | null
  error: string | null
  created_by: string
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface AiTaskListParams {
  page?: number
  page_size?: number
  status?: AiTask['status']
  type?: AiTask['type']
}

export interface CreateAiTaskRequest {
  type: AiTask['type']
  input: Record<string, unknown>
}

// ─── API Functions ──────────────────────────────────────

export async function listAiTasks(params?: AiTaskListParams): Promise<AiTask[]> {
  return hrGet<AiTask[]>('/ai-tasks', params as Record<string, string | number>)
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
