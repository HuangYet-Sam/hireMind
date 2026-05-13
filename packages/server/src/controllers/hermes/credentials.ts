import type { Context } from 'koa'
import { readFileSync } from 'fs'
import { join } from 'path'
import { getActiveProfileDir } from '../../services/hermes/hermes-profile'
import { logger } from '../../services/logger'

interface CredentialEntry {
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

export async function listPool(ctx: Context) {
  const authPath = join(getActiveProfileDir(), 'auth.json')
  try {
    const raw = readFileSync(authPath, 'utf-8')
    const auth = JSON.parse(raw)
    const pool = auth.credential_pool || {}

    // Sanitize: strip sensitive values, only expose metadata
    const result: Record<string, CredentialEntry[]> = {}
    for (const [provider, entries] of Object.entries(pool as Record<string, any[]>)) {
      if (!Array.isArray(entries)) continue
      result[provider] = entries.map(e => ({
        id: String(e.id || ''),
        label: String(e.label || ''),
        auth_type: String(e.auth_type || ''),
        priority: Number(e.priority) || 0,
        last_status: e.last_status ? String(e.last_status) : null,
        last_error_code: e.last_error_code ? String(e.last_error_code) : null,
        last_error_message: e.last_error_message ? String(e.last_error_message) : null,
        request_count: Number(e.request_count) || 0,
        has_key: !!(e.access_token || e.api_key),
      }))
    }

    ctx.body = { credential_pool: result }
  } catch (err: any) {
    logger.debug(err, 'Failed to read credential pool, returning empty')
    ctx.body = { credential_pool: {} }
  }
}
