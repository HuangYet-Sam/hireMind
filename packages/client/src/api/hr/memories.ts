/**
 * AI Memories API — M10 Memory Manager
 *
 * GET    /memories              — 记忆列表(分页+筛选)
 * POST   /memories              — 创建记忆
 * GET    /memories/:id          — 记忆详情
 * PUT    /memories/:id          — 更新记忆
 * DELETE /memories/:id          — 删除记忆
 * POST   /memories/search       — 搜索记忆
 * GET    /memories/stats         — 记忆统计
 * POST   /memories/trigger-build — 触发冷启动(7天记忆构建)
 * POST   /memories/consolidate   — 合并/去重记忆
 * POST   /memories/batch-delete  — 批量删除
 * POST   /memories/batch-expire  — 批量标记过期
 * POST   /memories/batch-merge   — 批量合并
 */
import { hrGet, hrPost, hrPut, hrDelete } from './client'

// ── Types ────────────────────────────────────────────────────

/** 记忆类型 */
export type MemoryType = 'preference' | 'insight' | 'decision' | 'pattern' | 'fact'

/** 记忆分类 */
export type MemoryCategory = 'recruitment' | 'candidate' | 'interview' | 'offer' | 'team' | 'process' | 'general'

/** 记忆实体 */
export interface Memory {
  id: string
  content: string
  summary: string
  type: MemoryType
  category: MemoryCategory
  source: string
  source_type: 'user_input' | 'observation' | 'inference' | 'import'
  confidence: number
  importance: 'low' | 'medium' | 'high' | 'critical'
  access_count: number
  tags: string[]
  related_memory_ids?: string[]
  entity_type?: string
  entity_id?: string
  is_expired: boolean
  created_at: string
  updated_at: string
  last_accessed_at?: string
}

/** 记忆筛选参数 */
export interface MemoryFilters {
  page?: number
  page_size?: number
  type?: MemoryType
  category?: MemoryCategory
  keyword?: string
  date_from?: string
  date_to?: string
  importance?: string
  is_expired?: boolean
}

/** 记忆列表响应 */
export interface MemoryListResponse {
  items: Memory[]
  total: number
  page: number
  page_size: number
  pages: number
}

/** 记忆创建/编辑数据 */
export interface MemoryFormData {
  content: string
  summary?: string
  type: MemoryType
  category: MemoryCategory
  importance?: 'low' | 'medium' | 'high' | 'critical'
  tags?: string[]
  source?: string
  entity_type?: string
  entity_id?: string
}

/** 记忆统计数据 */
export interface MemoryStats {
  total: number
  by_type: Record<MemoryType, number>
  by_category: Record<MemoryCategory, number>
  expired_count: number
  avg_confidence: number
  recent_count: number
}

/** 搜索请求 */
export interface MemorySearchParams {
  query: string
  limit?: number
  type?: MemoryType
}

/** 搜索响应 */
export interface MemorySearchResponse {
  items: Memory[]
  total: number
}

/** 批量操作请求 */
export interface BatchOperationRequest {
  ids: string[]
}

/** 合并请求 */
export interface MergeRequest {
  ids: string[]
  merged_content?: string
  merged_summary?: string
}

// ── API Functions ────────────────────────────────────────────

/** 获取记忆列表 */
export async function fetchMemories(filters?: MemoryFilters): Promise<MemoryListResponse> {
  return hrGet<MemoryListResponse>('/memories', filters as Record<string, string | number | boolean | undefined>)
}

/** 获取记忆详情 */
export async function getMemory(id: string): Promise<Memory> {
  return hrGet<Memory>(`/memories/${id}`)
}

/** 创建记忆 */
export async function createMemory(data: MemoryFormData): Promise<Memory> {
  return hrPost<Memory>('/memories', data)
}

/** 更新记忆 */
export async function updateMemory(id: string, data: Partial<MemoryFormData>): Promise<Memory> {
  return hrPut<Memory>(`/memories/${id}`, data)
}

/** 删除记忆 */
export async function deleteMemory(id: string): Promise<{ ok: boolean }> {
  return hrDelete<{ ok: boolean }>(`/memories/${id}`)
}

/** 搜索记忆 */
export async function searchMemories(params: MemorySearchParams): Promise<MemorySearchResponse> {
  return hrPost<MemorySearchResponse>('/memories/search', params)
}

/** 获取记忆统计 */
export async function getMemoryStats(): Promise<MemoryStats> {
  return hrGet<MemoryStats>('/memories/stats')
}

/** 触发冷启动(7天记忆构建) */
export async function triggerMemoryBuild(): Promise<{ task_id: string; message: string }> {
  return hrPost<{ task_id: string; message: string }>('/memories/trigger-build')
}

/** 合并/去重记忆 */
export async function consolidateMemories(): Promise<{ merged_count: number; message: string }> {
  return hrPost<{ merged_count: number; message: string }>('/memories/consolidate')
}

/** 批量删除 */
export async function batchDeleteMemories(ids: string[]): Promise<{ ok: boolean }> {
  return hrPost<{ ok: boolean }>('/memories/batch-delete', { ids })
}

/** 批量标记过期 */
export async function batchExpireMemories(ids: string[]): Promise<{ ok: boolean }> {
  return hrPost<{ ok: boolean }>('/memories/batch-expire', { ids })
}

/** 批量合并 */
export async function batchMergeMemories(data: MergeRequest): Promise<Memory> {
  return hrPost<Memory>('/memories/batch-merge', data)
}
