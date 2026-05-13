import { hrGet, hrPost } from './client'

// ─── Types ──────────────────────────────────────────────

export interface MatchResult {
  id: string
  position_id: string
  candidate_id: string
  position_title?: string
  candidate_name?: string
  overall_score: number
  skill_score: number
  experience_score: number
  education_score: number
  culture_score: number
  details: MatchDetail[]
  ai_explanation: string | null
  status: 'pending' | 'completed' | 'failed'
  created_at: string
}

export interface MatchDetail {
  dimension: string
  score: number
  weight: number
  reasoning: string
  evidence: string[]
}

export interface MatchRequest {
  position_id: string
  candidate_ids?: string[]
  top_k?: number
  include_explanation?: boolean
}

export interface BatchMatchRequest {
  position_ids?: string[]
  candidate_ids?: string[]
  top_k?: number
}

export interface MatchListParams {
  page?: number
  page_size?: number
  position_id?: string
  candidate_id?: string
  min_score?: number
}

// ─── API Functions ──────────────────────────────────────

export async function listMatches(params?: MatchListParams): Promise<MatchResult[]> {
  return hrGet<MatchResult[]>('/matching', params as Record<string, string | number>)
}

export async function getMatch(id: string): Promise<MatchResult> {
  return hrGet<MatchResult>(`/matching/${id}`)
}

export async function matchPositionToCandidates(data: MatchRequest): Promise<MatchResult[]> {
  return hrPost<MatchResult[]>('/matching/match', data)
}

export async function batchMatch(data: BatchMatchRequest): Promise<{ task_id: string }> {
  return hrPost<{ task_id: string }>('/matching/batch', data)
}

export async function getMatchMatrix(positionId: string): Promise<MatchResult[]> {
  return hrGet<MatchResult[]>(`/matching/matrix/${positionId}`)
}
