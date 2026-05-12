import Router from '@koa/router'
import * as ctrl from '../../controllers/hermes/credentials'

export const credentialRoutes = new Router()

credentialRoutes.get('/api/hermes/credentials/pool', ctrl.listPool)
