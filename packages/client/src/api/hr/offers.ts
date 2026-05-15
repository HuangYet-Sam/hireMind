import { hrGet, hrPost, hrPatch, hrDelete } from './client'
import type { PaginatedResponse } from './client'

// ─── Types ──────────────────────────────────────────────

export interface Offer {
  id: string
  candidate_id: string
  position_id: string | null
  status: 'draft' | 'pending_approval' | 'approved' | 'sent' | 'accepted' | 'rejected' | 'withdrawn' | 'expired'
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
}

export interface CreateOfferRequest {
  candidate_id: string
  position_id?: string
  base_salary?: number
  annual_bonus_months?: number
  sign_on_bonus?: number
  equity?: string
  benefits_summary?: string
  proposed_start_date?: string
  probation_months?: number
  work_location?: string
  employment_type?: string
  notes?: string
  expiry_date?: string
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

export async function approveOffer(id: string, comment?: string): Promise<Offer> {
  return hrPost<Offer>(`/offers/${id}/approve`, { comment })
}

// TODO: backend not yet implemented
export async function rejectOffer(id: string, comment?: string): Promise<Offer> {
  return hrPost<Offer>(`/offers/${id}/reject`, { comment })
}

export async function sendOffer(id: string): Promise<Offer> {
  return hrPost<Offer>(`/offers/${id}/send`)
}

export async function withdrawOffer(id: string, reason?: string): Promise<void> {
  const params = reason ? `?reason=${encodeURIComponent(reason)}` : ''
  return hrDelete(`/offers/${id}${params}`)
}
