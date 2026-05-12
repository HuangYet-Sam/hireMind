import type { Context } from 'koa'
import { getActiveProfileDir } from '../../services/hermes/hermes-profile'
import { getGatewayManagerInstance } from '../../services/gateway-bootstrap'
import type { GatewayStatus } from '../../services/hermes/gateway-manager'
import { getGroupChatServer } from '../../routes/hermes/group-chat'

const SQLITE_AVAILABLE = (() => {
  const [major, minor] = process.versions.node.split('.').map(Number)
  return major > 22 || (major === 22 && minor >= 5)
})()

// ─── Response Types ──────────────────────────────────────────

interface AgentNode {
  session_id: string
  model: string
  source: string
  status: string
  title: string | null
  started_at: number | null
  children: AgentNode[]
}

interface GatewayInfo {
  profile: string
  running: boolean
  port: number
  host: string
  pid?: number
}

interface GroupChatAgentInfo {
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

interface JobAgentInfo {
  jobId: string
  name: string
  scheduleDisplay: string
  enabled: boolean
  lastRunAt: string | null
  lastStatus: string | null
  lastOutput: string | null
  nextRunAt: string | null
}

interface AgentsDashboardResponse {
  gateways: GatewayInfo[]
  groupChatAgents: GroupChatAgentInfo[]
  jobs: JobAgentInfo[]
  sqliteAvailable: boolean
  delegationTree: AgentNode[]
  activeAgents: number
  platforms: Record<string, string>
}

// ─── Data Fetching ────────────────────────────────────────────

async function fetchHealthDetailed(): Promise<{ active_agents: number; platforms: Record<string, string> }> {
  try {
    const gm = getGatewayManagerInstance()
    if (!gm) return { active_agents: 0, platforms: {} }
    const upstream = gm.getUpstream()
    const apiKey = gm.getApiKey()
    const url = `${upstream}/health/detailed`
    const res = await fetch(url, {
      headers: apiKey ? { Authorization: `Bearer ${apiKey}` } : {},
      signal: AbortSignal.timeout(5000),
    })
    if (!res.ok) return { active_agents: 0, platforms: {} }
    const data = await res.json()
    return {
      active_agents: data.active_agents || 0,
      platforms: data.platforms || {},
    }
  } catch {
    return { active_agents: 0, platforms: {} }
  }
}

async function fetchGateways(): Promise<GatewayInfo[]> {
  try {
    const gm = getGatewayManagerInstance()
    if (!gm) return []
    const statuses = await gm.listAll()
    return statuses.map((s: GatewayStatus) => ({
      profile: s.profile,
      running: s.running,
      port: s.port,
      host: s.host,
      pid: s.pid,
    }))
  } catch {
    return []
  }
}

function fetchGroupChatAgents(): GroupChatAgentInfo[] {
  try {
    const chatServer = getGroupChatServer()
    if (!chatServer) return []

    const storage = chatServer.getStorage()
    const rooms = storage.getAllRooms()
    const agents: GroupChatAgentInfo[] = []

    for (const room of rooms) {
      const roomAgents = storage.getRoomAgents(room.id)
      const connectedAgents = chatServer.agentClients.getAgents(room.id)
      const connectedIds = new Set(connectedAgents.map(a => a.agentId))

      // Get recent messages for last-message lookup
      const messages = storage.getMessages(room.id, 50)

      for (const agent of roomAgents) {
        // Find the most recent message from this agent by matching agent name
        const lastMsg = messages
          .filter((m: any) => m.senderName === agent.name)
          .sort((a: any, b: any) => b.timestamp - a.timestamp)[0]

        agents.push({
          roomId: room.id,
          roomName: room.name,
          agentId: agent.id,
          name: agent.name,
          profile: agent.profile,
          description: agent.description,
          connected: connectedIds.has(agent.agentId) || connectedAgents.some(a => a.name === agent.name),
          lastMessage: lastMsg ? truncate(lastMsg.content, 200) : null,
          lastMessageTime: lastMsg ? lastMsg.timestamp : null,
        })
      }
    }

    return agents
  } catch {
    return []
  }
}

async function fetchJobs(): Promise<JobAgentInfo[]> {
  try {
    const gm = getGatewayManagerInstance()
    if (!gm) return []
    const upstream = gm.getUpstream()
    const apiKey = gm.getApiKey()
    if (!upstream) return []

    const res = await fetch(`${upstream}/api/jobs?include_disabled=true`, {
      headers: apiKey ? { Authorization: `Bearer ${apiKey}` } : {},
      signal: AbortSignal.timeout(5000),
    })
    if (!res.ok) return []

    const data = await res.json() as { jobs: any[] }
    return (data.jobs || []).map((job: any) => ({
      jobId: job.job_id || job.id,
      name: job.name,
      scheduleDisplay: job.schedule_display || job.schedule || '',
      enabled: job.enabled !== false,
      lastRunAt: job.last_run_at || null,
      lastStatus: job.last_status || null,
      lastOutput: null,
      nextRunAt: job.next_run_at || null,
    }))
  } catch {
    return []
  }
}

function truncate(str: string, max: number): string {
  if (!str) return str
  return str.length > max ? str.slice(0, max) + '...' : str
}

// ─── Delegation Tree (existing) ──────────────────────────────

interface SessionRow {
  id: string
  source: string
  model: string
  title: string | null
  started_at: number
  ended_at: number | null
  end_reason: string | null
  parent_session_id: string | null
}

function getDelegationTree(): AgentNode[] {
  if (!SQLITE_AVAILABLE) return []

  let db: any
  try {
    const { DatabaseSync } = require('node:sqlite')
    const dbPath = `${getActiveProfileDir()}/state.db`
    db = new DatabaseSync(dbPath, { readOnly: true })

    const stmt = db.prepare(`
      SELECT s.id, s.source, s.model, s.title, s.started_at, s.ended_at, s.end_reason,
             si.parent_session_id
      FROM sessions s
      LEFT JOIN session_info si ON s.id = si.session_id
      WHERE si.parent_session_id IS NOT NULL
         OR s.id IN (SELECT DISTINCT si2.parent_session_id FROM session_info si2 WHERE si2.parent_session_id IS NOT NULL)
      ORDER BY s.started_at DESC
      LIMIT 100
    `)
    const rows = stmt.all() as Record<string, unknown>[]

    const sessions: SessionRow[] = rows.map(r => ({
      id: String(r.id),
      source: String(r.source || ''),
      model: String(r.model || ''),
      title: r.title ? String(r.title) : null,
      started_at: Number(r.started_at) || 0,
      ended_at: r.ended_at ? Number(r.ended_at) : null,
      end_reason: r.end_reason ? String(r.end_reason) : null,
      parent_session_id: r.parent_session_id ? String(r.parent_session_id) : null,
    }))

    const byId = new Map<string, SessionRow & { children: AgentNode[] }>()
    for (const s of sessions) {
      byId.set(s.id, { ...s, children: [] })
    }

    const roots: (SessionRow & { children: AgentNode[] })[] = []
    for (const s of byId.values()) {
      if (s.parent_session_id && byId.has(s.parent_session_id)) {
        byId.get(s.parent_session_id)!.children.push(toNode(s))
      } else {
        roots.push(s)
      }
    }

    return roots.map(toNode)
  } catch {
    return []
  } finally {
    db?.close()
  }
}

function toNode(s: SessionRow & { children: AgentNode[] }): AgentNode {
  return {
    session_id: s.id,
    model: s.model,
    source: s.source,
    status: s.ended_at ? (s.end_reason || 'completed') : 'running',
    title: s.title,
    started_at: s.started_at || null,
    children: s.children,
  }
}

// ─── Main Handler ─────────────────────────────────────────────

export async function tree(ctx: Context) {
  const [health, delegationTree, gateways, jobs] = await Promise.all([
    fetchHealthDetailed(),
    Promise.resolve(getDelegationTree()),
    fetchGateways(),
    fetchJobs(),
  ])

  const groupChatAgents = fetchGroupChatAgents()

  const response: AgentsDashboardResponse = {
    gateways,
    groupChatAgents,
    jobs,
    sqliteAvailable: SQLITE_AVAILABLE,
    delegationTree,
    activeAgents: health.active_agents,
    platforms: health.platforms,
  }

  ctx.body = response
}
