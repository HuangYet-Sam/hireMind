import { getActiveProfileDir } from '../../services/hermes/hermes-profile'

const SQLITE_AVAILABLE = (() => {
  const [major, minor] = process.versions.node.split('.').map(Number)
  return major > 22 || (major === 22 && minor >= 5)
})()

export interface KanbanTask {
  id: string
  title: string
  body: string | null
  assignee: string | null
  status: string
  tenant: string | null
  priority: number
  workspace_kind: string | null
  workspace_path: string | null
  created_by: string | null
  created_at: string | null
  started_at: string | null
  completed_at: string | null
  result: string | null
  current_run_id: string | null
}

export interface KanbanRun {
  id: string
  profile: string | null
  status: string
  outcome: string | null
  summary: string | null
  error: string | null
  started_at: string | null
  ended_at: string | null
}

export interface KanbanComment {
  id: number
  task_id: string
  author: string | null
  body: string
  created_at: string | null
}

export interface KanbanTaskDetail extends KanbanTask {
  comments: KanbanComment[]
  runs: KanbanRun[]
  parent_ids: string[]
  child_ids: string[]
}

function kanbanDbPath(): string {
  return `${getActiveProfileDir()}/kanban.db`
}

function mapTask(row: Record<string, unknown>): KanbanTask {
  return {
    id: String(row.id || ''),
    title: String(row.title || ''),
    body: row.body ? String(row.body) : null,
    assignee: row.assignee ? String(row.assignee) : null,
    status: String(row.status || 'todo'),
    tenant: row.tenant ? String(row.tenant) : null,
    priority: Number(row.priority) || 0,
    workspace_kind: row.workspace_kind ? String(row.workspace_kind) : null,
    workspace_path: row.workspace_path ? String(row.workspace_path) : null,
    created_by: row.created_by ? String(row.created_by) : null,
    created_at: row.created_at ? String(row.created_at) : null,
    started_at: row.started_at ? String(row.started_at) : null,
    completed_at: row.completed_at ? String(row.completed_at) : null,
    result: row.result ? String(row.result) : null,
    current_run_id: row.current_run_id ? String(row.current_run_id) : null,
  }
}

export function listKanbanTasks(status?: string, assignee?: string): KanbanTask[] {
  if (!SQLITE_AVAILABLE) return []

  let db: any
  try {
    const { DatabaseSync } = require('node:sqlite')
    db = new DatabaseSync(kanbanDbPath(), { readOnly: true })
    db.exec('PRAGMA journal_mode=WAL')

    let sql = 'SELECT * FROM tasks'
    const conditions: string[] = []
    if (status) conditions.push(`status = '${status.replace(/'/g, "''")}'`)
    if (assignee) conditions.push(`assignee = '${assignee.replace(/'/g, "''")}'`)
    if (conditions.length > 0) sql += ' WHERE ' + conditions.join(' AND ')
    sql += ' ORDER BY priority DESC, created_at DESC'

    const stmt = db.prepare(sql)
    const rows = stmt.all() as Record<string, unknown>[]
    return rows.map(mapTask)
  } catch {
    return []
  } finally {
    db?.close()
  }
}

export function getKanbanTaskDetail(taskId: string): KanbanTaskDetail | null {
  if (!SQLITE_AVAILABLE) return null

  let db: any
  try {
    const { DatabaseSync } = require('node:sqlite')
    db = new DatabaseSync(kanbanDbPath(), { readOnly: true })
    db.exec('PRAGMA journal_mode=WAL')

    // Get task
    const taskStmt = db.prepare('SELECT * FROM tasks WHERE id = ?')
    const taskRow = taskStmt.get(taskId) as Record<string, unknown> | undefined
    if (!taskRow) return null
    const task = mapTask(taskRow)

    // Get comments
    const commentsStmt = db.prepare('SELECT * FROM task_comments WHERE task_id = ? ORDER BY created_at ASC')
    const commentRows = (commentsStmt.all(taskId) || []) as Record<string, unknown>[]
    const comments: KanbanComment[] = commentRows.map(r => ({
      id: Number(r.id),
      task_id: String(r.task_id),
      author: r.author ? String(r.author) : null,
      body: String(r.body || ''),
      created_at: r.created_at ? String(r.created_at) : null,
    }))

    // Get runs
    const runsStmt = db.prepare('SELECT * FROM task_runs WHERE task_id = ? ORDER BY started_at DESC')
    const runRows = (runsStmt.all(taskId) || []) as Record<string, unknown>[]
    const runs: KanbanRun[] = runRows.map(r => ({
      id: String(r.id),
      profile: r.profile ? String(r.profile) : null,
      status: String(r.status || 'pending'),
      outcome: r.outcome ? String(r.outcome) : null,
      summary: r.summary ? String(r.summary) : null,
      error: r.error ? String(r.error) : null,
      started_at: r.started_at ? String(r.started_at) : null,
      ended_at: r.ended_at ? String(r.ended_at) : null,
    }))

    // Get parent-child links
    const parentStmt = db.prepare('SELECT parent_id FROM task_links WHERE child_id = ?')
    const parentRows = (parentStmt.all(taskId) || []) as Record<string, unknown>[]
    const parentIds = parentRows.map(r => String(r.parent_id))

    const childStmt = db.prepare('SELECT child_id FROM task_links WHERE parent_id = ?')
    const childRows = (childStmt.all(taskId) || []) as Record<string, unknown>[]
    const childIds = childRows.map(r => String(r.child_id))

    return { ...task, comments, runs, parent_ids: parentIds, child_ids: childIds }
  } catch {
    return null
  } finally {
    db?.close()
  }
}
