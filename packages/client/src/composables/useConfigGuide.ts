import { ref } from 'vue'
import type { SmartConfigItem, AppConfig } from '@/api/hermes/config'
import { PLATFORM_KEYS } from './useSmartConfig'

export function useConfigGuide() {
  const guideItems = ref<SmartConfigItem[]>([])

  function detect(healthItems: SmartConfigItem[], config: AppConfig | null): SmartConfigItem[] {
    const results: SmartConfigItem[] = []

    const hasProvider = !healthItems.some(i => i.id.includes('provider') && i.severity === 'error')
    const hasSoul = !healthItems.some(i => i.id.includes('soul') && i.severity !== 'info')
    const memoryEnabled = config?.memory?.memory_enabled ?? false
    const connectedPlatforms = PLATFORM_KEYS.filter(key => {
      const section = config?.[key as keyof AppConfig] ?? config?.platforms?.[key]
      return section && typeof section === 'object' && Object.keys(section).length > 0
    })

    if (!hasProvider) {
      results.push({
        id: 'guide:provider-setup',
        source: 'guide',
        severity: 'error',
        status: 'active',
        title: 'Configure AI Provider',
        detail: 'Select a provider and enter your API key to start chatting.',
        configSources: ['env'],
        action: { type: 'inline', label: 'Configure', target: 'provider' },
      })
    }

    if (!hasSoul) {
      results.push({
        id: 'guide:soul-setup',
        source: 'guide',
        severity: 'warning',
        status: 'active',
        title: 'Define Agent Personality',
        detail: 'Use AI to generate or manually write your agent\'s personality.',
        configSources: ['soul.md'],
        action: { type: 'ai-generate', label: 'AI Generate', target: 'soul' },
      })
    }

    if (hasProvider && hasSoul && !memoryEnabled) {
      results.push({
        id: 'guide:memory-enable',
        source: 'guide',
        severity: 'info',
        status: 'active',
        title: 'Enable Memory',
        detail: 'Let your agent remember context across sessions.',
        configSources: ['config.yaml'],
        action: { type: 'inline', label: 'Enable', target: 'memory' },
      })
    }

    if (hasProvider && hasSoul && connectedPlatforms.length === 0) {
      results.push({
        id: 'guide:platform-connect',
        source: 'guide',
        severity: 'info',
        status: 'active',
        title: 'Connect Messaging Platforms (optional)',
        detail: 'Connect Telegram, Discord, Slack and more.',
        configSources: ['config.yaml', 'env'],
        action: { type: 'navigate', label: 'Open Settings', target: 'hermes.settings' },
      })
    }

    guideItems.value = results
    return results
  }

  return { guideItems, detect }
}
