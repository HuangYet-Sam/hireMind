import { ref } from 'vue'
import { fetchConfigHealth, type SmartConfigItem } from '@/api/hermes/config'
import { fetchModels } from '@/api/hermes/chat'
import { fetchMemory } from '@/api/hermes/skills'

export function useConfigHealth() {
  const items = ref<SmartConfigItem[]>([])
  const loading = ref(false)

  async function check(): Promise<SmartConfigItem[]> {
    loading.value = true
    try {
      const results: SmartConfigItem[] = []

      // 1. Backend cross-file conflict detection
      try {
        const health = await fetchConfigHealth()
        for (const item of health.items) {
          results.push({ ...item, source: 'health' as const, status: 'active' as const })
        }
      } catch {
        // Backend failed — continue with local checks
      }

      // 2. Provider check
      try {
        const res = await fetchModels()
        if (!res.data || res.data.length === 0) {
          results.push({
            id: 'health:provider-empty',
            source: 'health',
            severity: 'error',
            status: 'active',
            title: 'AI Provider not configured',
            detail: 'No AI models available. Select a provider and enter an API key.',
            configSources: ['env'],
            action: { type: 'inline', label: 'Configure', target: 'provider' },
          })
        }
      } catch {
        results.push({
          id: 'health:provider-empty',
          source: 'health',
          severity: 'error',
          status: 'active',
          title: 'AI Provider not connected',
          detail: 'Cannot reach AI provider. Check your configuration.',
          configSources: ['env'],
          action: { type: 'inline', label: 'Configure', target: 'provider' },
        })
      }

      // 3. SOUL.md check (supplement backend)
      try {
        const mem = await fetchMemory()
        if (mem.soul && mem.soul.trim().length > 10) {
          const soulItem = results.find(i => i.id === 'health:soul-empty')
          if (soulItem) soulItem.status = 'resolved'
        } else if (!results.some(i => i.id === 'health:soul-empty')) {
          results.push({
            id: 'health:soul-empty',
            source: 'health',
            severity: 'warning',
            status: 'active',
            title: 'SOUL.md not defined',
            detail: 'Agent personality is empty. Define it to give your agent a clear role.',
            configSources: ['soul.md'],
            action: { type: 'ai-generate', label: 'AI Generate', target: 'soul' },
          })
        }
      } catch {
        // Ignore
      }

      items.value = results
      return results
    } finally {
      loading.value = false
    }
  }

  function markResolved(id: string) {
    const item = items.value.find(i => i.id === id)
    if (item) item.status = 'resolved'
  }

  return { items, loading, check, markResolved }
}
