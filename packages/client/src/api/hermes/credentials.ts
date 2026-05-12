import { request } from '../client'

export interface CredentialEntry {
  id: string
  label: string
  auth_type: string
  priority: number
  last_status: string | null
  last_error_code: string | null
  last_error_message: string | null
  request_count: number
  has_key: boolean
}

export async function fetchCredentialPool(): Promise<Record<string, CredentialEntry[]>> {
  const res = await request<{ credential_pool: Record<string, CredentialEntry[]> }>('/api/hermes/credentials/pool')
  return res.credential_pool
}
