# Smart Config Guidance Layer — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the basic 4-item SetupChecklist with a three-layer intelligent config guidance system that detects cross-file conflicts, guides first-time setup, and suggests AI-powered optimizations.

**Architecture:** Four new composables (useConfigHealth, useConfigGuide, useConfigSuggest, useSmartConfig) orchestrated by a thin merge/dedup layer. One new backend endpoint (`GET /api/hermes/config/health`) handles .env-aware conflict detection. SetupChecklist.vue upgrades from hardcoded to dynamic rendering.

**Tech Stack:** Vue 3 Composition API, Pinia stores, Naive UI, Koa 2 backend, TypeScript strict mode

---

## Task 1: Backend — Create health-config controller

**Files:**
- Create: `packages/server/src/controllers/hermes/health-config.ts`

**Step 1: Write the controller**

```typescript
// packages/server/src/controllers/hermes/health-config.ts
import { readFile } from 'fs/promises'
import YAML from 'js-yaml'
import { getActiveConfigPath, getActiveEnvPath } from '../../services/hermes/hermes-profile'
import { safeReadFile } from '../../services/config-helpers'

interface HealthItem {
  id: string
  severity: 'error' | 'warning' | 'info'
  title: string
  detail: string
  configSources: ('config.yaml' | 'soul.md' | 'env')[]
  action?: {
    type: 'inline' | 'navigate'
    label: string
    target?: string
    payload?: Record<string, any>
  }
}

// Subset of envPlatformMap from config controller — maps env var → [platform, configPath]
const ENV_PLATFORM_MAP: Record<string, [string, string]> = {
  TELEGRAM_BOT_TOKEN: ['telegram', 'token'],
  DISCORD_BOT_TOKEN: ['discord', 'token'],
  SLACK_BOT_TOKEN: ['slack', 'token'],
  MATRIX_ACCESS_TOKEN: ['matrix', 'token'],
  FEISHU_APP_ID: ['feishu', 'extra.app_id'],
  FEISHU_APP_SECRET: ['feishu', 'extra.app_secret'],
  DINGTALK_CLIENT_ID: ['dingtalk', 'extra.client_id'],
  DINGTALK_CLIENT_SECRET: ['dingtalk', 'extra.client_secret'],
  WECOM_BOT_ID: ['wecom', 'extra.bot_id'],
  WECOM_SECRET: ['wecom', 'extra.secret'],
  WEIXIN_TOKEN: ['weixin', 'token'],
  WHATSAPP_ENABLED: ['whatsapp', 'enabled'],
  SIGNAL_HTTP_URL: ['signal', 'extra.http_url'],
  EMAIL_ADDRESS: ['email', 'extra.address'],
  EMAIL_PASSWORD: ['email', 'extra.password'],
  IRC_SERVER: ['irc', 'extra.server'],
  MATTERMOST_URL: ['mattermost', 'extra.url'],
  MATTERMOST_TOKEN: ['mattermost', 'token'],
  TEAMS_APP_ID: ['teams', 'extra.app_id'],
  TEAMS_CLIENT_SECRET: ['teams', 'extra.client_secret'],
  QQ_APP_ID: ['qq', 'extra.app_id'],
  QQ_CLIENT_SECRET: ['qq', 'extra.client_secret'],
  YUANBAO_APP_ID: ['yuanbao', 'extra.app_id'],
  YUANBAO_TOKEN: ['yuanbao', 'token'],
  WEBHOOK_URL: ['webhook', 'extra.url'],
  HOMEASSISTANT_URL: ['homeassistant', 'extra.url'],
  HOMEASSISTANT_TOKEN: ['homeassistant', 'token'],
  FLOAT_API_KEY: ['float', 'extra.api_key'],
}

// Map platform → required env vars for that platform
const PLATFORM_ENV_REQUIREMENTS: Record<string, string[]> = {}
for (const [envVar, [platform]] of Object.entries(ENV_PLATFORM_MAP)) {
  if (!PLATFORM_ENV_REQUIREMENTS[platform]) PLATFORM_ENV_REQUIREMENTS[platform] = []
  PLATFORM_ENV_REQUIREMENTS[platform].push(envVar)
}

function parseEnv(raw: string): Record<string, string> {
  const env: Record<string, string> = {}
  for (const line of raw.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eqIdx = trimmed.indexOf('=')
    if (eqIdx === -1) continue
    const key = trimmed.slice(0, eqIdx).trim()
    const val = trimmed.slice(eqIdx + 1).trim()
    if (val) env[key] = val
  }
  return env
}

function hasPlatformConfig(config: Record<string, any>, platform: string): boolean {
  const p = config.platforms?.[platform]
  if (!p) return false
  // Has at least one non-empty field
  return Object.values(p).some(v => v !== undefined && v !== null && v !== '')
}

export async function check(ctx: any) {
  try {
    const items: HealthItem[] = []

    // Read all three sources
    const configRaw = await safeReadFile(getActiveConfigPath())
    const envRaw = await safeReadFile(getActiveEnvPath())
    const hermesDir = process.env.HERMES_DIR || `${process.env.HOME || process.env.USERPROFILE}/.hermes`
    const { join } = await import('path')
    const soulRaw = await safeReadFile(join(hermesDir, 'SOUL.md'))

    const config: Record<string, any> = configRaw ? (YAML.load(configRaw) as Record<string, any>) || {} : {}
    const env = envRaw ? parseEnv(envRaw) : {}
    const soul = soulRaw || ''

    // ─── Cross-file conflict: env has credential but config doesn't enable ───
    const envPlatforms = new Set<string>()
    for (const [envVar, [platform]] of Object.entries(ENV_PLATFORM_MAP)) {
      if (env[envVar]) envPlatforms.add(platform)
    }

    for (const platform of envPlatforms) {
      if (!hasPlatformConfig(config, platform)) {
        items.push({
          id: `health:env-${platform}-no-config`,
          severity: 'warning',
          title: `${platform} credential exists but not enabled`,
          detail: `.env has credentials for ${platform}, but it is not configured in config.yaml`,
          configSources: ['env', 'config.yaml'],
          action: { type: 'inline', label: 'Enable', target: platform, payload: { platform } },
        })
      }
    }

    // ─── Cross-file conflict: config enables platform but env lacks credential ───
    const configPlatforms = config.platforms || {}
    for (const [platform, _] of Object.entries(configPlatforms)) {
      if (!PLATFORM_ENV_REQUIREMENTS[platform]) continue
      const required = PLATFORM_ENV_REQUIREMENTS[platform]
      const missing = required.filter(v => !env[v])
      // Only report if platform appears enabled (has non-empty config) but misses critical creds
      const tokenVars = required.filter(v => v.includes('TOKEN') || v.includes('SECRET') || v.includes('KEY'))
      if (tokenVars.length > 0 && tokenVars.some(v => !env[v]) && hasPlatformConfig(config, platform)) {
        items.push({
          id: `health:config-${platform}-no-cred`,
          severity: 'error',
          title: `${platform} enabled but missing credential`,
          detail: `${platform} is configured but required credential is missing from .env`,
          configSources: ['config.yaml', 'env'],
          action: { type: 'navigate', label: 'Configure', target: 'hermes.settings' },
        })
      }
    }

    // ─── SOUL.md analysis ───
    if (!soul || soul.trim().length <= 10) {
      items.push({
        id: 'health:soul-empty',
        severity: 'warning',
        title: 'SOUL.md not defined',
        detail: 'Agent personality is empty. Define it to give your agent a clear role.',
        configSources: ['soul.md'],
        action: { type: 'inline', label: 'Define', target: 'soul' },
      })
    }

    ctx.body = { items }
  } catch (err: any) {
    ctx.status = 500
    ctx.body = { error: err.message }
  }
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd packages/server && npx tsc --noEmit`
Expected: No type errors

**Step 3: Commit**

```bash
git add packages/server/src/controllers/hermes/health-config.ts
git commit -m "feat: add health-config controller for cross-file conflict detection"
```

---

## Task 2: Backend — Create health-config route + register

**Files:**
- Create: `packages/server/src/routes/hermes/health-config.ts`
- Modify: `packages/server/src/routes/index.ts`

**Step 1: Create route file**

```typescript
// packages/server/src/routes/hermes/health-config.ts
import Router from '@koa/router'
import * as ctrl from '../../controllers/hermes/health-config'

export const healthConfigRoutes = new Router()
healthConfigRoutes.get('/api/hermes/config/health', ctrl.check)
```

**Step 2: Register route in index.ts**

Add import at top of `packages/server/src/routes/index.ts`:

```typescript
import { healthConfigRoutes } from './hermes/health-config'
```

Add before `proxyRoutes` (line 79):

```typescript
app.use(healthConfigRoutes.routes())
```

**Step 3: Verify TypeScript compiles**

Run: `cd packages/server && npx tsc --noEmit`
Expected: No type errors

**Step 4: Commit**

```bash
git add packages/server/src/routes/hermes/health-config.ts packages/server/src/routes/index.ts
git commit -m "feat: add health-config route for GET /api/hermes/config/health"
```

---

## Task 3: Frontend — Add health API + SmartConfigItem type

**Files:**
- Modify: `packages/client/src/api/hermes/config.ts`

**Step 1: Add SmartConfigItem interface and fetchConfigHealth function**

Append to `packages/client/src/api/hermes/config.ts`:

```typescript
export interface SmartConfigItem {
  id: string
  source: 'health' | 'guide' | 'suggest'
  severity: 'error' | 'warning' | 'info'
  status: 'active' | 'dismissed' | 'resolved'
  title: string
  detail: string
  configSources: ('config.yaml' | 'soul.md' | 'env')[]
  action?: {
    type: 'inline' | 'navigate' | 'ai-generate'
    label: string
    target?: string
    payload?: Record<string, any>
  }
}

export interface ConfigHealthResponse {
  items: SmartConfigItem[]
}

export async function fetchConfigHealth(): Promise<ConfigHealthResponse> {
  return request<ConfigHealthResponse>('/api/hermes/config/health')
}
```

**Step 2: Verify TypeScript compiles**

Run: `npx vue-tsc --noEmit`
Expected: No type errors

**Step 3: Commit**

```bash
git add packages/client/src/api/hermes/config.ts
git commit -m "feat: add SmartConfigItem type and fetchConfigHealth API"
```

---

## Task 4: Frontend — Create useConfigHealth composable

**Files:**
- Create: `packages/client/src/composables/useConfigHealth.ts`

**Step 1: Write the composable**

```typescript
// packages/client/src/composables/useConfigHealth.ts
import { ref } from 'vue'
import { fetchConfigHealth, type SmartConfigItem } from '@/api/hermes/config'
import { fetchModels } from '@/api/hermes/chat'
import { fetchMemory } from '@/api/hermes/skills'

export function useConfigHealth() {
  const items = ref<SmartConfigItem[]>([])
  const loading = ref(false)

  async function check(): Promise<SmartConfigItem[]> {
    loading.value = true
    const results: SmartConfigItem[] = []

    // 1. Backend-driven cross-file conflict detection
    try {
      const health = await fetchConfigHealth()
      for (const item of health.items) {
        results.push({ ...item, source: 'health', status: 'active' })
      }
    } catch {
      // Backend health endpoint failed — continue with local checks
    }

    // 2. Frontend-only: Provider check (requires fetchModels which hits gateway)
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

    // 3. Frontend-only: SOUL.md check (supplement backend check with local data)
    try {
      const mem = await fetchMemory()
      if (mem.soul && mem.soul.trim().length > 10) {
        // Soul is defined — mark backend's soul-empty as resolved if present
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
      // Ignore — backend check already covers this
    }

    items.value = results
    loading.value = false
    return results
  }

  function markResolved(id: string) {
    const item = items.value.find(i => i.id === id)
    if (item) item.status = 'resolved'
  }

  return { items, loading, check, markResolved }
}
```

**Step 2: Verify TypeScript compiles**

Run: `npx vue-tsc --noEmit`
Expected: No type errors

**Step 3: Commit**

```bash
git add packages/client/src/composables/useConfigHealth.ts
git commit -m "feat: add useConfigHealth composable for detection layer"
```

---

## Task 5: Frontend — Create useConfigGuide composable

**Files:**
- Create: `packages/client/src/composables/useConfigGuide.ts`

**Step 1: Write the composable**

```typescript
// packages/client/src/composables/useConfigGuide.ts
import { ref } from 'vue'
import type { SmartConfigItem } from '@/api/hermes/config'

export function useConfigGuide() {
  const guideItems = ref<SmartConfigItem[]>([])

  function detect(healthItems: SmartConfigItem[]): SmartConfigItem[] {
    const results: SmartConfigItem[] = []

    const hasProvider = !healthItems.some(i => i.id.includes('provider') && i.severity === 'error')
    const hasSoul = !healthItems.some(i => i.id.includes('soul') && i.severity !== 'info')
    const hasMemory = healthItems.some(i => i.id.includes('memory'))

    // Provider guide — only if health says it's missing
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

    // SOUL.md guide — only if health says it's missing
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

    // Memory guide — only if not yet prompted
    if (!hasMemory && hasProvider && hasSoul) {
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

    // Platform guide — only after core is done
    if (hasProvider && hasSoul) {
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
```

**Step 2: Verify TypeScript compiles**

Run: `npx vue-tsc --noEmit`
Expected: No type errors

**Step 3: Commit**

```bash
git add packages/client/src/composables/useConfigGuide.ts
git commit -m "feat: add useConfigGuide composable for first-time guidance"
```

---

## Task 6: Frontend — Create useConfigSuggest composable

**Files:**
- Create: `packages/client/src/composables/useConfigSuggest.ts`

**Step 1: Write the composable**

```typescript
// packages/client/src/composables/useConfigSuggest.ts
import { ref, type Ref } from 'vue'
import type { SmartConfigItem, AppConfig } from '@/api/hermes/config'
import type { MemoryData } from '@/api/hermes/skills'
import { startRunViaSocket, type RunEvent } from '@/api/hermes/chat'

const SOUL_SYSTEM_PROMPT = `You are a SOUL.md generator for Hermes AI Agent. Given the user's description of their desired assistant, generate a complete SOUL.md file. Format: Markdown with # Role, # Personality, # Guidelines, # Constraints. Be specific, actionable, professional. Output ONLY the SOUL.md content.`

const CONFIG_SYSTEM_PROMPT = `You are a configuration optimizer for Hermes AI Agent. Given SOUL.md, platforms, and current config, recommend optimal settings. Return JSON: { "agent": { "max_turns": number, "gateway_timeout": number }, "memory": { "memory_enabled": boolean }, "reasons": { "section.key": "reason" } }. Output ONLY valid JSON, no markdown fences.`

function stripCodeFences(raw: string): string {
  let s = raw.trim()
  s = s.replace(/^```(?:json|JSON)?\s*\n?/, '')
  s = s.replace(/\n?```\s*$/, '')
  return s.trim()
}

function streamRun(input: string, instructions: string, streamContent: Ref<string>): Promise<{ text: string; error: string | null }> {
  return new Promise((resolve) => {
    let accumulated = ''
    const sessionId = `suggest-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

    startRunViaSocket(
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
      () => resolve({ text: accumulated, error: null }),
      (err: Error) => resolve({ text: accumulated, error: err.message }),
    )
  })
}

export function useConfigSuggest() {
  const suggestItems = ref<SmartConfigItem[]>([])
  const generating = ref(false)
  const streamContent = ref('')

  function detect(
    healthItems: SmartConfigItem[],
    config: AppConfig | null,
    memory: MemoryData | null,
  ): SmartConfigItem[] {
    const results: SmartConfigItem[] = []
    const soul = memory?.soul || ''
    const platforms = config?.platforms || {}
    const platformCount = Object.keys(platforms).length

    // Rule: Multi-platform → suggest enabling memory
    if (platformCount >= 2 && !config?.memory?.memory_enabled) {
      results.push({
        id: 'suggest:multi-platform-memory',
        source: 'suggest',
        severity: 'info',
        status: 'active',
        title: 'Suggest enabling memory',
        detail: `${platformCount} platforms connected. Memory preserves context across platforms.`,
        configSources: ['config.yaml'],
        action: { type: 'inline', label: 'Enable', target: 'memory' },
      })
    }

    // Rule: Coding scenario → suggest higher max_turns
    const isCoding = /coding|编程|代码|开发|debug|engineer/i.test(soul)
    if (isCoding && config?.agent?.max_turns && config.agent.max_turns < 20) {
      results.push({
        id: 'suggest:coding-max-turns',
        source: 'suggest',
        severity: 'info',
        status: 'active',
        title: 'Suggest increasing max turns',
        detail: `Coding scenarios often need more tool calls. Current max_turns=${config.agent.max_turns}.`,
        configSources: ['config.yaml', 'soul.md'],
        action: { type: 'inline', label: 'Set to 30', target: 'agent.max_turns', payload: { value: 30 } },
      })
    }

    // Rule: SOUL.md too long
    if (soul.length > 2000) {
      results.push({
        id: 'suggest:soul-too-long',
        source: 'suggest',
        severity: 'info',
        status: 'active',
        title: 'SOUL.md is long, consider condensing',
        detail: `Current: ${soul.length} chars. Long SOUL.md increases token usage per message.`,
        configSources: ['soul.md'],
        action: { type: 'ai-generate', label: 'AI Condense', target: 'soul', payload: { instruction: 'condense' } },
      })
    }

    // Rule: Has platforms but low gateway timeout
    if (platformCount > 0 && (!config?.agent?.gateway_timeout || config.agent.gateway_timeout < 60)) {
      results.push({
        id: 'suggest:gateway-timeout',
        source: 'suggest',
        severity: 'info',
        status: 'active',
        title: 'Suggest increasing gateway timeout',
        detail: 'With connected platforms, gateway_timeout should be ≥ 120s.',
        configSources: ['config.yaml'],
        action: { type: 'inline', label: 'Set 120s', target: 'agent.gateway_timeout', payload: { value: 120 } },
      })
    }

    suggestItems.value = results
    return results
  }

  async function generateSoul(userDescription: string): Promise<{ content: string; error: string | null }> {
    generating.value = true
    streamContent.value = ''
    const result = await streamRun(userDescription, SOUL_SYSTEM_PROMPT, streamContent)
    generating.value = false
    return { content: result.text, error: result.error }
  }

  async function generateConfigRecommendation(
    soulContent: string,
    platforms: string[],
    currentConfig: Record<string, any>,
  ): Promise<{ config: Record<string, any>; reasons: Record<string, string>; error: string | null }> {
    generating.value = true
    streamContent.value = ''

    const userMessage = [
      '## SOUL.md', soulContent, '',
      '## Selected Platforms', JSON.stringify(platforms, null, 2), '',
      '## Current Config', JSON.stringify(currentConfig, null, 2),
    ].join('\n')

    const result = await streamRun(userMessage, CONFIG_SYSTEM_PROMPT, streamContent)
    generating.value = false

    if (result.error) return { config: {}, reasons: {}, error: result.error }

    try {
      const parsed = JSON.parse(stripCodeFences(result.text))
      const config: Record<string, any> = {}
      if (parsed.agent !== undefined) config.agent = parsed.agent
      if (parsed.memory !== undefined) config.memory = parsed.memory
      return { config, reasons: parsed.reasons ?? {}, error: null }
    } catch {
      return { config: {}, reasons: {}, error: 'Failed to parse configuration recommendations.' }
    }
  }

  return { suggestItems, generating, streamContent, detect, generateSoul, generateConfigRecommendation }
}
```

**Step 2: Verify TypeScript compiles**

Run: `npx vue-tsc --noEmit`
Expected: No type errors

**Step 3: Commit**

```bash
git add packages/client/src/composables/useConfigSuggest.ts
git commit -m "feat: add useConfigSuggest composable for AI-powered suggestions"
```

---

## Task 7: Frontend — Create useSmartConfig orchestration composable

**Files:**
- Create: `packages/client/src/composables/useSmartConfig.ts`

**Step 1: Write the composable**

```typescript
// packages/client/src/composables/useSmartConfig.ts
import { ref, computed } from 'vue'
import type { SmartConfigItem } from '@/api/hermes/config'
import { useConfigHealth } from './useConfigHealth'
import { useConfigGuide } from './useConfigGuide'
import { useConfigSuggest } from './useConfigSuggest'
import { fetchConfig, type AppConfig } from '@/api/hermes/config'
import { fetchMemory, type MemoryData } from '@/api/hermes/skills'

const DISMISSED_KEY = 'hermes_smart_dismissed'

const severityOrder: Record<string, number> = { error: 0, warning: 1, info: 2 }
const sourceOrder: Record<string, number> = { health: 0, guide: 1, suggest: 2 }

function loadDismissed(): Set<string> {
  try {
    const raw = localStorage.getItem(DISMISSED_KEY)
    return new Set(raw ? JSON.parse(raw) : [])
  } catch {
    return new Set()
  }
}

function saveDismissed(ids: Set<string>) {
  try {
    localStorage.setItem(DISMISSED_KEY, JSON.stringify([...ids]))
  } catch {
    // Ignore quota errors
  }
}

export function useSmartConfig() {
  const health = useConfigHealth()
  const guide = useConfigGuide()
  const suggest = useConfigSuggest()

  const loading = ref(false)
  const currentConfig = ref<AppConfig | null>(null)
  const currentMemory = ref<MemoryData | null>(null)
  const dismissed = ref<Set<string>>(loadDismissed())

  const items = computed<SmartConfigItem[]>(() => {
    const healthItems = health.items.value.filter(i => i.status !== 'resolved')
    const guideItems = guide.detect(healthItems)
    const suggestItems = suggest.detect(healthItems, currentConfig.value, currentMemory.value)

    // 1. Merge
    const all = [...healthItems, ...guideItems, ...suggestItems]

    // 2. Dedup: same prefix, guide wins over health
    const seen = new Map<string, SmartConfigItem>()
    for (const item of all) {
      // Use id prefix for dedup (e.g. "provider" matches "health:provider-empty" and "guide:provider-setup")
      const key = item.id.replace(/^(health|guide|suggest):/, '')
      const existing = seen.get(key)
      if (!existing) {
        seen.set(key, item)
      } else if (item.source === 'guide' && existing.source === 'health') {
        seen.set(key, item)
      }
    }

    // 3. Filter dismissed (but not error severity)
    const currentDismissed = dismissed.value
    const filtered = [...seen.values()].filter(
      i => i.severity === 'error' || !currentDismissed.has(i.id),
    )

    // 4. Sort
    return filtered.sort(
      (a, b) => severityOrder[a.severity] - severityOrder[b.severity] || sourceOrder[a.source] - sourceOrder[b.source],
    )
  })

  const hasIssues = computed(() => items.value.some(i => i.severity !== 'info'))
  const errorCount = computed(() => items.value.filter(i => i.severity === 'error').length)
  const pendingCount = computed(() => items.value.filter(i => i.status !== 'resolved').length)
  const allResolved = computed(() => items.value.length > 0 && pendingCount.value === 0)

  async function refresh() {
    loading.value = true
    try {
      const [cfg, mem] = await Promise.all([
        fetchConfig().catch(() => null),
        fetchMemory().catch(() => null),
      ])
      currentConfig.value = cfg
      currentMemory.value = mem
      await health.check()
    } finally {
      loading.value = false
    }
  }

  function dismiss(id: string) {
    const next = new Set(dismissed.value)
    next.add(id)
    dismissed.value = next
    saveDismissed(next)
  }

  function markResolved(id: string) {
    health.markResolved(id)
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
    // Passthrough for AI generation
    generating: suggest.generating,
    streamContent: suggest.streamContent,
    generateSoul: suggest.generateSoul,
    generateConfigRecommendation: suggest.generateConfigRecommendation,
  }
}
```

**Step 2: Verify TypeScript compiles**

Run: `npx vue-tsc --noEmit`
Expected: No type errors

**Step 3: Commit**

```bash
git add packages/client/src/composables/useSmartConfig.ts
git commit -m "feat: add useSmartConfig orchestration composable"
```

---

## Task 8: Frontend — Upgrade SetupChecklist.vue

**Files:**
- Modify: `packages/client/src/components/hermes/chat/SetupChecklist.vue`

**Step 1: Rewrite SetupChecklist.vue**

Replace entire file content with the upgraded version that uses `useSmartConfig` for dynamic rendering:

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, NInput, NSelect, NSpin, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useSmartConfig } from '@/composables/useSmartConfig'
import { useSettingsStore } from '@/stores/hermes/settings'
import { useModelsStore } from '@/stores/hermes/models'
import { updateProvider } from '@/api/hermes/system'
import { fetchModels, startRunViaSocket } from '@/api/hermes/chat'
import { saveMemory } from '@/api/hermes/skills'

const { t } = useI18n()
const message = useMessage()
const settingsStore = useSettingsStore()
const modelsStore = useModelsStore()

const {
  items, loading, hasIssues, errorCount, pendingCount, allResolved,
  dismiss, markResolved, refresh,
  generating, streamContent, generateSoul,
} = useSmartConfig()

const expandedKey = ref<string | null>(null)

// ─── Provider inline state ───
const selectedProvider = ref<string | null>(null)
const apiKey = ref('')
const providerSaving = ref(false)

// ─── Soul inline state ───
const soulDescription = ref('')
const soulContent = ref('')
const soulGenerating = ref(false)
const soulEditing = ref(false)
const soulEditText = ref('')

const SOUL_PRESETS = [
  { key: 'customerService', desc: 'A professional customer service assistant for handling user inquiries with patience and accuracy' },
  { key: 'coding', desc: 'A technical coding assistant skilled in software development, debugging, and code review' },
  { key: 'writing', desc: 'A creative writing assistant for content creation, editing, and style guidance' },
  { key: 'general', desc: 'A versatile general-purpose assistant for Q&A, analysis, and recommendations' },
]

const collapsed = ref(false)

onMounted(() => {
  refresh()
  if (modelsStore.providers.length === 0) {
    modelsStore.fetchProviders()
  }
})

function toggleExpand(key: string | undefined) {
  if (!key) return
  expandedKey.value = expandedKey.value === key ? null : key
}

function toggleCollapse() {
  collapsed.value = !collapsed.value
}

// ─── Provider actions ───
async function saveProvider() {
  if (!selectedProvider.value || !apiKey.value.trim()) return
  providerSaving.value = true
  try {
    await updateProvider(selectedProvider.value, { api_key: apiKey.value.trim() })
    await fetchModels()
    markResolved('health:provider-empty')
    message.success(t('setup.provider.validated'))
  } catch (e: any) {
    message.error(e.message || t('setup.provider.validateFailed'))
  } finally {
    providerSaving.value = false
  }
}

// ─── Soul AI generation ───
function handleGenerateSoul() {
  if (!soulDescription.value.trim()) {
    message.warning(t('setup.soul.describeFirst'))
    return
  }
  soulGenerating.value = true

  generateSoul(soulDescription.value).then(({ content, error }) => {
    soulGenerating.value = false
    if (error) {
      message.error(error)
    } else if (content) {
      soulContent.value = content
      soulEditText.value = content
    }
  })
}

async function saveSoul() {
  const content = soulEditing.value ? soulEditText.value : soulContent.value
  if (!content?.trim()) return
  try {
    await saveMemory('soul', content)
    markResolved('health:soul-empty')
    message.success(t('setup.soul.saved'))
  } catch {
    message.error(t('setup.soul.saveFailed'))
  }
}

// ─── Generic inline actions ───
async function handleInlineAction(item: typeof items.value[0]) {
  const target = item.action?.target
  const payload = item.action?.payload

  if (target === 'memory') {
    try {
      await settingsStore.saveSection('memory', { memory_enabled: true })
      markResolved(item.id)
      message.success(t('common.saved'))
    } catch {
      message.error(t('common.saveFailed'))
    }
  } else if (target === 'agent.max_turns') {
    try {
      await settingsStore.saveSection('agent', { max_turns: payload?.value ?? 30 })
      markResolved(item.id)
      message.success(t('common.saved'))
    } catch {
      message.error(t('common.saveFailed'))
    }
  } else if (target === 'agent.gateway_timeout') {
    try {
      await settingsStore.saveSection('agent', { gateway_timeout: payload?.value ?? 120 })
      markResolved(item.id)
      message.success(t('common.saved'))
    } catch {
      message.error(t('common.saveFailed'))
    }
  }
}

function severityIcon(severity: string): string {
  switch (severity) {
    case 'error': return '✗'
    case 'warning': return '⚠'
    default: return 'ℹ'
  }
}
</script>

<template>
  <div v-if="!allResolved || hasIssues" class="setup-checklist" :class="{ collapsed }">
    <div class="checklist-header" @click="toggleCollapse">
      <span class="checklist-title">{{ t('setup.title') }}</span>
      <span class="checklist-progress">
        <template v-if="errorCount">{{ errorCount }} {{ t('setup.errors') }}</template>
        <template v-else-if="pendingCount">{{ pendingCount }} {{ t('setup.remaining') }}</template>
        <template v-else>{{ t('setup.allGood') }}</template>
      </span>
      <span class="checklist-toggle">{{ collapsed ? '▸' : '▾' }}</span>
    </div>

    <div v-if="!collapsed" class="checklist-body">
      <NSpin :show="loading" size="small">
        <div class="checklist-items">
          <div
            v-for="item in items"
            :key="item.id"
            class="checklist-item"
            :class="[item.severity, { expanded: expandedKey === item.id }]"
          >
            <div class="item-row" @click="item.action && toggleExpand(item.action.target || item.id)">
              <span class="item-icon" :class="item.severity">{{ severityIcon(item.severity) }}</span>
              <span class="item-label">{{ item.title }}</span>
              <span class="item-detail">{{ item.detail }}</span>

              <!-- Inline button for simple one-click actions -->
              <NButton
                v-if="item.action?.type === 'inline' && item.action.target !== 'provider' && item.action.target !== 'soul'"
                size="tiny"
                quaternary
                class="item-action-btn"
                @click.stop="handleInlineAction(item)"
              >
                {{ item.action.label }}
              </NButton>
              <!-- Navigate button -->
              <NButton
                v-else-if="item.action?.type === 'navigate'"
                size="tiny"
                quaternary
                class="item-action-btn"
                @click.stop="$router.push({ name: item.action.target as any })"
              >
                {{ item.action.label }}
              </NButton>
              <!-- Expand arrow for complex inline forms -->
              <span v-else-if="item.action && expandedKey !== item.id" class="item-action">→</span>
              <!-- Dismiss for info/warning -->
              <span
                v-if="item.severity !== 'error' && item.action?.type !== 'inline'"
                class="item-dismiss"
                @click.stop="dismiss(item.id)"
              >
                ×
              </span>
            </div>

            <!-- Provider inline form -->
            <div v-if="item.action?.target === 'provider' && expandedKey === 'provider'" class="item-form">
              <div class="form-row">
                <NSelect
                  v-model:value="selectedProvider"
                  :options="modelsStore.providers.map((p: any) => ({ label: p.label, value: p.provider }))"
                  :placeholder="t('setup.provider.select')"
                  size="small"
                  style="flex: 1"
                />
              </div>
              <div v-if="selectedProvider" class="form-row">
                <NInput
                  v-model:value="apiKey"
                  type="password"
                  show-password-on="click"
                  :placeholder="t('setup.provider.apiKey')"
                  size="small"
                  autocomplete="off"
                />
                <NButton type="primary" size="small" :loading="providerSaving" @click="saveProvider">
                  {{ t('setup.provider.validate') }}
                </NButton>
              </div>
            </div>

            <!-- Soul inline form -->
            <div v-if="(item.action?.target === 'soul') && expandedKey === 'soul'" class="item-form">
              <div class="preset-chips">
                <NButton
                  v-for="preset in SOUL_PRESETS"
                  :key="preset.key"
                  size="tiny"
                  quaternary
                  @click="soulDescription = preset.desc"
                >
                  {{ t(`onboarding.soul.presets.${preset.key}`) }}
                </NButton>
              </div>
              <NInput
                v-model:value="soulDescription"
                type="textarea"
                :rows="2"
                :placeholder="t('setup.soul.placeholder')"
                size="small"
              />
              <div class="form-actions">
                <NButton
                  type="primary"
                  size="small"
                  :loading="generating || soulGenerating"
                  :disabled="!soulDescription.trim()"
                  @click="handleGenerateSoul"
                >
                  {{ (generating || soulGenerating) ? t('setup.soul.generating') : t('setup.soul.generate') }}
                </NButton>
              </div>
              <!-- Streaming preview -->
              <div v-if="generating && streamContent" class="soul-preview streaming">
                <pre>{{ streamContent }}</pre>
              </div>
              <!-- Generated content -->
              <div v-if="soulContent && !generating" class="soul-preview">
                <div class="preview-header">
                  <span>{{ t('setup.soul.preview') }}</span>
                  <div class="preview-actions">
                    <NButton size="tiny" @click="handleGenerateSoul">{{ t('setup.soul.regenerate') }}</NButton>
                    <NButton size="tiny" @click="soulEditing = !soulEditing">
                      {{ soulEditing ? t('setup.soul.preview') : t('common.edit') }}
                    </NButton>
                  </div>
                </div>
                <pre v-if="!soulEditing">{{ soulContent }}</pre>
                <div v-else>
                  <NInput v-model:value="soulEditText" type="textarea" :rows="8" />
                </div>
                <NButton type="primary" size="small" @click="saveSoul">{{ t('common.save') }}</NButton>
              </div>
            </div>
          </div>
        </div>
      </NSpin>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.setup-checklist {
  border-bottom: 1px solid $border-light;
  background: $bg-card;
  transition: all $transition-normal;

  &.collapsed .checklist-header {
    border-bottom: none;
  }
}

.checklist-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  cursor: pointer;
  user-select: none;
  border-bottom: 1px solid $border-light;

  &:hover { background: $bg-card-hover; }
}

.checklist-title {
  font-size: 13px;
  font-weight: 600;
  color: $text-primary;
}

.checklist-progress {
  font-size: 11px;

  .error & { color: $error; }
  &:not(.error &) { color: $warning; }
}

.checklist-toggle {
  margin-left: auto;
  font-size: 12px;
  color: $text-muted;
}

.checklist-body { padding: 8px 16px 12px; }

.checklist-items {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.checklist-item {
  border-radius: $radius-sm;
  transition: background $transition-fast;

  &.error .item-icon { color: $error; }
  &.warning .item-icon { color: $warning; }
  &.info .item-icon { color: $text-muted; }

  &.expanded { background: $bg-secondary; }
}

.item-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  cursor: pointer;

  .checklist-item.info & { cursor: default; }
}

.item-icon {
  font-size: 14px;
  width: 16px;
  text-align: center;
  flex-shrink: 0;
}

.item-label {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}

.item-detail {
  font-size: 11px;
  color: $text-muted;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-action {
  font-size: 12px;
  color: $text-muted;
  flex-shrink: 0;
}

.item-action-btn { flex-shrink: 0; }

.item-dismiss {
  font-size: 14px;
  color: $text-muted;
  cursor: pointer;
  padding: 0 4px;
  flex-shrink: 0;

  &:hover { color: $text-secondary; }
}

.item-form {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.form-actions { display: flex; gap: 8px; }

.preset-chips {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.soul-preview {
  margin-top: 4px;
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  overflow: hidden;

  &.streaming { border-color: $accent-muted; }

  pre {
    padding: 8px;
    font-size: 12px;
    white-space: pre-wrap;
    max-height: 200px;
    overflow-y: auto;
    margin: 0;
  }
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 8px;
  background: $bg-secondary;
  font-size: 11px;
}

.preview-actions { display: flex; gap: 4px; }
</style>
```

**Step 2: Verify TypeScript compiles**

Run: `npx vue-tsc --noEmit`
Expected: No type errors

**Step 3: Commit**

```bash
git add packages/client/src/components/hermes/chat/SetupChecklist.vue
git commit -m "feat: upgrade SetupChecklist to use useSmartConfig dynamic rendering"
```

---

## Task 9: Frontend — Add i18n keys

**Files:**
- Modify: `packages/client/src/i18n/locales/en.ts`
- Modify: `packages/client/src/i18n/locales/zh.ts`
- Modify: all other locale files

**Step 1: Add setup section to en.ts**

Find the existing `setup` section in `en.ts` and ensure these keys exist:

```typescript
setup: {
  title: 'Config Status',
  errors: 'issues',
  remaining: 'remaining',
  allGood: 'All configured',
  provider: {
    select: 'Select provider...',
    apiKey: 'API Key',
    validate: 'Validate',
    validated: 'Provider connected!',
    validateFailed: 'Validation failed',
  },
  soul: {
    placeholder: 'Describe your assistant, e.g. "A customer service agent for e-commerce"',
    generate: 'AI Generate',
    generating: 'Generating...',
    preview: 'Preview',
    regenerate: 'Regenerate',
    saved: 'SOUL.md saved',
    saveFailed: 'Failed to save',
    describeFirst: 'Please describe your assistant',
  },
  memory: {
    hint: 'Enable memory so the agent remembers context across sessions.',
    enable: 'Enable Memory',
  },
  platforms: {
    hint: 'Connect messaging platforms in Settings.',
    goSettings: 'Open Settings',
  },
},
```

**Step 2: Add setup section to zh.ts**

```typescript
setup: {
  title: '配置状态',
  errors: '个问题',
  remaining: '项待完成',
  allGood: '配置完成',
  provider: {
    select: '选择提供商...',
    apiKey: 'API Key',
    validate: '验证',
    validated: '提供商已连接！',
    validateFailed: '验证失败',
  },
  soul: {
    placeholder: '描述你的助手，例如"电商平台的客服助手"',
    generate: 'AI 生成',
    generating: '生成中...',
    preview: '预览',
    regenerate: '重新生成',
    saved: 'SOUL.md 已保存',
    saveFailed: '保存失败',
    describeFirst: '请先描述你的助手',
  },
  memory: {
    hint: '启用记忆功能，让助手在会话间保留上下文。',
    enable: '启用记忆',
  },
  platforms: {
    hint: '在设置中连接消息平台。',
    goSettings: '打开设置',
  },
},
```

**Step 3: Add English fallback to de.ts, es.ts, fr.ts, ja.ts, ko.ts, pt.ts**

Use the English version as placeholder for each locale file that doesn't have native translations.

**Step 4: Verify TypeScript compiles**

Run: `npx vue-tsc --noEmit`
Expected: No type errors

**Step 5: Commit**

```bash
git add packages/client/src/i18n/locales/
git commit -m "feat: add smart config i18n keys to all locales"
```

---

## Task 10: Frontend — Delete useSetupStatus.ts

**Files:**
- Delete: `packages/client/src/composables/useSetupStatus.ts`

**Step 1: Verify no other file imports useSetupStatus**

Run: `grep -r "useSetupStatus" packages/client/src/`
Expected: No results (SetupChecklist was rewritten in Task 8 to use useSmartConfig instead)

**Step 2: Delete the file**

```bash
rm packages/client/src/composables/useSetupStatus.ts
```

**Step 3: Verify TypeScript compiles**

Run: `npx vue-tsc --noEmit`
Expected: No type errors

**Step 4: Commit**

```bash
git add -A
git commit -m "refactor: remove useSetupStatus (replaced by useConfigHealth)"
```

---

## Task 11: E2E verification

**Step 1: Start dev server**

Run: `npm run dev`

**Step 2: Test scenarios**

1. Navigate to `/hermes/chat`
2. Verify SetupChecklist renders with dynamic items from useSmartConfig
3. If Provider not configured: should show error item with expand → inline form
4. Click Provider → select provider → enter API key → validate → item resolves
5. If .env has Telegram token but config doesn't enable: should show warning from backend
6. SOUL.md empty: warning item with AI Generate action
7. Configure SOUL.md → item resolves
8. Info-level suggestions appear if conditions met (multi-platform, coding soul, etc.)
9. Dismiss info/warning items → persists across page refresh
10. Error items cannot be dismissed
11. Settings page still works
12. Navigate away and back → checklist state preserved

**Step 3: Type check**

Run: `npm run build`
Expected: Build succeeds with no type errors

**Step 4: Final commit**

```bash
git commit --allow-empty -m "test: e2e verification passed for smart config guidance layer"
```

---

## Execution Notes

- **Dependencies:** Tasks 1-2 (backend) are independent of Tasks 3-7 (frontend composables). They can be parallelized.
- **Critical path:** Tasks 1+2 → Task 8 (SetupChecklist needs backend + all composables) → Task 9 (i18n) → Task 10 (cleanup) → Task 11 (verify)
- **Task 8 depends on:** Tasks 3, 4, 5, 6, 7 (all composables + type must exist)
- **Rollback:** Each task is a separate commit. Revert any task independently.
- **No database changes.** No new npm dependencies. All backend logic uses existing functions.
