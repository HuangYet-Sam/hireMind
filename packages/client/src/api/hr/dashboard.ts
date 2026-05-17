/**
 * Dashboard API — 4 endpoints per PRD §9.1
 *
 * GET /dashboard/todos       — 待办清单
 * GET /dashboard/schedule    — 今日日程
 * GET /dashboard/metrics     — 快捷指标
 * GET /dashboard/ai-insights — AI洞察推送
 */
import { hrGet } from './client'

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
  created_at?: string
  action_label?: string
  action_link?: string
}

export interface AiInsightsResponse {
  insights: AiInsight[]
  total: number
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

/** 获取 AI 洞察推送 */
export async function getDashboardAiInsights(): Promise<AiInsightsResponse> {
  return hrGet<AiInsightsResponse>('/dashboard/ai-insights')
}
