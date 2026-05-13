import type { Context } from 'koa'
import { readFile } from 'fs/promises'
import YAML from 'js-yaml'
import { getActiveConfigPath } from '../../services/hermes/hermes-profile'
import { getActiveProfileDir } from '../../services/hermes/hermes-profile'

const SQLITE_AVAILABLE = (() => {
  const [major, minor] = process.versions.node.split('.').map(Number)
  return major > 22 || (major === 22 && minor >= 5)
})()

interface TerminalToolCall {
  session_id: string
  session_title: string | null
  tool_name: string
  content: string
  timestamp: number
}

export async function getTerminalConfig(ctx: Context) {
  try {
    const raw = await readFile(getActiveConfigPath(), 'utf-8')
    const config = (YAML.load(raw, { schema: YAML.JSON_SCHEMA }) as Record<string, any>) || {}
    const terminalCwd = config?.terminal?.cwd || config?.agent?.cwd || ''
    ctx.body = { cwd: terminalCwd }
  } catch (err: any) {
    ctx.body = { cwd: '' }
  }
}

export async function getRecentTerminalOps(ctx: Context) {
  if (!SQLITE_AVAILABLE) {
    ctx.body = { operations: [] }
    return
  }

  let db: any
  try {
    const { DatabaseSync } = require('node:sqlite')
    const dbPath = `${getActiveProfileDir()}/state.db`
    db = new DatabaseSync(dbPath, { open: true, readOnly: true })

    const limit = Math.min(Number(ctx.query.limit) || 20, 100)

    // Find recent messages with tool_name related to terminal/shell operations
    const rows = db.prepare(`
      SELECT
        m.session_id,
        m.tool_name,
        m.content,
        m.timestamp,
        COALESCE(s.title, '') AS session_title
      FROM messages m
      JOIN sessions s ON s.id = m.session_id
      WHERE m.role = 'tool'
        AND (
          m.tool_name LIKE '%terminal%'
          OR m.tool_name LIKE '%shell%'
          OR m.tool_name LIKE '%exec%'
          OR m.tool_name LIKE '%bash%'
          OR m.tool_name LIKE '%command%'
        )
      ORDER BY m.timestamp DESC
      LIMIT ?
    `).all(limit) as Record<string, unknown>[]

    const operations: TerminalToolCall[] = rows.map(r => ({
      session_id: String(r.session_id || ''),
      session_title: r.session_title ? String(r.session_title) : null,
      tool_name: String(r.tool_name || ''),
      content: String(r.content || '').slice(0, 500),
      timestamp: Number(r.timestamp) || 0,
    }))

    ctx.body = { operations }
  } catch {
    ctx.body = { operations: [] }
  } finally {
    db?.close()
  }
}
