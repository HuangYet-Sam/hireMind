/**
 * Analytics API — M8 Enhanced
 *
 * Existing endpoints + new funnel / trends / source / channel / position APIs
 * + M8: Comparison, Prediction, Position Analysis, Channel ROI Enhanced,
 *        Insight Scan, Insight History, Insight Actions, Report Export/Download
 */
import { hrGet, hrPost } from './client'

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

// ── M8 New Types ─────────────────────────────────────────────

export type ComparisonMode = 'none' | 'yoy' | 'mom'

export interface ComparisonFunnelData {
  current: FunnelStageDetailed[]
  previous: FunnelStageDetailed[]
  comparison_mode: ComparisonMode
  previous_period_label: string
}

export interface PredictionPoint {
  date: string
  predicted: number
  lower_bound?: number
  upper_bound?: number
}

export interface TrendWithPrediction {
  historical: TrendPoint[]
  prediction: PredictionPoint[]
}

export interface PositionAnalysisData {
  position_id: string
  position_title: string
  department: string
  total_candidates: number
  interview_rate: number
  offer_rate: number
  avg_time_to_hire: number
  performance_score: number
  funnel_stages: FunnelStageDetailed[]
  rank: number
}

export interface ChannelROIEnhanced extends ChannelROI {
  roi_grade: 'A' | 'B' | 'C' | 'D'
  cost_efficiency_score: number
  quality_score: number
}

/** M8: 漏斗对比参数 */
export interface FunnelComparisonParams extends AnalyticsParams {
  comparison_mode: ComparisonMode
}

/** M8: 趋势预测参数 */
export interface TrendPredictionParams extends TrendParams {
  predict_periods?: number
}

/** M8: 渠道 ROI 参数 */
export interface ChannelROIParams extends AnalyticsParams {
  include_cost?: boolean
  include_quality?: boolean
}

/** M8: 洞察历史参数 */
export interface InsightHistoryParams {
  page?: number
  page_size?: number
  category?: string
  status?: 'all' | 'read' | 'unread' | 'ignored'
  date_from?: string
  date_to?: string
}

/** M8: 洞察历史条目 */
export interface InsightHistoryItem {
  id: string
  category: string
  title: string
  content: string
  confidence: number
  action_suggestion?: string
  created_at: string
  read: boolean
  ignored: boolean
}

/** M8: 洞察历史响应 */
export interface InsightHistoryResponse {
  items: InsightHistoryItem[]
  total: number
  page: number
  page_size: number
  pages: number
}

/** M8: 报表导出参数 */
export interface ReportExportParams {
  report_type: 'funnel' | 'trend' | 'position' | 'channel' | 'full'
  format: 'excel' | 'pdf'
  date_from?: string
  date_to?: string
}

/** M8: 报表导出响应 */
export interface ReportExportResponse {
  report_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  download_url?: string
  file_size?: string
  created_at: string
}

// ── M8 New API Functions ─────────────────────────────────────

/** 获取漏斗同比/环比对比数据 */
export async function fetchFunnelComparison(params?: FunnelComparisonParams): Promise<ComparisonFunnelData> {
  return hrGet<ComparisonFunnelData>('/analytics/funnel-comparison', params as Record<string, string>)
}

/** 获取趋势预测数据（含未来 N 期预测） */
export async function fetchTrendPrediction(params: TrendPredictionParams): Promise<TrendWithPrediction> {
  return hrGet<TrendWithPrediction>('/analytics/trends-prediction', params as Record<string, string>)
}

/** 获取单个岗位的详细分析数据 */
export async function fetchPositionAnalytics(positionId: string): Promise<PositionAnalysisData> {
  return hrGet<PositionAnalysisData>(`/analytics/position/${positionId}/analytics`)
}

/** 获取渠道 ROI 增强数据（含成本/质量/效率评分） */
export async function fetchChannelROIEnhanced(params?: ChannelROIParams): Promise<ChannelROIEnhanced[]> {
  return hrGet<ChannelROIEnhanced[]>('/analytics/channel-roi-enhanced', params as Record<string, string>)
}

/** 触发 AI 洞察扫描（后台分析生成洞察） */
export async function triggerInsightScan(): Promise<{ task_id: string; status: string }> {
  return hrPost<{ task_id: string; status: string }>('/analytics/insight-scan')
}

/** 获取洞察历史记录（分页） */
export async function fetchInsightHistory(params?: InsightHistoryParams): Promise<InsightHistoryResponse> {
  return hrGet<InsightHistoryResponse>('/analytics/insight-history', params as Record<string, string>)
}

/** 更新洞察操作（标记已读/未读/忽略） */
export async function updateInsightAction(
  insightId: string,
  action: 'read' | 'unread' | 'ignore' | 'dismiss',
): Promise<{ ok: boolean }> {
  return hrPost<{ ok: boolean }>(`/analytics/insight/${insightId}/${action}`)
}

/** 发起报表导出 */
export async function exportReport(params: ReportExportParams): Promise<ReportExportResponse> {
  return hrPost<ReportExportResponse>('/analytics/report/export', params)
}

/** 下载已生成的报表 */
export async function downloadReport(reportId: string): Promise<Blob> {
  const res = await fetch(`/api/v1/analytics/report/${reportId}/download`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('hermes_api_key') || ''}`,
    },
  })
  if (!res.ok) throw new Error(`Download failed: ${res.status}`)
  return res.blob()
}
