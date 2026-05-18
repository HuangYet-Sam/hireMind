/**
 * AI Insights API — Context Bar per-entity insights (PRD §10.1b)
 *
 * GET /insights?entity_type=X&entity_id=Y&tab=Z
 */
import { hrGet } from './client'

export type EntityType = 'position' | 'candidate' | 'resume' | 'interview' | 'offer'

export interface InsightData {
  summary: string
  details?: string
  confidence?: number
  suggestions?: string[]
  actions?: InsightAction[]
}

export interface InsightAction {
  label: string
  link?: string
  capability?: string
}

export interface InsightsResponse {
  entity_type: EntityType
  entity_id: string
  tab: string
  insight: InsightData | null
  cached_at?: string
}

export interface InsightsParams {
  entity_type: EntityType
  entity_id: string
  tab?: string
}

export async function getEntityInsights(params: InsightsParams): Promise<InsightsResponse> {
  return hrGet<InsightsResponse>('/insights', params as Record<string, string>)
}
