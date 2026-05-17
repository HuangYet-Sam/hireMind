import { hrGet } from './client'

export interface DashboardData {
  open_positions: number
  candidates_in_pipeline: number
  interviews_this_week: number
  offers_pending: number
  avg_time_to_hire: number | null
}

export interface PipelineStage {
  stage: string
  count: number
}

export interface PipelineResponse {
  stages: PipelineStage[]
}

export interface TimeToHirePeriod {
  period: string
  avg_days: number
  count: number
}

export interface SourceEffectiveness {
  source: string
  total: number
  hired: number
  conversion_rate: number
}

export interface DepartmentSummary {
  department: string
  positions: number
  candidates: number
}

export interface AnalyticsParams {
  date_from?: string
  date_to?: string
  department_id?: string
  position_id?: string
}

export async function getDashboardOverview(params?: AnalyticsParams): Promise<DashboardData> {
  return hrGet<DashboardData>('/analytics/dashboard', params as Record<string, string>)
}

export async function getKpiSummary(params?: AnalyticsParams): Promise<DashboardData> {
  return hrGet<DashboardData>('/analytics/dashboard', params as Record<string, string>)
}

export async function getRecruitmentFunnel(params?: AnalyticsParams): Promise<PipelineStage[]> {
  const res = await hrGet<PipelineResponse>('/analytics/pipeline', params as Record<string, string>)
  return res.stages ?? res as unknown as PipelineStage[]
}

export async function getTimeToHire(params?: AnalyticsParams & { group_by?: string }): Promise<TimeToHirePeriod[]> {
  return hrGet<TimeToHirePeriod[]>('/analytics/time-to-hire', params as Record<string, string>)
}

/**
 * Position-level metrics.
 * NOTE: The backend has no /analytics/positions endpoint.
 * This function will always fall back to [] until the endpoint is added.
 */
export async function getPositionMetrics(params?: AnalyticsParams): Promise<unknown[]> {
  try {
    return await hrGet<unknown[]>('/analytics/positions', params as Record<string, string>)
  } catch {
    // Backend does not implement this endpoint yet — return empty fallback
    return []
  }
}

export async function getSourceBreakdown(): Promise<SourceEffectiveness[]> {
  return hrGet<SourceEffectiveness[]>('/analytics/source-effectiveness')
}

export async function getDepartmentSummary(): Promise<DepartmentSummary[]> {
  return hrGet<DepartmentSummary[]>('/analytics/department-summary')
}
