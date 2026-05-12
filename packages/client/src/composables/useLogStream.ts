import { ref, onUnmounted } from 'vue'
import { getBaseUrlValue, getApiKey } from '@/api/client'

export interface StreamLogLine {
  line: string
}

export function useLogStream() {
  const connected = ref(false)
  const lines = ref<string[]>([])
  const error = ref<string | null>(null)
  let source: EventSource | null = null

  function start() {
    stop()
    lines.value = []
    error.value = null

    const baseUrl = getBaseUrlValue()
    const token = getApiKey()
    const url = `${baseUrl}/api/hermes/logs/stream?name=webui${token ? `&token=${token}` : ''}`

    source = new EventSource(url)

    source.onopen = () => {
      connected.value = true
    }

    source.onmessage = (e) => {
      try {
        const data: StreamLogLine = JSON.parse(e.data)
        lines.value.push(data.line)
        // Keep buffer bounded
        if (lines.value.length > 500) {
          lines.value = lines.value.slice(-400)
        }
      } catch {
        // ignore malformed data
      }
    }

    source.onerror = () => {
      connected.value = false
      source?.close()
      source = null
      error.value = 'Connection lost'
    }
  }

  function stop() {
    if (source) {
      source.close()
      source = null
    }
    connected.value = false
  }

  function clear() {
    lines.value = []
  }

  onUnmounted(() => {
    stop()
  })

  return { connected, lines, error, start, stop, clear }
}
