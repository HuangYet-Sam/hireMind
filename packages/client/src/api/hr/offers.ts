import { hrGet, hrPost, hrPatch, hrDelete } from './client'
import type { PaginatedResponse } from './client'

export interface Offer {
  id: string
  candidate_id: string
  position_id: string | null
  status: string
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
}

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
 * NOTE: Backend OfferUpdate only applies to draft-status offers.
 * If the backend adds a reject flow (e.g. status → 'rejected' + response_note),
 * update this to send { status: 'rejected', response_note: comment }.
 */
export async function rejectOffer(id: string, comment?: string): Promise<Offer> {
  return await hrPatch<Offer>(`/offers/${id}`, {
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
}): Promise<unknown> {
  return hrPost('/offers/ai/salary-recommendation', payload)
}
