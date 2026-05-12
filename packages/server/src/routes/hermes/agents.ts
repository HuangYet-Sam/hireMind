import Router from '@koa/router'
import type { Context } from 'koa'
import * as ctrl from '../../controllers/hermes/agents'
import { getGatewayManagerInstance } from '../../services/gateway-bootstrap'

export const agentRoutes = new Router()

function emptyHealthResponse() {
  return { status: 'ok', platform: 'api', gateway_state: '', platforms: {}, active_agents: 0, pid: null, exit_reason: null, updated_at: Date.now() }
}

agentRoutes.get('/api/hermes/agents/tree', ctrl.tree)

agentRoutes.get('/api/hermes/health/detailed', async (ctx: Context) => {
  try {
    const gm = getGatewayManagerInstance()
    if (!gm) { ctx.body = emptyHealthResponse(); return }
    const upstream = gm.getUpstream()
    const apiKey = gm.getApiKey()
    const res = await fetch(`${upstream}/health/detailed`, {
      headers: apiKey ? { Authorization: `Bearer ${apiKey}` } : {},
      signal: AbortSignal.timeout(5000),
    })
    ctx.body = res.ok ? await res.json() : emptyHealthResponse()
  } catch {
    ctx.body = emptyHealthResponse()
  }
})
