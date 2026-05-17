import { hrGet, hrPost } from './client'

export interface MatchResultItem {
  candidate_id: string
  candidate_name: string | null
  overall_score: number
  skill_score: number | null
  experience_score: number | null
  education_score: number | null
  matched_skills: string[]
  missing_skills: string[]
  explanation: string | null
}

export interface PositionMatchResult {
  position_id: string
  position_title: string | null
  total_candidates: number
  matches: MatchResultItem[]
}

export interface CandidateMatchResultItem {
  position_id: string
  position_title: string | null
  overall_score: number
  skill_score: number | null
  matched_skills: string[]
  missing_skills: string[]
  explanation: string | null
}

export interface CandidateMatchResult {
  candidate_id: string
  total_positions: number
  matches: CandidateMatchResultItem[]
}

export interface MatchDetailResponse {
  id: string
  position_id: string
  candidate_id: string
  status: string
  overall_score: number | null
  skill_score: number | null
  experience_score: number | null
  education_score: number | null
  score_breakdown: Record<string, unknown> | null
  match_details: Record<string, unknown> | null
  matched_at: string | null
}

export interface MatchListResponse {
  items: MatchDetailResponse[]
  total: number
  pages: number
}

export interface MatchRequestParams {
  top_k?: number
  min_score?: number
}

export async function matchCandidatesForPosition(
  positionId: string,
  params?: MatchRequestParams
): Promise<PositionMatchResult> {
  return hrPost<PositionMatchResult>(
    `/matching/position/${positionId}/candidates`,
    undefined,
    params as Record<string, string | number | boolean | undefined>,
  )
}

export async function matchPositionsForCandidate(
  candidateId: string,
  params?: MatchRequestParams
): Promise<CandidateMatchResult> {
  return hrPost<CandidateMatchResult>(
    `/matching/candidate/${candidateId}/positions`,
    undefined,
    params as Record<string, string | number | boolean | undefined>,
  )
}

export async function getMatchResult(
  positionId: string
): Promise<MatchListResponse | null> {
  return hrGet<MatchListResponse>(`/matching/position/${positionId}/result`)
}
