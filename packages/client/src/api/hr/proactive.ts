/**
 * Proactive AI API — M10 主动AI推送中心
 *
 * GET  /proactive/messages       — 推送消息列表(分页+筛选)
 * POST /proactive/scan           — 触发主动扫描
 * POST /proactive/messages/:id   — 处理消息(确认/忽略/执行)
 * POST /proactive/batch-read     — 批量标已读
 * GET  /proactive/stats          — 推送统计
 *
 * GET  /proactive/talent-activation      — 沉默候选人列表
 * POST /proactive/talent-activation/:id  — 激活候选人
 * POST /proactive/batch-activate         — 批量激活
 * GET  /proactive/activation-stats       — 激活统计
 * GET  /proactive/activation-strategies  — 可用激活策略
 */
import { hrGet, hrPost } from './client'

// ── Types ────────────────────────────────────────────────────

/** 推送消息分类 */
export type ProactiveCategory =
  | 'resume_arrival'
  | 'match_anomaly'
  | 'interview_timeout'
  | 'offer_deadlock'
  | 'funnel_bottleneck'
  | 'silent_activation'
  | 'system'

/** 推送消息状态 */
export type ProactiveStatus = 'pending' | 'confirmed' | 'ignored' | 'executed'

/** 推送消息 */
export interface ProactiveMessage {
  id: string
  category: ProactiveCategory
  title: string
  content: string
  entity_type?: string
  entity_id?: string
  action_label?: string
  action_link?: string
  status: ProactiveStatus
  is_read: boolean
  priority: 'low' | 'medium' | 'high' | 'urgent'
  created_at: string
  read_at?: string
  handled_at?: string
}

/** 推送消息筛选 */
export interface ProactiveMessageFilters {
  page?: number
  page_size?: number
  category?: ProactiveCategory
  status?: ProactiveStatus
  is_read?: boolean
  date_from?: string
  date_to?: string
}

/** 推送列表响应 */
export interface ProactiveMessageListResponse {
  items: ProactiveMessage[]
  total: number
  page: number
  page_size: number
  pages: number
}

/** 推送统计 */
export interface ProactiveStats {
  today_total: number
  pending_count: number
  confirmed_count: number
  ignored_count: number
  executed_count: number
  by_category: Record<ProactiveCategory, number>
}

/** 处理动作 */
export type MessageAction = 'confirm' | 'ignore' | 'execute'

/** 沉默候选人 */
export interface SilentCandidate {
  id: string
  candidate_id: string
  name: string
  silent_days: number
  match_position_count: number
  recommended_strategy: string
  strategy_id: string
  last_contact_at?: string
  skills: string[]
  position_direction?: string
}

/** 激活策略 */
export interface ActivationStrategy {
  id: string
  name: string
  description: string
  match_score: number
  recommended_message: string
  best_contact_time: string
  channel: string
}

/** 候选人筛选 */
export interface TalentActivationFilters {
  page?: number
  page_size?: number
  silent_days_min?: number
  position_direction?: string
  skills?: string
}

/** 激活统计 */
export interface ActivationStats {
  silent_count: number
  activated_count: number
  success_rate: number
  avg_response_days: number
}

// ── API Functions ────────────────────────────────────────────

/** 获取推送消息列表 */
export async function fetchProactiveMessages(
  filters?: ProactiveMessageFilters,
): Promise<ProactiveMessageListResponse> {
  return hrGet<ProactiveMessageListResponse>(
    '/proactive/messages',
    filters as Record<string, string | number | boolean | undefined>,
  )
}

/** 触发主动扫描 */
export async function triggerProactiveScan(): Promise<{ task_id: string; message: string }> {
  return hrPost<{ task_id: string; message: string }>('/proactive/scan')
}

/** 处理消息 */
export async function handleMessage(id: string, action: MessageAction): Promise<ProactiveMessage> {
  return hrPost<ProactiveMessage>(`/proactive/messages/${id}`, { action })
}

/** 批量标已读 */
export async function batchMarkRead(ids?: string[]): Promise<{ ok: boolean }> {
  return hrPost<{ ok: boolean }>('/proactive/batch-read', { ids })
}

/** 获取推送统计 */
export async function fetchProactiveStats(): Promise<ProactiveStats> {
  return hrGet<ProactiveStats>('/proactive/stats')
}

/** 获取沉默候选人列表 */
export async function fetchTalentActivation(
  filters?: TalentActivationFilters,
): Promise<{ items: SilentCandidate[]; total: number; page: number; page_size: number }> {
  return hrGet<{ items: SilentCandidate[]; total: number; page: number; page_size: number }>(
    '/proactive/talent-activation',
    filters as Record<string, string | number | undefined>,
  )
}

/** 激活候选人 */
export async function activateTalent(
  candidateId: string,
  strategyId: string,
): Promise<{ ok: boolean; message: string }> {
  return hrPost<{ ok: boolean; message: string }>(`/proactive/talent-activation/${candidateId}`, {
    strategy_id: strategyId,
  })
}

/** 批量激活 */
export async function batchActivate(
  items: Array<{ candidate_id: string; strategy_id: string }>,
): Promise<{ success_count: number; fail_count: number }> {
  return hrPost<{ success_count: number; fail_count: number }>('/proactive/batch-activate', { items })
}

/** 获取激活统计 */
export async function fetchActivationStats(): Promise<ActivationStats> {
  return hrGet<ActivationStats>('/proactive/activation-stats')
}

/** 获取可用激活策略 */
export async function fetchActivationStrategies(): Promise<ActivationStrategy[]> {
  return hrGet<ActivationStrategy[]>('/proactive/activation-strategies')
}
