/**
 * Skills API — M9
 *
 * CRUD operations for AI Skill registry with call/stats support.
 *
 * GET    /skills                — List all skills
 * POST   /skills                — Register a new skill
 * GET    /skills/:id            — Get skill detail
 * PUT    /skills/:id            — Update skill
 * DELETE /skills/:id            — Delete skill
 * POST   /skills/:id/call       — Call/invoke a skill
 * GET    /skills/:id/stats      — Get skill statistics
 * GET    /skills/stats          — Global stats overview
 */
import { hrGet, hrPost, hrPut, hrDelete } from './client'

// ── Types ──────────────────────────────────────────────────

export interface Skill {
  id: string
  name: string
  type: string
  description: string
  prompt_template: string
  input_schema: string
  output_schema: string
  tags: string[]
  enabled: boolean
  call_count: number
  success_count: number
  fail_count: number
  avg_latency_ms: number | null
  created_at: string
  updated_at: string
}

export interface SkillCreateRequest {
  name: string
  type: string
  description?: string
  prompt_template?: string
  input_schema?: string
  output_schema?: string
  tags?: string[]
}

export interface SkillUpdateRequest {
  name?: string
  type?: string
  description?: string
  prompt_template?: string
  input_schema?: string
  output_schema?: string
  tags?: string[]
  enabled?: boolean
}

export interface SkillCallRequest {
  input: Record<string, unknown>
}

export interface SkillCallResponse {
  output: unknown
  latency_ms: number
  status: 'success' | 'failed'
  error?: string
}

export interface SkillStats {
  skill_id: string
  skill_name: string
  total_calls: number
  success_count: number
  fail_count: number
  avg_latency_ms: number
  recent_calls: {
    id: string
    status: string
    latency_ms: number
    called_at: string
  }[]
}

export interface SkillListParams {
  keyword?: string
  type?: string
  enabled?: boolean
}

export interface GlobalStatsResponse {
  total_skills: number
  total_calls: number
  total_success: number
  avg_latency_ms: number
}

// ── API Functions ──────────────────────────────────────────

/** Fetch all skills (with optional filter) */
export async function fetchSkills(params?: SkillListParams): Promise<Skill[]> {
  try {
    const res = await hrGet<{ items: Skill[] }>('/skills', params as Record<string, string>)
    return res.items ?? (res as unknown as Skill[])
  } catch {
    return []
  }
}

/** Register a new skill */
export async function registerSkill(data: SkillCreateRequest): Promise<Skill> {
  return hrPost<Skill>('/skills', data)
}

/** Get a single skill by ID */
export async function getSkill(id: string): Promise<Skill> {
  return hrGet<Skill>(`/skills/${id}`)
}

/** Update skill definition */
export async function updateSkill(id: string, data: SkillUpdateRequest): Promise<Skill> {
  return hrPut<Skill>(`/skills/${id}`, data)
}

/** Delete a skill */
export async function deleteSkill(id: string): Promise<{ ok: boolean }> {
  return hrDelete<{ ok: boolean }>(`/skills/${id}`)
}

/** Call/invoke a skill with input */
export async function callSkill(id: string, input: Record<string, unknown>): Promise<SkillCallResponse> {
  return hrPost<SkillCallResponse>(`/skills/${id}/call`, { input })
}

/** Get statistics for a specific skill */
export async function getSkillStats(id: string): Promise<SkillStats> {
  return hrGet<SkillStats>(`/skills/${id}/stats`)
}

/** Get global skill statistics */
export async function getGlobalStats(): Promise<GlobalStatsResponse> {
  try {
    return await hrGet<GlobalStatsResponse>('/skills/stats')
  } catch {
    return { total_skills: 0, total_calls: 0, total_success: 0, avg_latency_ms: 0 }
  }
}
