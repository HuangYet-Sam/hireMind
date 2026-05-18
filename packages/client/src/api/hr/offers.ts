import { hrGet, hrPost, hrPatch, hrDelete } from './client'
import type { PaginatedResponse } from './client'

export interface Offer {
  id: string
  candidate_id: string
  candidate_name?: string
  position_id: string | null
  position_title?: string
  department?: string
  status: string
  urgency?: 'low' | 'normal' | 'high' | 'critical'
  base_salary: number | null
  annual_bonus_months: number | null
  sign_on_bonus: number | null
  equity: string | null
  benefits_summary: string | null
  proposed_start_date: string | null
  probation_months: number | null
  work_location: string | null
  employment_type: string | null
  notes: string | null
  offer_letter_url: string | null
  sent_at: string | null
  responded_at: string | null
  response_note: string | null
  expiry_date: string | null
  created_by: string | null
  created_at: string
  updated_at: string
  approval_progress?: number
  match_score?: number
  interview_scores?: InterviewScore[]
}

export interface InterviewScore {
  round: number
  type: string
  score: number
  summary?: string
}

export interface CreateOfferRequest {
  candidate_id: string
  position_id?: string | null
  base_salary?: number | null
  annual_bonus_months?: number | null
  sign_on_bonus?: number | null
  equity?: string | null
  benefits_summary?: string | null
  proposed_start_date?: string | null
  probation_months?: number | null
  work_location?: string | null
  employment_type?: string | null
  notes?: string | null
  expiry_date?: string | null
  template_id?: string | null
}

export interface UpdateOfferRequest {
  base_salary?: number | null
  annual_bonus_months?: number | null
  sign_on_bonus?: number | null
  equity?: string | null
  benefits_summary?: string | null
  proposed_start_date?: string | null
  probation_months?: number | null
  work_location?: string | null
  employment_type?: string | null
  notes?: string | null
  expiry_date?: string | null
}

export interface OfferListParams {
  page?: number
  page_size?: number
  candidate_id?: string
  position_id?: string
  status?: string
  department?: string
  urgency?: string
  date_from?: string
  date_to?: string
}

/** AI 薪资建议 */
export interface SalarySuggestion {
  base_salary: number
  annual_bonus_months: number
  sign_on_bonus: number
  equity: string
  total_compensation: number
  confidence: number
  reasoning: string
  market_percentile: number
}

/** 薪资对标 */
export interface CompensationBenchmark {
  internal_p50: number
  internal_p75: number
  internal_p90: number
  market_p50: number
  market_p75: number
  current_offer: number
  fairness_score: number
  position_title: string
  department: string
  currency: string
}

/** 审批节点 */
export interface ApprovalNode {
  id: string
  step: number
  label: string
  approver_id: string
  approver_name: string
  approver_avatar?: string
  status: 'pending' | 'approved' | 'rejected' | 'waiting'
  comment?: string
  acted_at?: string
}

/** 审批历史 */
export interface ApprovalHistory {
  id: string
  action: 'approved' | 'rejected' | 'withdrawn' | 'submitted' | 'sent' | 'countered' | 'status_changed'
  actor_name: string
  comment?: string
  created_at: string
  from_status?: string
  to_status?: string
}

/** Offer 模板 */
export interface OfferTemplate {
  id: string
  name: string
  description?: string
  content: string
  is_default: boolean
  created_at: string
}

/** 反报价请求 */
export interface CounterOfferRequest {
  expected_base_salary?: number
  expected_bonus_months?: number
  expected_equity?: string
  expected_sign_on_bonus?: number
  reason: string
}

/** 谈判建议 */
export interface NegotiationAdvice {
  strategy: string
  max_budget: number
  recommended_counter: number
  key_points: string[]
  risk_level: 'low' | 'medium' | 'high'
}

// ─── 基础 CRUD ────────────────────────────────────────────────

export async function listOffers(params?: OfferListParams): Promise<PaginatedResponse<Offer>> {
  return hrGet<PaginatedResponse<Offer>>('/offers', params as Record<string, string | number>)
}

export async function getOffer(id: string): Promise<Offer> {
  return hrGet<Offer>(`/offers/${id}`)
}

export async function createOffer(data: CreateOfferRequest): Promise<Offer> {
  return hrPost<Offer>('/offers', data)
}

export async function updateOffer(id: string, data: UpdateOfferRequest): Promise<Offer> {
  return hrPatch<Offer>(`/offers/${id}`, data)
}

export async function approveOffer(id: string, comment?: string): Promise<Offer> {
  return hrPost<Offer>(`/offers/${id}/approve`, { comment })
}

/**
 * Reject an offer.
 * Backend has no dedicated /reject endpoint.
 * We PATCH the offer with notes containing the rejection reason.
 */
export async function rejectOffer(id: string, comment?: string): Promise<Offer> {
  return hrPatch<Offer>(`/offers/${id}`, {
    notes: comment ?? 'Rejected',
  })
}

export async function sendOffer(id: string): Promise<Offer> {
  return hrPost<Offer>(`/offers/${id}/send`)
}

export async function withdrawOffer(id: string, reason?: string): Promise<void> {
  const params = reason ? `?reason=${encodeURIComponent(reason)}` : ''
  return hrDelete(`/offers/${id}${params}`)
}

export async function generateSalaryRecommendation(payload: {
  candidate: Record<string, unknown>
  position: Record<string, unknown>
  market_data?: Record<string, unknown>
}): Promise<SalarySuggestion> {
  return hrPost('/offers/ai/salary-recommendation', payload)
}

// ─── M6 新增 API ──────────────────────────────────────────────

/** AI 生成 Offer（含薪资建议） */
export async function generateOffer(positionId: string, candidateId: string): Promise<{
  offer: Partial<CreateOfferRequest>
  suggestion: SalarySuggestion
}> {
  return hrPost('/offers/ai/generate', { position_id: positionId, candidate_id: candidateId })
}

/** 审批 Offer（含审批数据） */
export async function approveOfferWithData(id: string, data: { comment?: string; approved: boolean }): Promise<Offer> {
  return hrPost<Offer>(`/offers/${id}/approve`, data)
}

/** 拒绝 Offer */
export async function rejectOfferWithData(id: string, data: { reason: string }): Promise<Offer> {
  return hrPost<Offer>(`/offers/${id}/reject`, data)
}

/** 撤回 Offer */
export async function withdrawOfferWithData(id: string, data?: { reason?: string }): Promise<void> {
  return hrPost(`/offers/${id}/withdraw`, data)
}

/** 反报价 */
export async function counterOffer(id: string, data: CounterOfferRequest): Promise<Offer> {
  return hrPost<Offer>(`/offers/${id}/counter`, data)
}

/** 获取薪资对标数据 */
export async function getCompensationBenchmark(offerId: string): Promise<CompensationBenchmark> {
  return hrGet<CompensationBenchmark>(`/offers/${offerId}/benchmark`)
}

/** 获取谈判建议 */
export async function getNegotiationAdvice(offerId: string): Promise<NegotiationAdvice> {
  return hrGet<NegotiationAdvice>(`/offers/${offerId}/negotiation-advice`)
}

/** 获取审批历史 */
export async function getApprovalHistory(offerId: string): Promise<ApprovalHistory[]> {
  return hrGet<ApprovalHistory[]>(`/offers/${offerId}/approval-history`)
}

/** 获取 Offer 模板列表 */
export async function getOfferTemplates(): Promise<OfferTemplate[]> {
  return hrGet<OfferTemplate[]>('/offers/templates')
}

/** 创建 Offer 模板 */
export async function createOfferTemplate(data: {
  name: string
  description?: string
  content: string
  is_default?: boolean
}): Promise<OfferTemplate> {
  return hrPost<OfferTemplate>('/offers/templates', data)
}

/** 渲染 Offer 信 */
export async function renderOfferLetter(offerId: string, templateId: string): Promise<{ url: string; html: string }> {
  return hrPost('/offers/render-letter', { offer_id: offerId, template_id: templateId })
}
