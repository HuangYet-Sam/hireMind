import { hrGet, hrPost, hrPatch, hrDelete } from './client'
import type { PaginatedResponse } from './client'

// ─── Types ──────────────────────────────────────────────

export interface Offer {
  id: string
  candidate_id: string
  candidate_name?: string
  position_id: string
  position_title?: string
  status: 'draft' | 'pending_approval' | 'approved' | 'sent' | 'accepted' | 'rejected' | 'withdrawn' | 'expired'
  salary: number
  salary_currency: string
  bonus: number | null
  equity: string | null
  start_date: string
  contract_type: 'permanent' | 'contract' | 'intern'
  contract_duration_months: number | null
  location: string
  benefits_summary: string | null
  notes: string
  approved_by: string | null
  approved_at: string | null
  sent_at: string | null
  responded_at: string | null
  expiry_date: string | null
  approval_chain: ApprovalStep[]
  ai_risk_assessment: string | null
  created_by: string
  created_at: string
  updated_at: string
}

export interface ApprovalStep {
  step: number
  role: string
  user_id: string | null
  user_name: string | null
  status: 'pending' | 'approved' | 'rejected'
  comment: string | null
  acted_at: string | null
}

export interface CreateOfferRequest {
  candidate_id: string
  position_id: string
  salary: number
  salary_currency?: string
  bonus?: number
  equity?: string
  start_date: string
  contract_type?: Offer['contract_type']
  contract_duration_months?: number
  location?: string
  benefits_summary?: string
  notes?: string
  expiry_date?: string
}

export interface UpdateOfferRequest {
  salary?: number
  bonus?: number | null
  equity?: string | null
  start_date?: string
  contract_type?: Offer['contract_type']
  location?: string
  benefits_summary?: string | null
  notes?: string
  status?: Offer['status']
}

export interface OfferListParams {
  page?: number
  page_size?: number
  status?: Offer['status']
  candidate_id?: string
  position_id?: string
}

// ─── API Functions ──────────────────────────────────────

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

export async function submitOfferForApproval(id: string): Promise<Offer> {
  return hrPost<Offer>(`/offers/${id}/submit`)
}

export async function approveOffer(id: string, comment?: string): Promise<Offer> {
  return hrPost<Offer>(`/offers/${id}/approve`, { comment })
}

export async function rejectOffer(id: string, comment?: string): Promise<Offer> {
  return hrPost<Offer>(`/offers/${id}/reject`, { comment })
}

export async function sendOffer(id: string): Promise<Offer> {
  return hrPost<Offer>(`/offers/${id}/send`)
}

export async function withdrawOffer(id: string): Promise<Offer> {
  return hrPost<Offer>(`/offers/${id}/withdraw`)
}
