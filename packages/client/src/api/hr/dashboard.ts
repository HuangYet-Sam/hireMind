/**
 * Dashboard API — M7 Enhanced
 *
 * GET  /dashboard/todos         — 待办清单
 * GET  /dashboard/schedule      — 今日日程
 * GET  /dashboard/metrics       — 快捷指标
 * GET  /dashboard/ai-insights   — AI洞察推送
 * GET  /dashboard/metrics/kpi   — 核心指标卡片
 * GET  /dashboard/funnel        — 招聘漏斗
 * GET  /dashboard/trends        — 趋势折线
 * GET  /dashboard/sources       — 来源分布
 * GET  /dashboard/insights      — AI洞察 (新接口)
 * POST /dashboard/report/daily  — 生成日报
 * POST /dashboard/report/weekly — 生成周报
 */
import { hrGet, hrPost } from './client'

// ── Types ────────────────────────────────────────────────────

export interface TodoItem {
  id: string
  title: string
  description?: string
  due_date?: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
  status: 'pending' | 'in_progress' | 'completed'
  related_type?: string
  related_id?: string
}

export interface TodoListResponse {
  items: TodoItem[]
  total: number
}

export interface ScheduleEvent {
  id: string
  title: string
  start_time: string
  end_time?: string
  type: 'interview' | 'meeting' | 'deadline' | 'reminder'
  location?: string
  candidate_name?: string
  position_title?: string
  status: 'scheduled' | 'completed' | 'cancelled'
}

export interface ScheduleResponse {
  date: string
  events: ScheduleEvent[]
  total: number
}

export interface MetricItem {
  key: string
  label: string
  value: number | string
  unit?: string
  trend?: 'up' | 'down' | 'flat'
  trend_value?: number
  period?: string
}

export interface MetricsResponse {
  metrics: MetricItem[]
}

export interface AiInsight {
  id: string
  type: 'recommendation' | 'alert' | 'summary' | 'suggestion'
  title: string
  content: string
  priority: 'low' | 'medium' | 'high'
  confidence?: number
  action_label?: string
  action_link?: string
  action_suggestion?: string
  created_at?: string
}

export interface AiInsightsResponse {
  insights: AiInsight[]
  total: number
}

/** 核心指标卡片 */
export interface KpiMetrics {
  open_positions: number
  candidates_in_pipeline: number
  interviews_this_week: number
  offers_pending: number
  open_positions_trend?: number
  candidates_trend?: number
  interviews_trend?: number
  offers_trend?: number
}

/** 漏斗阶段 */
export interface FunnelStage {
  stage: string
  count: number
  percentage?: number
  conversion_rate?: number
}

/** 趋势数据点 */
export interface TrendDataPoint {
  date: string
  resumes: number
  matches: number
  interviews: number
  offers: number
}

export interface TrendParams {
  period: 'day' | 'week' | 'month'
  date_from?: string
  date_to?: string
}

/** 来源分布 */
export interface SourceDistribution {
  source: string
  count: number
  percentage: number
  color?: string
}

/** AI 洞察（新接口） */
export interface AIInsight {
  id: string
  category: 'trend' | 'risk' | 'opportunity' | 'suggestion'
  title: string
  content: string
  confidence: number
  action_suggestion?: string
  created_at: string
}

/** 日报/周报 */
export interface ReportResponse {
  id: string
  title: string
  content: string
  generated_at: string
}

// ── API Functions ────────────────────────────────────────────

/** 获取待办清单 */
export async function getDashboardTodos(): Promise<TodoListResponse> {
  return hrGet<TodoListResponse>('/dashboard/todos')
}

/** 获取今日日程 */
export async function getDashboardSchedule(): Promise<ScheduleResponse> {
  return hrGet<ScheduleResponse>('/dashboard/schedule')
}

/** 获取快捷指标 */
export async function getDashboardMetrics(): Promise<MetricsResponse> {
  return hrGet<MetricsResponse>('/dashboard/metrics')
}

/** 获取 AI 洞察推送 (旧接口) */
export async function getDashboardAiInsights(): Promise<AiInsightsResponse> {
  return hrGet<AiInsightsResponse>('/dashboard/ai-insights')
}

// ── M7 New API Functions ─────────────────────────────────────

/** 获取核心指标（KPI 卡片） */
export async function fetchMetrics(): Promise<KpiMetrics> {
  return hrGet<KpiMetrics>('/dashboard/metrics/kpi')
}

/** 获取招聘漏斗数据 */
export async function fetchFunnel(params?: { position_id?: string }): Promise<FunnelStage[]> {
  return hrGet<FunnelStage[]>('/dashboard/funnel', params as Record<string, string>)
}

/** 获取待办清单（新版） */
export async function fetchTodos(): Promise<TodoListResponse> {
  return hrGet<TodoListResponse>('/dashboard/todos')
}

/** 获取趋势数据 */
export async function fetchTrends(params: TrendParams): Promise<TrendDataPoint[]> {
  return hrGet<TrendDataPoint[]>('/dashboard/trends', params as Record<string, string>)
}

/** 获取来源分布 */
export async function fetchSources(): Promise<SourceDistribution[]> {
  return hrGet<SourceDistribution[]>('/dashboard/sources')
}

/** 获取 AI 洞察（新接口） */
export async function fetchInsights(): Promise<AIInsight[]> {
  return hrGet<AIInsight[]>('/dashboard/insights')
}

/** 生成日报 */
export async function generateDailyReport(): Promise<ReportResponse> {
  return hrPost<ReportResponse>('/dashboard/report/daily')
}

/** 生成周报 */
export async function generateWeeklyReport(): Promise<ReportResponse> {
  return hrPost<ReportResponse>('/dashboard/report/weekly')
}
