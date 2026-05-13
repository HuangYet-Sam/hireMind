import type { Context } from 'koa'
import { existsSync, statSync, openSync, readSync, closeSync } from 'fs'
import { join } from 'path'
import { homedir } from 'os'

const WEBUI_LOG_FILE = join(homedir(), '.hermes-web-ui', 'logs', 'server.log')

export function stream(ctx: Context) {
  const logName = (ctx.query.name as string) || 'webui'

  // Only support streaming the webui log for now (agent logs require CLI)
  if (logName !== 'webui') {
    ctx.status = 400
    ctx.body = { error: 'Only webui log streaming is supported' }
    return
  }

  if (!existsSync(WEBUI_LOG_FILE)) {
    ctx.status = 404
    ctx.body = { error: 'Log file not found' }
    return
  }

  ctx.set('Content-Type', 'text/event-stream')
  ctx.set('Cache-Control', 'no-cache')
  ctx.set('Connection', 'keep-alive')
  ctx.set('X-Accel-Buffering', 'no')

  const res = ctx.res

  // Start from end of file
  let lastSize = statSync(WEBUI_LOG_FILE).size
  let fd: number | null = null
  let watcher: ReturnType<typeof import('fs').watchFile> | null = null

  try {
    fd = openSync(WEBUI_LOG_FILE, 'r')

    // Send initial recent lines (last 20)
    const buf = Buffer.alloc(Math.min(lastSize, 8192))
    const bytesRead = readSync(fd, buf, 0, buf.length, Math.max(0, lastSize - 8192))
    const recentContent = buf.toString('utf-8', 0, bytesRead)
    const recentLines = recentContent.split('\n').filter(l => l.trim()).slice(-20)
    for (const line of recentLines) {
      res.write(`data: ${JSON.stringify({ line })}\n\n`)
    }

    // Watch for changes
    const { watchFile, unwatchFile } = require('fs') as typeof import('fs')
    watchFile(WEBUI_LOG_FILE, { interval: 1000 }, (curr: any) => {
      if (!res.writable) {
        unwatchFile(WEBUI_LOG_FILE)
        return
      }

      if (curr.size > lastSize && fd !== null) {
        const deltaSize = curr.size - lastSize
        const deltaBuf = Buffer.alloc(deltaSize)
        const read = readSync(fd, deltaBuf, 0, deltaSize, lastSize)
        const newContent = deltaBuf.toString('utf-8', 0, read)
        const newLines = newContent.split('\n').filter((l: string) => l.trim())
        for (const line of newLines) {
          res.write(`data: ${JSON.stringify({ line })}\n\n`)
        }
        lastSize = curr.size
      } else if (curr.size < lastSize) {
        // File was truncated/rotated
        lastSize = 0
      }
    })

    // Cleanup on close
    res.on('close', () => {
      unwatchFile(WEBUI_LOG_FILE)
      if (fd !== null) {
        closeSync(fd)
        fd = null
      }
    })
  } catch (err: any) {
    if (fd !== null) closeSync(fd)
    if (!res.headersSent) {
      ctx.status = 500
      ctx.body = { error: err.message }
    }
  }
}
