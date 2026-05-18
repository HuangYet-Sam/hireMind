/**
 * Analytics API — M7 Enhanced
 *
 * Existing endpoints + new funnel / trends / source / channel / position APIs
 */
import { hrGet } from './client'

// ── Types ────────────────────────────────────────────────────

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

// ── M7 New Types ─────────────────────────────────────────────

/** 漏斗分析数据 */
export interface FunnelStageDetailed {
  stage: string
  count: number
  percentage: number
  conversion_rate: number
  avg_days_in_stage?: number
}

/** 趋势数据点 */
export interface TrendPoint {
  date: string
  resumes: number
  matches: number
  interviews: number
  offers: number
}

/** 来源分布 */
export interface SourceDistributionItem {
  source: string
  count: number
  percentage: number
}

/** 渠道 ROI */
export interface ChannelROI {
  source: string
  resume_count: number
  interview_rate: number
  offer_rate: number
  cost_per_hire: number
  total_cost: number
  roi_score: number
}

/** 岗位效能 */
export interface PositionPerformance {
  position_id: string
  position_title: string
  department: string
  total_candidates: number
  interview_rate: number
  offer_rate: number
  avg_time_to_hire: number
  funnel_stages: FunnelStageDetailed[]
  performance_score: number
}

export interface TrendParams {
  period: 'day' | 'week' | 'month'
  date_from?: string
  date_to?: string
}

// ── Existing API Functions ───────────────────────────────────

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

export async function getPositionMetrics(params?: AnalyticsParams): Promise<unknown[]> {
  try {
    return await hrGet<unknown[]>('/analytics/positions', params as Record<string, string>)
  } catch {
    return []
  }
}

export async function getSourceBreakdown(): Promise<SourceEffectiveness[]> {
  return hrGet<SourceEffectiveness[]>('/analytics/source-effectiveness')
}

export async function getDepartmentSummary(): Promise<DepartmentSummary[]> {
  return hrGet<DepartmentSummary[]>('/analytics/department-summary')
}

// ── M7 New API Functions ─────────────────────────────────────

/** 获取漏斗详细数据 */
export async function fetchFunnel(params?: AnalyticsParams): Promise<FunnelStageDetailed[]> {
  return hrGet<FunnelStageDetailed[]>('/analytics/funnel', params as Record<string, string>)
}

/** 获取趋势数据 */
export async function fetchTrends(params: TrendParams): Promise<TrendPoint[]> {
  return hrGet<TrendPoint[]>('/analytics/trends', params as Record<string, string>)
}

/** 获取来源分布 */
export async function fetchSourceDistribution(params?: AnalyticsParams): Promise<SourceDistributionItem[]> {
  return hrGet<SourceDistributionItem[]>('/analytics/source-distribution', params as Record<string, string>)
}

/** 获取渠道 ROI 对比 */
export async function fetchChannelROI(params?: AnalyticsParams): Promise<ChannelROI[]> {
  return hrGet<ChannelROI[]>('/analytics/channel-roi', params as Record<string, string>)
}

/** 获取岗位效能排名 */
export async function fetchPositionPerformance(params?: AnalyticsParams): Promise<PositionPerformance[]> {
  return hrGet<PositionPerformance[]>('/analytics/position-performance', params as Record<string, string>)
}
