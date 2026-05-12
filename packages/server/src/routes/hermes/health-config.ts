import Router from '@koa/router'
import * as ctrl from '../../controllers/hermes/health-config'

export const healthConfigRoutes = new Router()
healthConfigRoutes.get('/api/hermes/config/health', ctrl.check)
