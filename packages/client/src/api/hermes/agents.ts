import { request } from '../client'

export interface AgentNode {
  session_id: string
  model: string
  source: string
  status: string
  title: string | null
  started_at: number | null
  children: AgentNode[]
}

export interface GatewayInfo {
  profile: string
  running: boolean
  port: number
  host: string
  pid?: number
}

export interface GroupChatAgentInfo {
  roomId: string
  roomName: string
  agentId: string
  name: string
  profile: string
  description: string
  connected: boolean
  lastMessage: string | null
  lastMessageTime: number | null
}

export interface JobAgentInfo {
  jobId: string
  name: string
  scheduleDisplay: string
  enabled: boolean
  lastRunAt: string | null
  lastStatus: string | null
  lastOutput: string | null
  nextRunAt: string | null
}

export interface AgentsDashboardResponse {
  gateways: GatewayInfo[]
  groupChatAgents: GroupChatAgentInfo[]
  jobs: JobAgentInfo[]
  sqliteAvailable: boolean
  delegationTree: AgentNode[]
  activeAgents: number
  platforms: Record<string, string>
}

/** @deprecated Use AgentsDashboardResponse */
export type AgentTreeResponse = AgentsDashboardResponse

export async function fetchAgentTree(): Promise<AgentsDashboardResponse> {
  return request<AgentsDashboardResponse>('/api/hermes/agents/tree')
}
