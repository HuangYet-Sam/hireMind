# Onboarding Wizard + Smart Configuration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a three-layer intelligent configuration guidance system (Onboarding Wizard + Health Dashboard + Smart Suggestions) for Hermes Web UI.

**Architecture:** Full-screen 4-step wizard triggered on first login, folding into a health check card in SettingsView post-completion. AI generation calls the existing Hermes gateway chat API (Socket.IO runs). No new backend endpoints needed.

**Tech Stack:** Vue 3 Composition API, Naive UI, Pinia, vue-i18n, Socket.IO client, TypeScript

---

## Task 1: Add `onboarding_done` to DisplayConfig type

**Files:**
- Modify: `packages/client/src/api/hermes/config.ts:9` (DisplayConfig interface)
- Modify: `packages/client/src/stores/hermes/settings.ts` (expose onboardingDone)

**Step 1: Update DisplayConfig interface**

In `packages/client/src/api/hermes/config.ts`, add `onboarding_done` to `DisplayConfig`:

```typescript
// packages/client/src/api/hermes/config.ts line 9
export interface DisplayConfig {
  compact?: boolean
  personality?: string
  resume_display?: string
  busy_input_mode?: string
  bell_on_complete?: boolean
  show_reasoning?: boolean
  streaming?: boolean
  inline_diffs?: boolean
  show_cost?: boolean
  skin?: string
  onboarding_done?: boolean  // ADD THIS
}
```

**Step 2: Expose `onboardingDone` computed in settings store**

In `packages/client/src/stores/hermes/settings.ts`, add a computed after `display` ref:

```typescript
import { ref, computed } from 'vue'

// Inside the store function, after display ref:
const onboardingDone = computed(() => !!display.value?.onboarding_done)

// Add to return:
return {
  // ...existing
  onboardingDone,
}
```

**Step 3: Verify type-check passes**

Run: `cd packages/client && npx vue-tsc --noEmit`
Expected: No type errors

**Step 4: Commit**

```bash
git add packages/client/src/api/hermes/config.ts packages/client/src/stores/hermes/settings.ts
git commit -m "feat: add onboarding_done to DisplayConfig type"
```

---

## Task 2: Add onboarding route + router redirect logic

**Files:**
- Modify: `packages/client/src/router/index.ts`

**Step 1: Add onboarding route**

In `packages/client/src/router/index.ts`, add after the `login` route (line ~9):

```typescript
{
  path: '/hermes/onboarding',
  name: 'hermes.onboarding',
  component: () => import('@/views/hermes/OnboardingView.vue'),
},
```

**Step 2: Add onboarding redirect guard in `beforeEach`**

In the router's `beforeEach` guard, after the auth check (`if (!hasApiKey())`) and before the final `next()`, add:

```typescript
// Check onboarding status for authenticated users
const settingsStore = await import('@/stores/hermes/settings').then(m => m.useSettingsStore())
const store = settingsStore()
if (!store.onboardingDone && to.name !== 'hermes.onboarding') {
  await store.fetchSettings()
  if (!store.onboardingDone) {
    next({ name: 'hermes.onboarding' })
    return
  }
}
if (store.onboardingDone && to.name === 'hermes.onboarding') {
  next({ name: 'hermes.chat' })
  return
}
```

Wait — the `beforeEach` is synchronous. Use a flag approach instead:

```typescript
router.beforeEach(async (to, _from, next) => {
  if (to.meta.public) {
    if (to.name === 'login' && hasApiKey()) {
      next({ path: '/hermes/chat' })
      return
    }
    next()
    return
  }
  if (!hasApiKey()) {
    next({ name: 'login' })
    return
  }

  // Onboarding redirect (only check once per session)
  if (to.name !== 'hermes.onboarding' && !sessionStorage.getItem('hermes_onboarding_checked')) {
    try {
      const { useSettingsStore } = await import('@/stores/hermes/settings')
      const store = useSettingsStore()
      if (!store.onboardingDone) {
        await store.fetchSettings()
        if (!store.onboardingDone) {
          next({ name: 'hermes.onboarding' })
          return
        }
      }
      sessionStorage.setItem('hermes_onboarding_checked', '1')
    } catch {
      // If config fetch fails, let user proceed normally
    }
  }

  next()
})
```

**Step 3: Verify route loads without error**

The `OnboardingView.vue` doesn't exist yet — this is expected to fail. Just verify TypeScript compiles:
Run: `cd packages/client && npx vue-tsc --noEmit`

**Step 4: Commit**

```bash
git add packages/client/src/router/index.ts
git commit -m "feat: add onboarding route and redirect guard"
```

---

## Task 3: Create OnboardingView.vue placeholder

**Files:**
- Create: `packages/client/src/views/hermes/OnboardingView.vue`

**Step 1: Create placeholder view**

```vue
<script setup lang="ts">
import { useRouter } from 'vue-router'
import OnboardingWizard from '@/components/hermes/onboarding/OnboardingWizard.vue'

const router = useRouter()

function handleComplete() {
  router.replace({ name: 'hermes.chat' })
}
</script>

<template>
  <div class="onboarding-view">
    <OnboardingWizard @complete="handleComplete" />
  </div>
</template>

<style scoped lang="scss">
.onboarding-view {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--n-color);
}
</style>
```

**Step 2: Commit**

```bash
git add packages/client/src/views/hermes/OnboardingView.vue
git commit -m "feat: add OnboardingView placeholder"
```

---

## Task 4: Create `useAIGeneration` composable

**Files:**
- Create: `packages/client/src/components/hermes/onboarding/composables/useAIGeneration.ts`

This composable wraps the Socket.IO chat run API to generate SOUL.md content and config recommendations.

**Step 1: Write the composable**

```typescript
import { ref } from 'vue'
import { startRunViaSocket, connectChatRun, disconnectChatRun } from '@/api/hermes/chat'
import { saveMemory } from '@/api/hermes/skills'

const SOUL_SYSTEM_PROMPT = `You are a SOUL.md generator for Hermes AI Agent.
Given the user's description of their desired assistant, generate a complete SOUL.md file.
Format: Markdown with clear sections (# Role, # Personality, # Guidelines, # Constraints).
Be specific, actionable, and professional. Output ONLY the SOUL.md content, no explanations.`

const CONFIG_SYSTEM_PROMPT = `You are a configuration optimizer for Hermes AI Agent.
Given the SOUL.md content, connected platforms, and current config, recommend optimal settings.
Return a JSON object with this structure:
{
  "agent": { "max_turns": number, "gateway_timeout": number },
  "memory": { "memory_enabled": boolean, "memory_char_limit": number },
  "display": {},
  "platforms": { "<platform>": { "<key>": <value> } },
  "reasons": { "<section>.<key>": "reason string" }
}
Output ONLY valid JSON, no markdown fences.`

interface GeneratedSoul {
  content: string
  error: string | null
}

interface ConfigRecommendation {
  config: Record<string, any>
  reasons: Record<string, string>
  error: string | null
}

export function useAIGeneration() {
  const generating = ref(false)
  const streaming = ref(false)
  const streamContent = ref('')

  function generateSoul(userDescription: string): Promise<GeneratedSoul> {
    return new Promise((resolve) => {
      generating.value = true
      streamContent.value = ''

      let accumulated = ''

      const { abort } = startRunViaSocket(
        {
          input: `Generate a SOUL.md for: ${userDescription}`,
          instructions: SOUL_SYSTEM_PROMPT,
          session_id: `onboarding-soul-${Date.now()}`,
        },
        (event) => {
          if (event.delta) {
            accumulated += event.delta
            streamContent.value = accumulated
          }
          if (event.output) {
            accumulated = event.output
            streamContent.value = accumulated
          }
        },
        () => {
          generating.value = false
          streaming.value = false
          resolve({ content: accumulated, error: null })
        },
        (err) => {
          generating.value = false
          streaming.value = false
          resolve({ content: '', error: err.message })
        },
      )
    })
  }

  function recommendConfig(
    soulContent: string,
    platforms: string[],
    currentConfig: Record<string, any>,
  ): Promise<ConfigRecommendation> {
    return new Promise((resolve) => {
      generating.value = true
      streamContent.value = ''

      const userInput = JSON.stringify({
        soul: soulContent.substring(0, 2000),
        platforms,
        currentConfig,
      })

      let accumulated = ''

      const { abort } = startRunViaSocket(
        {
          input: `Analyze and recommend configuration:\n${userInput}`,
          instructions: CONFIG_SYSTEM_PROMPT,
          session_id: `onboarding-config-${Date.now()}`,
        },
        (event) => {
          if (event.delta) {
            accumulated += event.delta
            streamContent.value = accumulated
          }
          if (event.output) {
            accumulated = event.output
            streamContent.value = accumulated
          }
        },
        () => {
          generating.value = false
          try {
            // Strip markdown fences if present
            const clean = accumulated.replace(/^```json?\n?/m, '').replace(/\n?```$/m, '').trim()
            const parsed = JSON.parse(clean)
            resolve({
              config: {
                agent: parsed.agent || {},
                memory: parsed.memory || {},
                display: parsed.display || {},
                platforms: parsed.platforms || {},
              },
              reasons: parsed.reasons || {},
              error: null,
            })
          } catch {
            resolve({ config: {}, reasons: {}, error: 'Failed to parse AI response' })
          }
        },
        (err) => {
          generating.value = false
          resolve({ config: {}, reasons: {}, error: err.message })
        },
      )
    })
  }

  async function saveSoulContent(content: string) {
    await saveMemory('soul', content)
  }

  return {
    generating,
    streaming,
    streamContent,
    generateSoul,
    recommendConfig,
    saveSoulContent,
  }
}
```

**Step 2: Commit**

```bash
git add packages/client/src/components/hermes/onboarding/composables/useAIGeneration.ts
git commit -m "feat: add useAIGeneration composable for soul/config generation"
```

---

## Task 5: Create `useHealthCheck` composable

**Files:**
- Create: `packages/client/src/components/hermes/onboarding/composables/useHealthCheck.ts`

**Step 1: Write the composable**

```typescript
import { ref, computed } from 'vue'
import { fetchModels } from '@/api/hermes/chat'
import { fetchMemory } from '@/api/hermes/skills'
import { fetchDetailedHealth } from '@/api/hermes/health'
import { fetchConfig } from '@/api/hermes/config'

export interface HealthItem {
  key: string
  label: string
  status: 'ok' | 'warning' | 'error'
  message: string
  action?: { label: string; section: string }
}

export function useHealthCheck() {
  const loading = ref(false)
  const items = ref<HealthItem[]>([])

  const healthy = computed(() => items.value.every(i => i.status === 'ok'))
  const warnings = computed(() => items.value.filter(i => i.status === 'warning' || i.status === 'error'))

  async function runChecks() {
    loading.value = true
    const results: HealthItem[] = []

    // Check 1: AI Provider connectivity
    try {
      await fetchModels()
      results.push({
        key: 'provider',
        label: 'AI Provider',
        status: 'ok',
        message: 'Connected and models available',
      })
    } catch {
      results.push({
        key: 'provider',
        label: 'AI Provider',
        status: 'error',
        message: 'No AI provider configured or unreachable',
        action: { label: 'Configure', section: 'models' },
      })
    }

    // Check 2: SOUL.md
    try {
      const mem = await fetchMemory()
      if (mem.soul && mem.soul.trim().length > 10) {
        results.push({
          key: 'soul',
          label: 'SOUL.md',
          status: 'ok',
          message: 'Agent personality defined',
        })
      } else {
        results.push({
          key: 'soul',
          label: 'SOUL.md',
          status: 'warning',
          message: 'Agent personality is empty — define it for better results',
          action: { label: 'Define', section: 'memory' },
        })
      }
    } catch {
      results.push({
        key: 'soul',
        label: 'SOUL.md',
        status: 'warning',
        message: 'Could not check soul status',
      })
    }

    // Check 3: Platform connections
    try {
      const health = await fetchDetailedHealth()
      const platforms = Object.entries(health.platforms || {})
      const connected = platforms.filter(([, info]) => info.state === 'running')
      const errored = platforms.filter(([, info]) => info.state === 'error')

      if (connected.length > 0) {
        results.push({
          key: 'platforms',
          label: 'Platforms',
          status: errored.length > 0 ? 'warning' : 'ok',
          message: `${connected.length}/${platforms.length} platform(s) connected${errored.length > 0 ? ` (${errored.length} error(s))` : ''}`,
        })
      } else if (platforms.length > 0) {
        results.push({
          key: 'platforms',
          label: 'Platforms',
          status: 'warning',
          message: 'No platforms currently connected',
          action: { label: 'Configure', section: 'platforms' },
        })
      }
    } catch {
      // Gateway not running — not an error per se
      results.push({
        key: 'platforms',
        label: 'Platforms',
        status: 'ok',
        message: 'No platforms configured (optional)',
      })
    }

    // Check 4: Memory enabled
    try {
      const config = await fetchConfig(['memory'])
      if (config.memory?.memory_enabled) {
        results.push({
          key: 'memory',
          label: 'Memory',
          status: 'ok',
          message: 'Context memory enabled',
        })
      } else {
        results.push({
          key: 'memory',
          label: 'Memory',
          status: 'warning',
          message: 'Memory disabled — agent won\'t remember context across sessions',
          action: { label: 'Enable', section: 'memory' },
        })
      }
    } catch {
      // Ignore
    }

    items.value = results
    loading.value = false
  }

  return { loading, items, healthy, warnings, runChecks }
}
```

**Step 2: Commit**

```bash
git add packages/client/src/components/hermes/onboarding/composables/useHealthCheck.ts
git commit -m "feat: add useHealthCheck composable"
```

---

## Task 6: Create `useSmartSuggestions` composable

**Files:**
- Create: `packages/client/src/components/hermes/onboarding/composables/useSmartSuggestions.ts`

**Step 1: Write the composable**

```typescript
import { ref, watch } from 'vue'
import { useAppStore } from '@/stores/hermes/app'
import { useSettingsStore } from '@/stores/hermes/settings'

export interface Suggestion {
  id: string
  type: 'info' | 'warning' | 'success'
  title: string
  message: string
  actionLabel?: string
  actionRoute?: string
}

export function useSmartSuggestions() {
  const suggestions = ref<Suggestion[]>([])
  const dismissed = ref<Set<string>>(new Set())

  function refresh() {
    const appStore = useAppStore()
    const settingsStore = useSettingsStore()
    const newSuggestions: Suggestion[] = []

    // Rule: Multiple platforms connected without memory
    const platformCount = Object.keys(appStore.connectedPlatforms).length
    if (platformCount > 1 && !settingsStore.memory?.memory_enabled) {
      newSuggestions.push({
        id: 'enable-memory-multi-platform',
        type: 'info',
        title: 'Enable Memory',
        message: `${platformCount} platforms connected. Enabling memory helps maintain context across platforms.`,
        actionLabel: 'Enable Memory',
        actionRoute: 'hermes.settings',
      })
    }

    // Rule: No provider configured
    if (appStore.modelGroups.length === 0) {
      newSuggestions.push({
        id: 'no-provider',
        type: 'warning',
        title: 'No AI Provider',
        message: 'No model provider is configured. Set up an API key to start using Hermes.',
        actionLabel: 'Configure',
        actionRoute: 'hermes.onboarding',
      })
    }

    // Rule: Gateway not running
    if (appStore.gatewayState === 'stopped' && platformCount > 0) {
      newSuggestions.push({
        id: 'gateway-stopped',
        type: 'warning',
        title: 'Gateway Stopped',
        message: 'Hermes gateway is not running. Connected platforms will not receive messages.',
        actionLabel: 'Start Gateway',
        actionRoute: 'hermes.gateways',
      })
    }

    // Filter dismissed
    suggestions.value = newSuggestions.filter(s => !dismissed.value.has(s.id))
  }

  function dismiss(id: string) {
    dismissed.value.add(id)
    suggestions.value = suggestions.value.filter(s => s.id !== id)
  }

  return { suggestions, refresh, dismiss }
}
```

**Step 2: Commit**

```bash
git add packages/client/src/components/hermes/onboarding/composables/useSmartSuggestions.ts
git commit -m "feat: add useSmartSuggestions composable"
```

---

## Task 7: Create ProviderStep.vue (Step 1)

**Files:**
- Create: `packages/client/src/components/hermes/onboarding/steps/ProviderStep.vue`

This step reuses the ModelSettings provider pattern — select provider, enter API key, validate.

**Step 1: Write the component**

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NSelect, NInput, NButton, NSpin, NAlert, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useModelsStore } from '@/stores/hermes/models'
import { updateProvider } from '@/api/hermes/system'
import { fetchModels } from '@/api/hermes/chat'

const emit = defineEmits<{
  (e: 'next'): void
}>()

const { t } = useI18n()
const message = useMessage()
const modelsStore = useModelsStore()

const selectedProvider = ref<string | null>(null)
const apiKey = ref('')
const saving = ref(false)
const validating = ref(false)
const validated = ref(false)

onMounted(() => {
  if (modelsStore.providers.length === 0) {
    modelsStore.fetchProviders()
  }
})

const providerOptions = computed(() =>
  modelsStore.providers.map(p => ({
    label: p.label,
    value: p.provider,
  })),
)

async function saveAndValidate() {
  if (!selectedProvider.value || !apiKey.value.trim()) {
    message.warning(t('onboarding.provider.keyRequired'))
    return
  }
  saving.value = true
  try {
    await updateProvider(selectedProvider.value, { api_key: apiKey.value.trim() })
    await modelsStore.fetchProviders()

    // Validate by fetching models
    validating.value = true
    await fetchModels()
    validated.value = true
    message.success(t('onboarding.provider.validated'))
  } catch (e: any) {
    message.error(e.message || t('onboarding.provider.validateFailed'))
    validated.value = false
  } finally {
    saving.value = false
    validating.value = false
  }
}

async function handleNext() {
  if (!validated.value) {
    await saveAndValidate()
    if (validated.value) emit('next')
    return
  }
  emit('next')
}
</script>

<template>
  <div class="provider-step">
    <h3 class="step-title">{{ t('onboarding.provider.title') }}</h3>
    <p class="step-desc">{{ t('onboarding.provider.desc') }}</p>

    <NSpin :show="modelsStore.loading">
      <div class="form-fields">
        <div class="field">
          <label>{{ t('onboarding.provider.select') }}</label>
          <NSelect
            v-model:value="selectedProvider"
            :options="providerOptions"
            :placeholder="t('onboarding.provider.selectPlaceholder')"
          />
        </div>

        <div v-if="selectedProvider" class="field">
          <label>{{ t('onboarding.provider.apiKey') }}</label>
          <NInput
            v-model:value="apiKey"
            type="password"
            show-password-on="click"
            :placeholder="t('onboarding.provider.keyPlaceholder')"
            autocomplete="off"
          />
        </div>

        <NButton
          v-if="selectedProvider && apiKey && !validated"
          type="primary"
          :loading="saving || validating"
          @click="saveAndValidate"
        >
          {{ validating ? t('onboarding.provider.validating') : t('onboarding.provider.validate') }}
        </NButton>

        <NAlert v-if="validated" type="success" :show-icon="true" :bordered="false">
          {{ t('onboarding.provider.validated') }}
        </NAlert>
      </div>
    </NSpin>

    <div class="step-actions">
      <div />
      <NButton type="primary" :disabled="!validated" @click="handleNext">
        {{ t('onboarding.next') }}
      </NButton>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.provider-step {
  max-width: 520px;
  margin: 0 auto;
}

.step-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 8px;
}

.step-desc {
  color: $text-secondary;
  margin: 0 0 24px;
  font-size: 14px;
}

.form-fields {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;

  label {
    font-size: 13px;
    font-weight: 500;
  }
}

.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 32px;
}
</style>
```

Note: This file uses `computed` from Vue — add `import { computed } from 'vue'` to the import line at the top.

**Step 2: Commit**

```bash
git add packages/client/src/components/hermes/onboarding/steps/ProviderStep.vue
git commit -m "feat: add ProviderStep component for onboarding wizard"
```

---

## Task 8: Create SoulStep.vue (Step 2)

**Files:**
- Create: `packages/client/src/components/hermes/onboarding/steps/SoulStep.vue`

**Step 1: Write the component**

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { NInput, NButton, NAlert, NSpin, NGrid, NGi, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useAIGeneration } from '../composables/useAIGeneration'

const emit = defineEmits<{
  (e: 'next'): void
  (e: 'update:soul', content: string): void
}>()

const { t } = useI18n()
const message = useMessage()
const { generating, streamContent, generateSoul, saveSoulContent } = useAIGeneration()

const userDescription = ref('')
const soulContent = ref('')
const isEditing = ref(false)
const editContent = ref('')

const PRESETS = [
  { key: 'customer-service', label: t('onboarding.soul.presets.customerService') },
  { key: 'coding', label: t('onboarding.soul.presets.coding') },
  { key: 'writing', label: t('onboarding.soul.presets.writing') },
  { key: 'general', label: t('onboarding.soul.presets.general') },
]

const PRESET_DESCRIPTIONS: Record<string, string> = {
  'customer-service': t('onboarding.soul.presetDesc.customerService'),
  'coding': t('onboarding.soul.presetDesc.coding'),
  'writing': t('onboarding.soul.presetDesc.writing'),
  'general': t('onboarding.soul.presetDesc.general'),
}

function selectPreset(key: string) {
  userDescription.value = PRESET_DESCRIPTIONS[key] || ''
}

async function handleGenerate() {
  if (!userDescription.value.trim()) {
    message.warning(t('onboarding.soul.describeFirst'))
    return
  }
  const result = await generateSoul(userDescription.value)
  if (result.error) {
    message.error(result.error)
    return
  }
  soulContent.value = result.content
  editContent.value = result.content
  emit('update:soul', result.content)
}

function startEdit() {
  editContent.value = soulContent.value
  isEditing.value = true
}

function saveEdit() {
  soulContent.value = editContent.value
  isEditing.value = false
  emit('update:soul', soulContent.value)
}

async function handleNext() {
  if (soulContent.value) {
    try {
      await saveSoulContent(soulContent.value)
      message.success(t('onboarding.soul.saved'))
    } catch {
      message.error(t('onboarding.soul.saveFailed'))
      return
    }
  }
  emit('next')
}
</script>

<template>
  <div class="soul-step">
    <h3 class="step-title">{{ t('onboarding.soul.title') }}</h3>
    <p class="step-desc">{{ t('onboarding.soul.desc') }}</p>

    <!-- Preset chips -->
    <div class="preset-chips">
      <NButton
        v-for="preset in PRESETS"
        :key="preset.key"
        size="small"
        quaternary
        @click="selectPreset(preset.key)"
      >
        {{ preset.label }}
      </NButton>
    </div>

    <!-- Description input -->
    <NInput
      v-model:value="userDescription"
      type="textarea"
      :rows="3"
      :placeholder="t('onboarding.soul.placeholder')"
      class="desc-input"
    />

    <NButton
      type="primary"
      :loading="generating"
      :disabled="!userDescription.trim()"
      @click="handleGenerate"
    >
      {{ generating ? t('onboarding.soul.generating') : t('onboarding.soul.generate') }}
    </NButton>

    <!-- Streaming preview -->
    <div v-if="generating && streamContent" class="preview-box streaming">
      <pre>{{ streamContent }}</pre>
    </div>

    <!-- Generated content preview / edit -->
    <div v-if="soulContent && !generating" class="preview-box">
      <div class="preview-header">
        <span>{{ t('onboarding.soul.preview') }}</span>
        <div class="preview-actions">
          <NButton size="tiny" @click="handleGenerate">{{ t('onboarding.soul.regenerate') }}</NButton>
          <NButton size="tiny" @click="startEdit">{{ t('common.edit') }}</NButton>
        </div>
      </div>
      <div v-if="!isEditing" class="preview-content">
        <pre>{{ soulContent }}</pre>
      </div>
      <div v-else class="edit-area">
        <NInput v-model:value="editContent" type="textarea" :rows="12" />
        <NButton type="primary" size="small" style="margin-top: 8px" @click="saveEdit">
          {{ t('common.save') }}
        </NButton>
      </div>
    </div>

    <div class="step-actions">
      <div />
      <NButton type="primary" @click="handleNext">
        {{ soulContent ? t('onboarding.next') : t('onboarding.skip') }}
      </NButton>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.soul-step {
  max-width: 640px;
  margin: 0 auto;
}

.step-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 8px;
}

.step-desc {
  color: $text-secondary;
  margin: 0 0 16px;
  font-size: 14px;
}

.preset-chips {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.desc-input {
  margin-bottom: 12px;
}

.preview-box {
  margin-top: 16px;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  overflow: hidden;

  &.streaming {
    border-color: $accent-primary;
  }
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: $bg-card;
  font-size: 13px;
  font-weight: 500;
}

.preview-actions {
  display: flex;
  gap: 4px;
}

.preview-content pre,
.edit-area {
  padding: 12px;
  font-size: 13px;
  white-space: pre-wrap;
  max-height: 400px;
  overflow-y: auto;
}

.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 32px;
}
</style>
```

**Step 2: Commit**

```bash
git add packages/client/src/components/hermes/onboarding/steps/SoulStep.vue
git commit -m "feat: add SoulStep component with AI generation"
```

---

## Task 9: Create PlatformStep.vue (Step 3)

**Files:**
- Create: `packages/client/src/components/hermes/onboarding/steps/PlatformStep.vue`

**Step 1: Write the component**

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { NInput, NButton, NGrid, NGi, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useSettingsStore } from '@/stores/hermes/settings'
import { saveCredentials } from '@/api/hermes/config'

const emit = defineEmits<{
  (e: 'next'): void
  (e: 'update:platforms', platforms: string[]): void
}>()

const { t } = useI18n()
const message = useMessage()
const settingsStore = useSettingsStore()

const MAJOR_PLATFORMS = [
  { key: 'telegram', label: 'Telegram', fields: ['token'] },
  { key: 'discord', label: 'Discord', fields: ['token'] },
  { key: 'slack', label: 'Slack', fields: ['bot_token', 'app_token'] },
  { key: 'whatsapp', label: 'WhatsApp', fields: ['phone_number', 'api_token'] },
  { key: 'wecom', label: 'WeCom', fields: ['corp_id', 'agent_id', 'secret'] },
  { key: 'feishu', label: 'Feishu', fields: ['app_id', 'app_secret'] },
]

const selectedPlatform = ref<string | null>(null)
const configuredPlatforms = ref<string[]>([])
const creds = ref<Record<string, Record<string, string>>>({})
const saving = ref(false)

function selectPlatform(key: string) {
  if (selectedPlatform.value === key) {
    selectedPlatform.value = null
    return
  }
  selectedPlatform.value = key
  if (!creds.value[key]) {
    const platform = MAJOR_PLATFORMS.find(p => p.key === key)
    creds.value[key] = {}
    for (const f of platform?.fields || []) {
      creds.value[key][f] = ''
    }
  }
}

async function savePlatformCreds(platform: string) {
  saving.value = true
  try {
    await saveCredentials(platform, creds.value[platform])
    if (!configuredPlatforms.value.includes(platform)) {
      configuredPlatforms.value.push(platform)
    }
    emit('update:platforms', configuredPlatforms.value)
    message.success(t('onboarding.platform.saved', { platform }))
  } catch {
    message.error(t('onboarding.platform.saveFailed'))
  } finally {
    saving.value = false
  }
}

function handleNext() {
  emit('next')
}
</script>

<template>
  <div class="platform-step">
    <h3 class="step-title">{{ t('onboarding.platform.title') }}</h3>
    <p class="step-desc">{{ t('onboarding.platform.desc') }}</p>

    <div class="platform-grid">
      <div
        v-for="platform in MAJOR_PLATFORMS"
        :key="platform.key"
        class="platform-card"
        :class="{ selected: selectedPlatform === platform.key, configured: configuredPlatforms.includes(platform.key) }"
        @click="selectPlatform(platform.key)"
      >
        <span class="platform-label">{{ platform.label }}</span>
        <span v-if="configuredPlatforms.includes(platform.key)" class="check">✓</span>
      </div>
    </div>

    <!-- Inline config form for selected platform -->
    <div v-if="selectedPlatform" class="platform-config">
      <h4>{{ MAJOR_PLATFORMS.find(p => p.key === selectedPlatform)?.label }}</h4>
      <div class="config-fields">
        <div v-for="field in MAJOR_PLATFORMS.find(p => p.key === selectedPlatform)?.fields" :key="field" class="field">
          <label>{{ field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) }}</label>
          <NInput
            v-model:value="creds[selectedPlatform][field]"
            type="password"
            show-password-on="click"
            :placeholder="field"
            autocomplete="off"
          />
        </div>
        <NButton type="primary" size="small" :loading="saving" @click="savePlatformCreds(selectedPlatform)">
          {{ t('onboarding.platform.save') }}
        </NButton>
      </div>
    </div>

    <div class="step-actions">
      <div />
      <NButton type="primary" @click="handleNext">
        {{ t('onboarding.platform.next') }}
      </NButton>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.platform-step {
  max-width: 640px;
  margin: 0 auto;
}

.step-title { font-size: 20px; font-weight: 600; margin: 0 0 8px; }
.step-desc { color: $text-secondary; margin: 0 0 16px; font-size: 14px; }

.platform-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}

.platform-card {
  padding: 12px;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;

  &:hover { border-color: $text-secondary; }
  &.selected { border-color: $accent-primary; background: rgba($accent-primary, 0.05); }
  &.configured { border-color: $success; }
}

.platform-label { font-size: 14px; font-weight: 500; }

.check {
  position: absolute;
  top: 4px;
  right: 8px;
  color: $success;
  font-weight: bold;
}

.platform-config {
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: 16px;
  margin-bottom: 16px;
  background: $bg-card;

  h4 { margin: 0 0 12px; font-size: 15px; }
}

.config-fields {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  label { font-size: 12px; color: $text-secondary; }
}

.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 32px;
}
</style>
```

**Step 2: Commit**

```bash
git add packages/client/src/components/hermes/onboarding/steps/PlatformStep.vue
git commit -m "feat: add PlatformStep component for onboarding wizard"
```

---

## Task 10: Create SmartConfigStep.vue (Step 4)

**Files:**
- Create: `packages/client/src/components/hermes/onboarding/steps/SmartConfigStep.vue`

**Step 1: Write the component**

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, NSwitch, NSpin, NAlert, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useSettingsStore } from '@/stores/hermes/settings'
import { useAIGeneration } from '../composables/useAIGeneration'

const props = defineProps<{
  soulContent: string
  connectedPlatforms: string[]
}>()

const emit = defineEmits<{
  (e: 'complete'): void
}>()

const { t } = useI18n()
const message = useMessage()
const settingsStore = useSettingsStore()
const { generating, recommendConfig } = useAIGeneration()

interface Recommendation {
  key: string
  label: string
  value: any
  reason: string
  accepted: boolean
}

const recommendations = ref<Recommendation[]>([])
const applying = ref(false)
const loaded = ref(false)

onMounted(async () => {
  if (!props.soulContent) {
    loaded.value = true
    return
  }

  const currentConfig: Record<string, any> = {
    agent: settingsStore.agent,
    memory: settingsStore.memory,
    display: settingsStore.display,
  }

  const result = await recommendConfig(
    props.soulContent,
    props.connectedPlatforms,
    currentConfig,
  )

  if (result.error) {
    message.warning(result.error)
    loaded.value = true
    return
  }

  // Flatten recommendations
  const items: Recommendation[] = []
  for (const [section, values] of Object.entries(result.config)) {
    for (const [key, value] of Object.entries(values as Record<string, any>)) {
      const reasonKey = `${section}.${key}`
      items.push({
        key: `${section}.${key}`,
        label: `${section}.${key}`,
        value,
        reason: result.reasons[reasonKey] || '',
        accepted: true,
      })
    }
  }
  recommendations.value = items
  loaded.value = true
})

function toggleAccept(idx: number) {
  recommendations.value[idx].accepted = !recommendations.value[idx].accepted
}

async function acceptAll() {
  applying.value = true
  try {
    const grouped: Record<string, Record<string, any>> = {}
    for (const rec of recommendations.value) {
      if (!rec.accepted) continue
      const [section, ...rest] = rec.key.split('.')
      const key = rest.join('.')
      if (!grouped[section]) grouped[section] = {}
      grouped[section][key] = rec.value
    }

    for (const [section, values] of Object.entries(grouped)) {
      await settingsStore.saveSection(section, values)
    }
    message.success(t('onboarding.config.applied'))
    emit('complete')
  } catch {
    message.error(t('onboarding.config.applyFailed'))
  } finally {
    applying.value = false
  }
}
</script>

<template>
  <div class="smart-config-step">
    <h3 class="step-title">{{ t('onboarding.config.title') }}</h3>
    <p class="step-desc">{{ t('onboarding.config.desc') }}</p>

    <NSpin :show="generating || !loaded">
      <div v-if="recommendations.length > 0" class="recommendations">
        <div v-for="(rec, idx) in recommendations" :key="rec.key" class="rec-card">
          <div class="rec-header">
            <NSwitch :value="rec.accepted" size="small" @update:value="toggleAccept(idx)" />
            <span class="rec-label">{{ rec.label }}</span>
            <code class="rec-value">{{ JSON.stringify(rec.value) }}</code>
          </div>
          <p v-if="rec.reason" class="rec-reason">{{ rec.reason }}</p>
        </div>
      </div>

      <NAlert v-else-if="loaded" type="info" :show-icon="true" :bordered="false">
        {{ t('onboarding.config.noRecommendations') }}
      </NAlert>
    </NSpin>

    <div class="step-actions">
      <NButton @click="$emit('complete')">{{ t('onboarding.skip') }}</NButton>
      <NButton
        type="primary"
        :loading="applying"
        :disabled="recommendations.length === 0"
        @click="acceptAll"
      >
        {{ t('onboarding.config.acceptAll') }}
      </NButton>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.smart-config-step { max-width: 640px; margin: 0 auto; }
.step-title { font-size: 20px; font-weight: 600; margin: 0 0 8px; }
.step-desc { color: $text-secondary; margin: 0 0 16px; font-size: 14px; }

.recommendations {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rec-card {
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: 12px;
}

.rec-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rec-label { font-size: 14px; font-weight: 500; flex: 1; }
.rec-value { font-size: 12px; color: $text-secondary; }
.rec-reason { font-size: 12px; color: $text-secondary; margin: 6px 0 0; padding-left: 32px; }

.step-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 32px;
}
</style>
```

**Step 2: Commit**

```bash
git add packages/client/src/components/hermes/onboarding/steps/SmartConfigStep.vue
git commit -m "feat: add SmartConfigStep component with AI recommendations"
```

---

## Task 11: Create OnboardingWizard.vue container

**Files:**
- Create: `packages/client/src/components/hermes/onboarding/OnboardingWizard.vue`

**Step 1: Write the component**

```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NButton, NIcon, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useSettingsStore } from '@/stores/hermes/settings'
import ProviderStep from './steps/ProviderStep.vue'
import SoulStep from './steps/SoulStep.vue'
import PlatformStep from './steps/PlatformStep.vue'
import SmartConfigStep from './steps/SmartConfigStep.vue'

const emit = defineEmits<{
  (e: 'complete'): void
}>()

const { t } = useI18n()
const message = useMessage()
const settingsStore = useSettingsStore()

const currentStep = ref(0)
const soulContent = ref('')
const connectedPlatforms = ref<string[]>([])

const STEPS = computed(() => [
  { key: 'provider', title: t('onboarding.steps.provider') },
  { key: 'soul', title: t('onboarding.steps.soul') },
  { key: 'platform', title: t('onboarding.steps.platform') },
  { key: 'config', title: t('onboarding.steps.config') },
])

function handleSoulUpdate(content: string) {
  soulContent.value = content
}

function handlePlatformsUpdate(platforms: string[]) {
  connectedPlatforms.value = platforms
}

async function handleComplete() {
  try {
    await settingsStore.saveSection('display', { onboarding_done: true })
    emit('complete')
  } catch {
    message.error(t('onboarding.completeFailed'))
  }
}

function handleBack() {
  if (currentStep.value > 0) currentStep.value--
}
</script>

<template>
  <div class="onboarding-wizard">
    <div class="wizard-container">
      <!-- Header -->
      <header class="wizard-header">
        <h1 class="wizard-title">{{ t('onboarding.title') }}</h1>
        <p class="wizard-subtitle">{{ t('onboarding.subtitle') }}</p>
      </header>

      <!-- Step indicator -->
      <div class="step-indicator">
        <div
          v-for="(step, idx) in STEPS"
          :key="step.key"
          class="step-dot"
          :class="{ active: idx === currentStep, done: idx < currentStep }"
          :title="step.title"
        />
      </div>

      <!-- Step content -->
      <div class="step-content">
        <ProviderStep v-if="currentStep === 0" @next="currentStep++" />
        <SoulStep
          v-else-if="currentStep === 1"
          @next="currentStep++"
          @update:soul="handleSoulUpdate"
        />
        <PlatformStep
          v-else-if="currentStep === 2"
          @next="currentStep++"
          @update:platforms="handlePlatformsUpdate"
        />
        <SmartConfigStep
          v-else-if="currentStep === 3"
          :soul-content="soulContent"
          :connected-platforms="connectedPlatforms"
          @complete="handleComplete"
        />
      </div>

      <!-- Back button -->
      <div v-if="currentStep > 0 && currentStep < 3" class="wizard-back">
        <NButton quaternary size="small" @click="handleBack">
          {{ t('onboarding.back') }}
        </NButton>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.onboarding-wizard {
  width: 100%;
  max-width: 800px;
  padding: 40px 24px;
}

.wizard-container {
  position: relative;
}

.wizard-header {
  text-align: center;
  margin-bottom: 32px;
}

.wizard-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 8px;
}

.wizard-subtitle {
  color: $text-secondary;
  font-size: 15px;
  margin: 0;
}

.step-indicator {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-bottom: 40px;
}

.step-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: $border-color;
  transition: all 0.3s;

  &.active { background: $accent-primary; transform: scale(1.3); }
  &.done { background: $success; }
}

.step-content {
  min-height: 300px;
}

.wizard-back {
  position: absolute;
  top: 0;
  left: 0;
}
</style>
```

**Step 2: Commit**

```bash
git add packages/client/src/components/hermes/onboarding/OnboardingWizard.vue
git commit -m "feat: add OnboardingWizard container with 4-step flow"
```

---

## Task 12: Create HealthDashboard.vue

**Files:**
- Create: `packages/client/src/components/hermes/onboarding/HealthDashboard.vue`

**Step 1: Write the component**

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { NCard, NButton, NCollapse, NCollapseItem, NSpin, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useHealthCheck, type HealthItem } from '../composables/useHealthCheck'

const { t } = useI18n()
const router = useRouter()
const { loading, items, healthy, warnings, runChecks } = useHealthCheck()

onMounted(() => {
  runChecks()
})

function getStatusIcon(status: HealthItem['status']) {
  return status === 'ok' ? '✅' : status === 'warning' ? '⚠️' : '❌'
}

function handleRerunWizard() {
  router.push({ name: 'hermes.onboarding' })
}

function handleAction(section: string) {
  router.push({ name: 'hermes.settings' })
}
</script>

<template>
  <div class="health-dashboard">
    <NCollapse>
      <NCollapseItem :title="t('onboarding.health.title')" name="health">
        <template #header-extra>
          <span v-if="healthy" class="status-badge ok">{{ t('onboarding.health.allGood') }}</span>
          <span v-else class="status-badge warn">{{ warnings.length }} {{ t('onboarding.health.issues') }}</span>
        </template>

        <NSpin :show="loading" size="small">
          <div class="health-items">
            <div v-for="item in items" :key="item.key" class="health-item" :class="item.status">
              <span class="item-icon">{{ getStatusIcon(item.status) }}</span>
              <div class="item-info">
                <span class="item-label">{{ item.label }}</span>
                <span class="item-msg">{{ item.message }}</span>
              </div>
              <NButton
                v-if="item.action"
                size="tiny"
                type="primary"
                quaternary
                @click="handleAction(item.action.section)"
              >
                {{ item.action.label }}
              </NButton>
            </div>
          </div>

          <div class="health-actions">
            <NButton size="small" quaternary @click="runChecks">
              {{ t('onboarding.health.refresh') }}
            </NButton>
            <NButton size="small" quaternary @click="handleRerunWizard">
              {{ t('onboarding.health.rerun') }}
            </NButton>
          </div>
        </NSpin>
      </NCollapseItem>
    </NCollapse>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.health-dashboard {
  margin-bottom: 20px;
}

.status-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;

  &.ok { background: rgba($success, 0.12); color: $success; }
  &.warn { background: rgba($warning, 0.12); color: $warning; }
}

.health-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.health-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: $radius-md;

  &.warning, &.error {
    background: rgba($warning, 0.05);
  }
}

.item-icon { font-size: 16px; }
.item-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.item-label { font-size: 13px; font-weight: 500; }
.item-msg { font-size: 12px; color: $text-secondary; }

.health-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>
```

**Step 2: Commit**

```bash
git add packages/client/src/components/hermes/onboarding/HealthDashboard.vue
git commit -m "feat: add HealthDashboard component"
```

---

## Task 13: Integrate HealthDashboard into SettingsView

**Files:**
- Modify: `packages/client/src/views/hermes/SettingsView.vue`

**Step 1: Add HealthDashboard import and embed**

Add import after existing imports:

```typescript
import HealthDashboard from '@/components/hermes/onboarding/HealthDashboard.vue'
```

Add HealthDashboard before the `<NTabs>` in the template:

```html
<!-- Inside .settings-content, before NSpin -->
<HealthDashboard />

<NSpin ...>
```

**Step 2: Verify SettingsView renders correctly**

Run: `npm run dev:client` and navigate to `/hermes/settings`
Expected: HealthDashboard card appears at top of settings page

**Step 3: Commit**

```bash
git add packages/client/src/views/hermes/SettingsView.vue
git commit -m "feat: embed HealthDashboard in SettingsView"
```

---

## Task 14: Add i18n translations for onboarding

**Files:**
- Modify: `packages/client/src/i18n/locales/en.ts`
- Modify: `packages/client/src/i18n/locales/zh.ts`
- Modify: `packages/client/src/i18n/locales/de.ts`
- Modify: `packages/client/src/i18n/locales/es.ts`
- Modify: `packages/client/src/i18n/locales/fr.ts`
- Modify: `packages/client/src/i18n/locales/ja.ts`
- Modify: `packages/client/src/i18n/locales/ko.ts`
- Modify: `packages/client/src/i18n/locales/pt.ts`

**Step 1: Add English translations**

Add to `en.ts` at the top level of the exported object:

```typescript
onboarding: {
  title: 'Welcome to Hermes',
  subtitle: 'Let\'s set up your AI assistant in a few steps',
  next: 'Next Step',
  back: 'Back',
  skip: 'Skip',
  steps: {
    provider: 'AI Provider',
    soul: 'Personality',
    platform: 'Platforms',
    config: 'Smart Config',
  },
  provider: {
    title: 'Configure AI Provider',
    desc: 'Choose your AI provider and enter the API key to get started.',
    select: 'Provider',
    selectPlaceholder: 'Select a provider...',
    apiKey: 'API Key',
    keyPlaceholder: 'Enter your API key...',
    keyRequired: 'Please enter an API key',
    validate: 'Validate & Save',
    validating: 'Validating...',
    validated: 'Provider connected successfully!',
    validateFailed: 'Validation failed. Check your API key.',
  },
  soul: {
    title: 'Define Agent Personality',
    desc: 'Describe your assistant or choose a preset. AI will generate a SOUL.md for you.',
    placeholder: 'Describe your assistant role, e.g. "A professional customer service agent for an e-commerce platform"',
    generate: 'AI Generate SOUL.md',
    generating: 'Generating...',
    preview: 'Generated SOUL.md',
    regenerate: 'Regenerate',
    saved: 'SOUL.md saved',
    saveFailed: 'Failed to save SOUL.md',
    describeFirst: 'Please describe your assistant first',
    presets: {
      customerService: 'Customer Service',
      coding: 'Coding Assistant',
      writing: 'Writing Assistant',
      general: 'General Assistant',
    },
    presetDesc: {
      customerService: 'A professional customer service assistant for handling user inquiries, complaints, and support tickets with patience and accuracy',
      coding: 'A technical coding assistant skilled in software development, debugging, code review, and architecture design',
      writing: 'A creative writing assistant for content creation, editing, proofreading, and style guidance',
      general: 'A versatile general-purpose assistant that can handle a wide range of tasks including Q&A, analysis, and recommendations',
    },
  },
  platform: {
    title: 'Connect Platforms',
    desc: 'Connect messaging platforms (optional — you can skip and configure later).',
    save: 'Save Credentials',
    saved: '{platform} credentials saved',
    saveFailed: 'Failed to save credentials',
    next: 'Next',
  },
  config: {
    title: 'Smart Configuration',
    desc: 'Based on your personality and platforms, AI recommends optimal settings.',
    acceptAll: 'Accept All & Complete',
    applied: 'Configuration applied successfully!',
    applyFailed: 'Failed to apply configuration',
    noRecommendations: 'No specific recommendations. Your configuration looks good!',
  },
  health: {
    title: 'Configuration Health',
    allGood: 'All good',
    issues: 'issue(s)',
    refresh: 'Refresh',
    rerun: 'Re-run Setup Wizard',
  },
  completeFailed: 'Failed to complete setup. Please try again.',
},
```

**Step 2: Add Chinese translations**

Add corresponding `onboarding` section to `zh.ts`:

```typescript
onboarding: {
  title: '欢迎使用 Hermes',
  subtitle: '几步完成 AI 助手配置',
  next: '下一步',
  back: '上一步',
  skip: '跳过',
  steps: {
    provider: 'AI 提供商',
    soul: '人格定义',
    platform: '平台连接',
    config: '智能配置',
  },
  provider: {
    title: '配置 AI 提供商',
    desc: '选择 AI 提供商并输入 API Key 以开始使用。',
    select: '提供商',
    selectPlaceholder: '选择提供商...',
    apiKey: 'API Key',
    keyPlaceholder: '输入 API Key...',
    keyRequired: '请输入 API Key',
    validate: '验证并保存',
    validating: '验证中...',
    validated: '提供商连接成功！',
    validateFailed: '验证失败，请检查 API Key。',
  },
  soul: {
    title: '定义助手人格',
    desc: '描述你的助手或选择预设模板，AI 将为你生成 SOUL.md。',
    placeholder: '描述你的助手角色，例如"一个电商平台的专业客服助手"',
    generate: 'AI 生成 SOUL.md',
    generating: '生成中...',
    preview: '生成的 SOUL.md',
    regenerate: '重新生成',
    saved: 'SOUL.md 已保存',
    saveFailed: 'SOUL.md 保存失败',
    describeFirst: '请先描述你的助手',
    presets: {
      customerService: '客服助手',
      coding: '编程助手',
      writing: '写作助手',
      general: '通用助手',
    },
    presetDesc: {
      customerService: '一个专业的客服助手，用于处理用户咨询、投诉和工单，耐心且准确',
      coding: '一个技术编程助手，擅长软件开发、调试、代码审查和架构设计',
      writing: '一个创意写作助手，用于内容创作、编辑、校对和风格指导',
      general: '一个多功能的通用助手，可以处理问答、分析和建议等多种任务',
    },
  },
  platform: {
    title: '连接平台',
    desc: '连接消息平台（可选 — 可以跳过，稍后配置）。',
    save: '保存凭据',
    saved: '{platform} 凭据已保存',
    saveFailed: '凭据保存失败',
    next: '下一步',
  },
  config: {
    title: '智能配置',
    desc: '基于你的人格和平台，AI 推荐最优设置。',
    acceptAll: '全部采用并完成',
    applied: '配置已应用！',
    applyFailed: '配置应用失败',
    noRecommendations: '没有特别建议，配置看起来很好！',
  },
  health: {
    title: '配置健康检查',
    allGood: '一切正常',
    issues: '个问题',
    refresh: '刷新',
    rerun: '重新运行设置向导',
  },
  completeFailed: '设置完成失败，请重试。',
},
```

**Step 3: Add placeholder translations for other 6 locales**

For `de.ts`, `es.ts`, `fr.ts`, `ja.ts`, `ko.ts`, `pt.ts` — add the English version as fallback with a TODO comment:

```typescript
// TODO: Translate to {language}
onboarding: { /* same as English */ },
```

**Step 4: Verify i18n loads without error**

Run: `npm run dev:client`
Expected: App loads, no console errors about missing translation keys

**Step 5: Commit**

```bash
git add packages/client/src/i18n/locales/
git commit -m "feat: add onboarding i18n translations (en, zh + 6 locale placeholders)"
```

---

## Task 15: End-to-end smoke test

**Step 1: Start dev server**

Run: `npm run dev`

**Step 2: Test onboarding flow**

1. Clear `sessionStorage` and set config `display.onboarding_done = false`
2. Navigate to `/hermes/chat` — should redirect to `/hermes/onboarding`
3. Step 1: Select provider, enter API key, validate
4. Step 2: Describe assistant, generate SOUL.md, preview/edit
5. Step 3: Connect a platform (or skip)
6. Step 4: Review AI recommendations, accept
7. Verify redirect to `/hermes/chat` after completion
8. Navigate to `/hermes/settings` — HealthDashboard should appear at top

**Step 3: Commit**

```bash
git commit --allow-empty -m "test: e2e smoke test passed for onboarding wizard"
```

---

## Execution Notes

- **Dependencies between tasks:** Tasks 1-3 are independent. Tasks 4-6 (composables) are independent. Tasks 7-10 (step components) depend on composables. Task 11 (wizard) depends on steps. Tasks 12-13 (health + integration) depend on composables. Task 14 (i18n) is independent but should come before testing.
- **Critical path:** Task 1 → Task 4 → Task 7 → Task 11 → Task 15
- **Each component is self-contained** — if AI generation fails, the wizard still works (user can skip soul generation and config recommendations).
