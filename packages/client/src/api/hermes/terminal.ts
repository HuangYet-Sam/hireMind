import { request } from '../client'

export interface TerminalConfig {
  cwd: string
}

export interface AiOperation {
  session_id: string
  session_title: string | null
  tool_name: string
  content: string
  timestamp: number
}

export async function fetchTerminalConfig(): Promise<TerminalConfig> {
  return request<TerminalConfig>('/api/hermes/terminal/config')
}

export async function fetchRecentAiOps(limit?: number): Promise<AiOperation[]> {
  const params = limit ? `?limit=${limit}` : ''
  const res = await request<{ operations: AiOperation[] }>(`/api/hermes/terminal/ai-ops${params}`)
  return res.operations
}
