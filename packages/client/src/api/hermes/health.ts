import { request } from '../client'

export interface PlatformInfo {
  state: string
  error_code: string | null
  error_message: string | null
  updated_at: string
}

export interface DetailedHealthResponse {
  status: string
  platform: string
  gateway_state: string
  platforms: Record<string, PlatformInfo>
  active_agents: number
  pid: number
  exit_reason: string | null
  updated_at: string
}

export async function fetchDetailedHealth(profile?: string): Promise<DetailedHealthResponse> {
  const query = profile ? `?profile=${encodeURIComponent(profile)}` : ''
  return request<DetailedHealthResponse>(`/api/hermes/health/detailed${query}`)
}
