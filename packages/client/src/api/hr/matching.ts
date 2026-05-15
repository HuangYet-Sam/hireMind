import { hrGet, hrPost } from './client'

// ─── Types ──────────────────────────────────────────────

export interface MatchResult {
  id: string
  position_id: string
  candidate_id: string
  candidate_name?: string
  overall_score: number
  skill_score: number
  experience_score: number
  education_score: number
  bonus_score: number
  matched_skills: string[]
  missing_skills: string[]
  strengths: string[]
  gaps: string[]
  suggestions: string[]
  created_at: string
}

export interface MatchRequestParams {
  top_k?: number
  min_score?: number
}

// ─── API Functions ──────────────────────────────────────

export async function matchCandidatesForPosition(
  positionId: string,
  params?: MatchRequestParams
): Promise<{ position_id: string; matches: MatchResult[]; total: number }> {
  return hrPost(`/matching/position/${positionId}/candidates`, params)
}

export async function matchPositionsForCandidate(
  candidateId: string,
  params?: MatchRequestParams
): Promise<{ candidate_id: string; matches: MatchResult[]; total: number }> {
  return hrPost(`/matching/candidate/${candidateId}/positions`, params)
}

export async function getMatchResult(
  positionId: string
): Promise<{ position_id: string; matches: MatchResult[]; total: number } | null> {
  return hrGet(`/matching/position/${positionId}/result`)
}
