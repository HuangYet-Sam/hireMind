import { ref, type Ref } from 'vue'
import type { SmartConfigItem, AppConfig } from '@/api/hermes/config'
import type { MemoryData } from '@/api/hermes/skills'
import { startRunViaSocket, type RunEvent } from '@/api/hermes/chat'
import { PLATFORM_KEYS } from './useSmartConfig'

const SOUL_SYSTEM_PROMPT =
  'You are a SOUL.md generator for Hermes AI Agent. Given the user\'s description of their desired assistant, generate a complete SOUL.md file. Format: Markdown with # Role, # Personality, # Guidelines, # Constraints. Be specific, actionable, professional. Output ONLY the SOUL.md content.'

const CONFIG_SYSTEM_PROMPT =
  'You are a configuration optimizer for Hermes AI Agent. Given SOUL.md, platforms, and current config, recommend optimal settings. Return JSON: { "agent": { "max_turns": number, "gateway_timeout": number }, "memory": { "memory_enabled": boolean }, "reasons": { "section.key": "reason" } }. Output ONLY valid JSON, no markdown fences.'

const GENERATION_TIMEOUT = 60_000

function streamRun(
  input: string,
  instructions: string,
  streamContent: Ref<string>,
  abortRef: Ref<(() => void) | null>,
): Promise<{ text: string; error: string | null }> {
  return new Promise((resolve) => {
    let resolved = false
    let accumulated = ''
    const sessionId = `suggest-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

    const { abort } = startRunViaSocket(
      { input, instructions, session_id: sessionId },
      (event: RunEvent) => {
        if (event.delta) {
          accumulated += event.delta
          streamContent.value = accumulated
        }
        if (event.event === 'run.completed' && event.output && !accumulated) {
          accumulated = event.output
          streamContent.value = accumulated
        }
      },
      () => {
        if (!resolved) {
          resolved = true
          abortRef.value = null
          clearTimeout(timer)
          resolve({ text: accumulated, error: accumulated ? null : 'AI returned empty response' })
        }
      },
      (err: Error) => {
        if (!resolved) {
          resolved = true
          abortRef.value = null
          clearTimeout(timer)
          resolve({ text: accumulated, error: err.message })
        }
      },
    )
    abortRef.value = abort

    const timer = setTimeout(() => {
      if (!resolved) {
        resolved = true
        abort()
        abortRef.value = null
        resolve({ text: accumulated, error: 'Generation timed out' })
      }
    }, GENERATION_TIMEOUT)
  })
}

const CODING_KEYWORDS = [
  'code', 'coding', 'programming', 'developer', 'software',
  'debug', 'refactor', 'engineer', 'development', 'implementation',
]

export function useConfigSuggest() {
  const suggestItems = ref<SmartConfigItem[]>([])
  const generating = ref(false)
  const streamContent = ref('')
  const currentAbort = ref<(() => void) | null>(null)

  function detect(
    healthItems: SmartConfigItem[],
    config: AppConfig | null,
    memory: MemoryData | null,
  ): SmartConfigItem[] {
    const results: SmartConfigItem[] = []

    const hasProvider = !healthItems.some(
      (i) => i.id.includes('provider') && i.severity === 'error',
    )

    if (!hasProvider) return results

    const connectedPlatforms = PLATFORM_KEYS.filter((key) => {
      const section = config?.[key as keyof AppConfig] ?? config?.platforms?.[key]
      return section && typeof section === 'object' && Object.keys(section).length > 0
    })

    const memoryEnabled = config?.memory?.memory_enabled ?? false
    const maxTurns = config?.agent?.max_turns ?? 0
    const gatewayTimeout = config?.agent?.gateway_timeout ?? 0
    const soulContent = memory?.soul ?? ''

    if (connectedPlatforms.length >= 2 && !memoryEnabled) {
      results.push({
        id: 'suggest:enable-memory',
        source: 'suggest',
        severity: 'info',
        status: 'active',
        title: 'Enable memory for multi-platform use',
        detail: 'You have multiple platforms connected but memory is disabled. Enabling memory keeps context consistent across channels.',
        configSources: ['config.yaml'],
        action: { type: 'inline', label: 'Enable Memory', target: 'memory' },
      })
    }

    const lowerSoul = soulContent.toLowerCase()
    const hasCodingKeywords = CODING_KEYWORDS.some((kw) => lowerSoul.includes(kw))
    if (hasCodingKeywords && maxTurns > 0 && maxTurns < 20) {
      results.push({
        id: 'suggest:increase-max-turns',
        source: 'suggest',
        severity: 'info',
        status: 'active',
        title: 'Increase max turns for coding tasks',
        detail: 'Your agent has a coding personality but max_turns is set low. Increasing to 30 allows more thorough code assistance.',
        configSources: ['config.yaml'],
        action: { type: 'inline', label: 'Set to 30', target: 'agent.max_turns', payload: { value: 30 } },
      })
    }

    if (soulContent.length > 2000) {
      results.push({
        id: 'suggest:condense-soul',
        source: 'suggest',
        severity: 'info',
        status: 'active',
        title: 'Condense SOUL.md',
        detail: 'Your SOUL.md is over 2000 characters. A more concise version can improve agent focus and reduce token costs.',
        configSources: ['soul.md'],
        action: { type: 'ai-generate', label: 'AI Condense', target: 'soul' },
      })
    }

    if (connectedPlatforms.length > 0 && gatewayTimeout > 0 && gatewayTimeout < 60) {
      results.push({
        id: 'suggest:increase-timeout',
        source: 'suggest',
        severity: 'info',
        status: 'active',
        title: 'Increase gateway timeout',
        detail: 'With platforms connected, a gateway timeout under 60s may cause dropped responses. Recommend setting to 120s.',
        configSources: ['config.yaml'],
        action: { type: 'inline', label: 'Set to 120s', target: 'agent.gateway_timeout', payload: { value: 120 } },
      })
    }

    suggestItems.value = results
    return results
  }

  function abortGeneration() {
    currentAbort.value?.()
    currentAbort.value = null
  }

  async function generateSoul(userDescription: string): Promise<{ text: string; error: string | null }> {
    if (generating.value) return { text: '', error: 'Generation already in progress' }
    generating.value = true
    streamContent.value = ''
    try {
      return await streamRun(userDescription, SOUL_SYSTEM_PROMPT, streamContent, currentAbort)
    } finally {
      generating.value = false
    }
  }

  async function generateConfigRecommendation(
    soulContent: string,
    platforms: string[],
    currentConfig: Partial<AppConfig>,
  ): Promise<{ text: string; error: string | null }> {
    if (generating.value) return { text: '', error: 'Generation already in progress' }
    generating.value = true
    streamContent.value = ''
    try {
      const input = JSON.stringify({ soul: soulContent, platforms, currentConfig })
      return await streamRun(input, CONFIG_SYSTEM_PROMPT, streamContent, currentAbort)
    } finally {
      generating.value = false
    }
  }

  return {
    suggestItems,
    generating,
    streamContent,
    detect,
    abortGeneration,
    generateSoul,
    generateConfigRecommendation,
  }
}
