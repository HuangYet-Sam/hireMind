import { ref, computed } from 'vue'
import { fetchConfig, type AppConfig, type SmartConfigItem } from '@/api/hermes/config'
import type { MemoryData } from '@/api/hermes/skills'
import { fetchMemory } from '@/api/hermes/skills'
import { useConfigHealth } from './useConfigHealth'
import { useConfigGuide } from './useConfigGuide'
import { useConfigSuggest } from './useConfigSuggest'

const DISMISSED_KEY = 'hermes_smart_dismissed'

export const PLATFORM_KEYS = [
  'telegram', 'discord', 'slack', 'whatsapp', 'matrix',
  'wecom', 'feishu', 'dingtalk', 'weixin',
  'signal', 'email', 'irc', 'mattermost', 'teams',
  'qq', 'yuanbao', 'webhook', 'homeassistant', 'float',
]

const severityOrder: Record<string, number> = { error: 0, warning: 1, info: 2 }
const sourceOrder: Record<string, number> = { health: 0, guide: 1, suggest: 2 }

const KNOWN_TOPICS = new Set(['provider', 'soul', 'memory'])

function itemTopic(item: SmartConfigItem): string {
  if (item.action?.target && KNOWN_TOPICS.has(item.action.target)) return item.action.target
  const stripped = item.id.replace(/^(health|guide|suggest):/, '')
  // Normalize known prefixes so different sources dedup correctly
  if (stripped.startsWith('provider')) return 'provider'
  if (stripped.startsWith('soul')) return 'soul'
  if (stripped.startsWith('memory')) return 'memory'
  return stripped
}

function loadDismissed(): Set<string> {
  try {
    const raw = localStorage.getItem(DISMISSED_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) return new Set(parsed)
    }
  } catch {
    // ignore
  }
  return new Set()
}

function saveDismissed(ids: Set<string>) {
  try {
    localStorage.setItem(DISMISSED_KEY, JSON.stringify([...ids]))
  } catch {
    // ignore quota errors
  }
}

export function useSmartConfig() {
  const health = useConfigHealth()
  const guide = useConfigGuide()
  const suggest = useConfigSuggest()

  const loading = ref(false)
  const dismissed = ref<Set<string>>(loadDismissed())
  const currentConfig = ref<AppConfig | null>(null)
  const currentMemory = ref<MemoryData | null>(null)

  const items = computed<SmartConfigItem[]>(() => {
    const healthItems = health.items.value.filter((i) => i.status !== 'resolved')
    const guideItems = guide.detect(healthItems, currentConfig.value)
    const suggestItems = suggest.detect(healthItems, currentConfig.value, currentMemory.value)

    // Merge all sources
    const all = [...healthItems, ...guideItems, ...suggestItems]

    // Dedup by semantic topic, higher sourceOrder wins (suggest > guide > health)
    const seen = new Map<string, SmartConfigItem>()
    for (const item of all) {
      const key = itemTopic(item)
      const existing = seen.get(key)
      if (!existing) {
        seen.set(key, item)
      } else if (sourceOrder[item.source] > sourceOrder[existing.source]) {
        seen.set(key, item)
      }
    }

    // Filter dismissed (error severity items cannot be dismissed)
    const filtered = [...seen.values()].filter(
      (i) => i.severity === 'error' || (!dismissed.value.has(i.id) && !dismissed.value.has(itemTopic(i))),
    )

    // Sort: error > warning > info, then health > guide > suggest
    return filtered.sort(
      (a, b) =>
        severityOrder[a.severity] - severityOrder[b.severity] ||
        sourceOrder[a.source] - sourceOrder[b.source],
    )
  })

  const hasIssues = computed(() => items.value.length > 0)
  const errorCount = computed(() => items.value.filter((i) => i.severity === 'error').length)
  const pendingCount = computed(() => items.value.filter((i) => i.status === 'active').length)
  const allResolved = computed(() => items.value.length === 0 || pendingCount.value === 0)

  function dismiss(id: string) {
    const item = items.value.find((i) => i.id === id)
    if (item && item.severity === 'error') return

    const next = new Set(dismissed.value)
    next.add(id)
    if (item) next.add(itemTopic(item))
    dismissed.value = next
    saveDismissed(next)
  }

  function markResolved(id: string) {
    health.markResolved(id)
    const item = items.value.find((i) => i.id === id)
    const next = new Set(dismissed.value)
    next.delete(id)
    if (item) next.delete(itemTopic(item))
    dismissed.value = next
    saveDismissed(next)
  }

  async function refresh() {
    loading.value = true
    try {
      const [cfg, mem] = await Promise.all([
        fetchConfig().catch(() => null),
        fetchMemory().catch(() => null),
        health.check().catch(() => []),
      ])
      currentConfig.value = cfg
      currentMemory.value = mem
    } finally {
      loading.value = false
    }
  }

  return {
    items,
    loading,
    hasIssues,
    errorCount,
    pendingCount,
    allResolved,
    dismiss,
    markResolved,
    refresh,
    // Passthrough from suggest
    generating: suggest.generating,
    streamContent: suggest.streamContent,
    generateSoul: suggest.generateSoul,
    generateConfigRecommendation: suggest.generateConfigRecommendation,
    abortGeneration: suggest.abortGeneration,
  }
}
