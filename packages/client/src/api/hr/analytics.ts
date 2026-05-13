import { hrGet } from './client'

// ─── Types ──────────────────────────────────────────────

export interface RecruitmentFunnel {
  stage: string
  count: number
  conversion_rate: number
}

export interface HiringTrend {
  date: string
  applications: number
  interviews: number
  offers: number
  hires: number
}

export interface PositionMetrics {
  position_id: string
  position_title: string
  days_open: number
  applications: number
  interviews: number
  offers: number
  time_to_hire: number | null
  cost_per_hire: number | null
}

export interface KpiSummary {
  total_open_positions: number
  total_candidates: number
  interviews_this_week: number
  offers_pending: number
  hires_this_month: number
  avg_time_to_hire: number | null
  offer_acceptance_rate: number
  source_breakdown: SourceBreakdown[]
}

export interface SourceBreakdown {
  source: string
  count: number
  percentage: number
}

export interface AnalyticsParams {
  date_from?: string
  date_to?: string
  department_id?: string
  position_id?: string
}

// ─── API Functions ──────────────────────────────────────

export async function getKpiSummary(params?: AnalyticsParams): Promise<KpiSummary> {
  return hrGet<KpiSummary>('/analytics/kpi', params as Record<string, string>)
}

export async function getRecruitmentFunnel(params?: AnalyticsParams): Promise<RecruitmentFunnel[]> {
  return hrGet<RecruitmentFunnel[]>('/analytics/funnel', params as Record<string, string>)
}

export async function getHiringTrends(params?: AnalyticsParams): Promise<HiringTrend[]> {
  return hrGet<HiringTrend[]>('/analytics/trends', params as Record<string, string>)
}

export async function getPositionMetrics(params?: AnalyticsParams): Promise<PositionMetrics[]> {
  return hrGet<PositionMetrics[]>('/analytics/positions', params as Record<string, string>)
}

export async function getSourceBreakdown(params?: AnalyticsParams): Promise<SourceBreakdown[]> {
  return hrGet<SourceBreakdown[]>('/analytics/sources', params as Record<string, string>)
}

export async function getDashboardOverview(): Promise<KpiSummary> {
  return hrGet<KpiSummary>('/analytics/dashboard')
}
