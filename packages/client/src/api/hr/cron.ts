import { hrGet, hrPost, hrPatch, hrDelete } from './client'
import type { PaginatedResponse } from './client'

export interface CronJob {
  id: string
  name: string
  description: string
  schedule: string
  skill_name: string
  enabled: boolean
  last_run_at: string | null
  last_run_status: string | null
  next_run_at: string | null
  created_at: string
  updated_at: string
}

export interface CronRun {
  id: string
  job_id: string
  job_name: string
  status: string
  started_at: string
  completed_at: string | null
  duration_ms: number | null
  result_summary: string | null
  error: string | null
}

export interface CreateCronJobRequest {
  name: string
  description?: string
  schedule: string
  skill_name: string
  enabled?: boolean
}

export interface UpdateCronJobRequest {
  name?: string
  description?: string
  schedule?: string
  skill_name?: string
  enabled?: boolean
}

export interface CronJobListParams {
  page?: number
  page_size?: number
  enabled?: boolean
}

export interface CronRunListParams {
  page?: number
  page_size?: number
  job_id?: string
  status?: string
}

export async function listCronJobs(params?: CronJobListParams): Promise<PaginatedResponse<CronJob>> {
  try {
    return await hrGet<PaginatedResponse<CronJob>>('/cron/jobs', params as Record<string, string | number>)
  } catch {
    return { items: [], total: 0, page: 1, page_size: 20, pages: 0 }
  }
}

export async function getCronJob(id: string): Promise<CronJob> {
  return hrGet<CronJob>(`/cron/jobs/${id}`)
}

export async function createCronJob(data: CreateCronJobRequest): Promise<CronJob> {
  return hrPost<CronJob>('/cron/jobs', data)
}

export async function updateCronJob(id: string, data: UpdateCronJobRequest): Promise<CronJob> {
  return hrPatch<CronJob>(`/cron/jobs/${id}`, data)
}

export async function deleteCronJob(id: string): Promise<{ ok: boolean }> {
  return hrDelete<{ ok: boolean }>(`/cron/jobs/${id}`)
}

export async function toggleCronJob(id: string, enabled: boolean): Promise<CronJob> {
  return hrPatch<CronJob>(`/cron/jobs/${id}`, { enabled })
}

export async function triggerCronJob(id: string): Promise<CronRun> {
  return hrPost<CronRun>(`/cron/jobs/${id}/trigger`)
}

export async function listCronRuns(params?: CronRunListParams): Promise<PaginatedResponse<CronRun>> {
  try {
    return await hrGet<PaginatedResponse<CronRun>>('/cron/runs', params as Record<string, string | number>)
  } catch {
    return { items: [], total: 0, page: 1, page_size: 20, pages: 0 }
  }
}

export async function getCronRun(id: string): Promise<CronRun> {
  return hrGet<CronRun>(`/cron/runs/${id}`)
}
