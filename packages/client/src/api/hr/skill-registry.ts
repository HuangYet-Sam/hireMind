import { hrGet } from './client'
import type { PaginatedResponse } from './client'

export interface RegisteredSkill {
  id: string
  name: string
  description: string
  category: string
  version: string
  enabled: boolean
  prompt_template: string
  call_count: number
  success_count: number
  fail_count: number
  avg_duration_ms: number | null
  last_called_at: string | null
  registered_at: string
}

export interface SkillCallStat {
  skill_name: string
  date: string
  call_count: number
  success_count: number
  fail_count: number
  avg_duration_ms: number
}

export interface SkillListParams {
  page?: number
  page_size?: number
  category?: string
  enabled?: boolean
}

export interface SkillCallStatParams {
  skill_name?: string
  date_from?: string
  date_to?: string
}

export async function listRegisteredSkills(params?: SkillListParams): Promise<PaginatedResponse<RegisteredSkill>> {
  try {
    return await hrGet<PaginatedResponse<RegisteredSkill>>('/skills/registry', params as Record<string, string | number>)
  } catch {
    return { items: [], total: 0, page: 1, page_size: 20, pages: 0 }
  }
}

export async function getRegisteredSkill(id: string): Promise<RegisteredSkill> {
  return hrGet<RegisteredSkill>(`/skills/registry/${id}`)
}

export async function getSkillPrompt(id: string): Promise<{ prompt_template: string }> {
  return hrGet<{ prompt_template: string }>(`/skills/registry/${id}/prompt`)
}

export async function getSkillCallStats(params?: SkillCallStatParams): Promise<SkillCallStat[]> {
  try {
    return await hrGet<SkillCallStat[]>('/skills/call-stats', params as Record<string, string>)
  } catch {
    return []
  }
}
