import Router from '@koa/router'
import * as ctrl from '../../controllers/hermes/terminal-ai'

export const terminalAiRoutes = new Router()

terminalAiRoutes.get('/api/hermes/terminal/config', ctrl.getTerminalConfig)
terminalAiRoutes.get('/api/hermes/terminal/ai-ops', ctrl.getRecentTerminalOps)
