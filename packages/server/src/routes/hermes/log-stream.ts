import Router from '@koa/router'
import * as ctrl from '../../controllers/hermes/log-stream'

export const logStreamRoutes = new Router()

logStreamRoutes.get('/api/hermes/logs/stream', ctrl.stream)
