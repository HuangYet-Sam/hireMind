# Smart Dashboard — Replace Onboarding Wizard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the disruptive full-screen 4-step onboarding wizard with a non-blocking SetupChecklist embedded in ChatView.

**Architecture:** Delete 10 onboarding files. Create 2 new files: `useSetupStatus.ts` composable (detects config status) and `SetupChecklist.vue` (inline checklist with expandable mini-forms). Embed in ChatView above ChatPanel. Persist collapsed state in localStorage. No new backend endpoints.

**Tech Stack:** Vue 3 Composition API, Naive UI, Pinia stores (app, settings), Socket.IO (for AI SOUL generation), TypeScript

---

## Task 1: Create `useSetupStatus.ts` composable

**Files:**
- Create: `packages/client/src/composables/useSetupStatus.ts`

**Step 1: Write the composable**

```typescript
// packages/client/src/composables/useSetupStatus.ts
import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/hermes/app'
import { useSettingsStore } from '@/stores/hermes/settings'
import { fetchMemory } from '@/api/hermes/skills'
import { fetchModels } from '@/api/hermes/chat'

export interface SetupItem {
  key: string
  status: 'ok' | 'warning' | 'empty'
  label: string
  detail: string
}

const COLLAPSED_KEY = 'hermes_setup_collapsed'

export function useSetupStatus() {
  const loading = ref(false)
  const items = ref<SetupItem[]>([])
  const collapsed = ref(localStorage.getItem(COLLAPSED_KEY) === '1')

  const pending = computed(() => items.value.filter(i => i.status !== 'ok'))
  const allDone = computed(() => items.value.length > 0 && pending.value.length === 0)

  async function check() {
    loading.value = true
    const results: SetupItem[] = []

    // Check 1: AI Provider
    try {
      const res = await fetchModels()
      if (res.data && res.data.length > 0) {
        results.push({
          key: 'provider',
          status: 'ok',
          label: 'AI Provider',
          detail: `${res.data.length} model(s) available`,
        })
      } else {
        results.push({ key: 'provider', status: 'empty', label: 'AI Provider', detail: 'No models configured' })
      }
    } catch {
      results.push({ key: 'provider', status: 'empty', label: 'AI Provider', detail: 'No provider connected' })
    }

    // Check 2: SOUL.md
    try {
      const mem = await fetchMemory()
      if (mem.soul && mem.soul.trim().length > 10) {
        results.push({ key: 'soul', status: 'ok', label: 'SOUL.md', detail: 'Agent personality defined' })
      } else {
        results.push({ key: 'soul', status: 'empty', label: 'SOUL.md', detail: 'Agent personality is empty' })
      }
    } catch {
      results.push({ key: 'soul', status: 'empty', label: 'SOUL.md', detail: 'Could not check' })
    }

    // Check 3: Memory enabled
    try {
      const settingsStore = useSettingsStore()
      if (!settingsStore.memory?.memory_enabled) {
        await settingsStore.fetchSettings()
      }
      if (settingsStore.memory?.memory_enabled) {
        results.push({ key: 'memory', status: 'ok', label: 'Memory', detail: 'Context memory enabled' })
      } else {
        results.push({ key: 'memory', status: 'warning', label: 'Memory', detail: 'Memory disabled' })
      }
    } catch {
      results.push({ key: 'memory', status: 'warning', label: 'Memory', detail: 'Could not check' })
    }

    // Check 4: Platforms (optional, so warning not error)
    try {
      const appStore = useAppStore()
      const platformCount = Object.keys(appStore.connectedPlatforms).length
      if (platformCount > 0) {
        results.push({ key: 'platforms', status: 'ok', label: 'Platforms', detail: `${platformCount} connected` })
      } else {
        results.push({ key: 'platforms', status: 'warning', label: 'Platforms', detail: 'No platforms (optional)' })
      }
    } catch {
      results.push({ key: 'platforms', status: 'warning', label: 'Platforms', detail: 'Optional' })
    }

    items.value = results
    loading.value = false

    // Auto-expand if new issues found
    if (pending.value.length > 0) {
      collapsed.value = false
      localStorage.removeItem(COLLAPSED_KEY)
    }
  }

  function toggleCollapse() {
    collapsed.value = !collapsed.value
    try {
      localStorage.setItem(COLLAPSED_KEY, collapsed.value ? '1' : '0')
    } catch {
      // ignore quota errors
    }
  }

  function markDone(key: string) {
    const item = items.value.find(i => i.key === key)
    if (item) {
      item.status = 'ok'
      item.detail = 'Configured'
    }
    // Auto-collapse when all done
    if (allDone.value) {
      collapsed.value = true
      localStorage.setItem(COLLAPSED_KEY, '1')
    }
  }

  return { loading, items, collapsed, pending, allDone, check, toggleCollapse, markDone }
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd packages/client && npx vue-tsc --noEmit`
Expected: No type errors related to this file

**Step 3: Commit**

```bash
git add packages/client/src/composables/useSetupStatus.ts
git commit -m "feat: add useSetupStatus composable for smart dashboard"
```

---

## Task 2: Create `SetupChecklist.vue` component

**Files:**
- Create: `packages/client/src/components/hermes/chat/SetupChecklist.vue`

**Step 1: Write the component**

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, NInput, NSelect, NSwitch, NSpin, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useSetupStatus } from '@/composables/useSetupStatus'
import { useAppStore } from '@/stores/hermes/app'
import { useSettingsStore } from '@/stores/hermes/settings'
import { useModelsStore } from '@/stores/hermes/models'
import { updateProvider } from '@/api/hermes/system'
import { fetchModels } from '@/api/hermes/chat'
import { saveMemory } from '@/api/hermes/skills'
import { startRunViaSocket, connectChatRun } from '@/api/hermes/chat'

const { t } = useI18n()
const message = useMessage()
const appStore = useAppStore()
const settingsStore = useSettingsStore()
const modelsStore = useModelsStore()

const { loading, items, collapsed, pending, allDone, check, toggleCollapse, markDone } = useSetupStatus()

const expandedKey = ref<string | null>(null)

// ─── Provider state ───
const selectedProvider = ref<string | null>(null)
const apiKey = ref('')
const providerSaving = ref(false)
const providerValidated = ref(false)

// ─── Soul state ───
const soulDescription = ref('')
const soulContent = ref('')
const soulGenerating = ref(false)
const soulStreaming = ref('')
const soulEditing = ref(false)
const soulEditText = ref('')

const SOUL_PRESETS = [
  { key: 'customerService', desc: 'A professional customer service assistant for handling user inquiries with patience and accuracy' },
  { key: 'coding', desc: 'A technical coding assistant skilled in software development, debugging, and code review' },
  { key: 'writing', desc: 'A creative writing assistant for content creation, editing, and style guidance' },
  { key: 'general', desc: 'A versatile general-purpose assistant for Q&A, analysis, and recommendations' },
]

onMounted(() => {
  check()
  if (modelsStore.providers.length === 0) {
    modelsStore.fetchProviders()
  }
})

function toggleExpand(key: string) {
  expandedKey.value = expandedKey.value === key ? null : key
}

// ─── Provider actions ───
async function saveProvider() {
  if (!selectedProvider.value || !apiKey.value.trim()) return
  providerSaving.value = true
  try {
    await updateProvider(selectedProvider.value, { api_key: apiKey.value.trim() })
    await fetchModels()
    providerValidated.value = true
    markDone('provider')
    message.success(t('setup.provider.validated'))
  } catch (e: any) {
    message.error(e.message || t('setup.provider.validateFailed'))
  } finally {
    providerSaving.value = false
  }
}

// ─── Soul actions ───
async function generateSoul() {
  if (!soulDescription.value.trim()) {
    message.warning(t('setup.soul.describeFirst'))
    return
  }
  soulGenerating.value = true
  soulStreaming.value = ''

  const SYSTEM_PROMPT = `You are a SOUL.md generator for Hermes AI Agent.
Given the user's description of their desired assistant, generate a complete SOUL.md file.
Format: Markdown with sections (# Role, # Personality, # Guidelines, # Constraints).
Be specific and professional. Output ONLY the SOUL.md content.`

  let accumulated = ''
  const sessionId = `setup-soul-${Date.now()}`

  startRunViaSocket(
    {
      input: `Generate a SOUL.md for: ${soulDescription.value}`,
      instructions: SYSTEM_PROMPT,
      session_id: sessionId,
    },
    (event) => {
      if (event.delta) {
        accumulated += event.delta
        soulStreaming.value = accumulated
      }
      if (event.output) {
        accumulated = event.output
        soulStreaming.value = accumulated
      }
    },
    () => {
      soulContent.value = accumulated
      soulGenerating.value = false
    },
    (err) => {
      soulGenerating.value = false
      message.error(err.message || 'Generation failed')
    },
  )
}

async function saveSoul() {
  const content = soulEditing.value ? soulEditText.value : soulContent.value
  if (!content?.trim()) return
  try {
    await saveMemory('soul', content)
    markDone('soul')
    message.success(t('setup.soul.saved'))
  } catch {
    message.error(t('setup.soul.saveFailed'))
  }
}

// ─── Memory actions ───
async function enableMemory() {
  try {
    await settingsStore.saveSection('memory', { memory_enabled: true })
    markDone('memory')
    message.success(t('common.saved'))
  } catch {
    message.error(t('common.saveFailed'))
  }
}
</script>

<template>
  <div v-if="!allDone" class="setup-checklist" :class="{ collapsed }">
    <div class="checklist-header" @click="toggleCollapse">
      <span class="checklist-title">{{ t('setup.title') }}</span>
      <span class="checklist-progress">{{ pending.length }} {{ t('setup.remaining') }}</span>
      <span class="checklist-toggle">{{ collapsed ? '▸' : '▾' }}</span>
    </div>

    <div v-if="!collapsed" class="checklist-body">
      <NSpin :show="loading" size="small">
        <div class="checklist-items">
          <div
            v-for="item in items"
            :key="item.key"
            class="checklist-item"
            :class="{ [item.status]: true, expanded: expandedKey === item.key }"
          >
            <div class="item-row" @click="item.status !== 'ok' && toggleExpand(item.key)">
              <span class="item-icon">{{ item.status === 'ok' ? '✓' : item.status === 'warning' ? '⚠' : '○' }}</span>
              <span class="item-label">{{ item.label }}</span>
              <span class="item-detail">{{ item.detail }}</span>
              <span v-if="item.status !== 'ok' && expandedKey !== item.key" class="item-action">→</span>
            </div>

            <!-- Provider form -->
            <div v-if="item.key === 'provider' && expandedKey === 'provider'" class="item-form">
              <div class="form-row">
                <NSelect
                  v-model:value="selectedProvider"
                  :options="modelsStore.providers.map(p => ({ label: p.label, value: p.provider }))"
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

            <!-- Soul form -->
            <div v-if="item.key === 'soul' && expandedKey === 'soul'" class="item-form">
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
                  :loading="soulGenerating"
                  :disabled="!soulDescription.trim()"
                  @click="generateSoul"
                >
                  {{ soulGenerating ? t('setup.soul.generating') : t('setup.soul.generate') }}
                </NButton>
              </div>
              <!-- Streaming preview -->
              <div v-if="soulGenerating && soulStreaming" class="soul-preview streaming">
                <pre>{{ soulStreaming }}</pre>
              </div>
              <!-- Generated content -->
              <div v-if="soulContent && !soulGenerating" class="soul-preview">
                <div class="preview-header">
                  <span>{{ t('setup.soul.preview') }}</span>
                  <div class="preview-actions">
                    <NButton size="tiny" @click="generateSoul">{{ t('setup.soul.regenerate') }}</NButton>
                    <NButton size="tiny" @click="soulEditing = !soulEditing">{{ soulEditing ? t('setup.soul.preview') : t('common.edit') }}</NButton>
                  </div>
                </div>
                <pre v-if="!soulEditing">{{ soulContent }}</pre>
                <div v-else>
                  <NInput v-model:value="soulEditText" type="textarea" :rows="8" />
                </div>
                <NButton type="primary" size="small" @click="saveSoul">{{ t('common.save') }}</NButton>
              </div>
            </div>

            <!-- Memory toggle -->
            <div v-if="item.key === 'memory' && expandedKey === 'memory'" class="item-form">
              <p class="form-hint">{{ t('setup.memory.hint') }}</p>
              <NButton type="primary" size="small" @click="enableMemory">{{ t('setup.memory.enable') }}</NButton>
            </div>

            <!-- Platforms link -->
            <div v-if="item.key === 'platforms' && expandedKey === 'platforms'" class="item-form">
              <p class="form-hint">{{ t('setup.platforms.hint') }}</p>
              <NButton size="small" @click="$router.push({ name: 'hermes.settings' })">
                {{ t('setup.platforms.goSettings') }}
              </NButton>
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

  &.collapsed {
    .checklist-header {
      border-bottom: none;
    }
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

  &:hover {
    background: $bg-card-hover;
  }
}

.checklist-title {
  font-size: 13px;
  font-weight: 600;
  color: $text-primary;
}

.checklist-progress {
  font-size: 11px;
  color: $warning;
}

.checklist-toggle {
  margin-left: auto;
  font-size: 12px;
  color: $text-muted;
}

.checklist-body {
  padding: 8px 16px 12px;
}

.checklist-items {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.checklist-item {
  border-radius: $radius-sm;
  transition: background $transition-fast;

  &.ok .item-icon { color: $success; }
  &.warning .item-icon { color: $warning; }
  &.empty .item-icon { color: $text-muted; }

  &.expanded {
    background: $bg-secondary;
  }
}

.item-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  cursor: pointer;

  .checklist-item.ok & {
    cursor: default;
  }
}

.item-icon {
  font-size: 14px;
  width: 16px;
  text-align: center;
}

.item-label {
  font-size: 13px;
  font-weight: 500;
}

.item-detail {
  font-size: 11px;
  color: $text-muted;
  flex: 1;
}

.item-action {
  font-size: 12px;
  color: $text-muted;
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

.form-actions {
  display: flex;
  gap: 8px;
}

.form-hint {
  font-size: 12px;
  color: $text-secondary;
  margin: 0;
}

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

  &.streaming {
    border-color: $accent-muted;
  }

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

.preview-actions {
  display: flex;
  gap: 4px;
}
</style>
```

**Step 2: Verify TypeScript compiles**

Run: `cd packages/client && npx vue-tsc --noEmit`
Expected: No type errors

**Step 3: Commit**

```bash
git add packages/client/src/components/hermes/chat/SetupChecklist.vue
git commit -m "feat: add SetupChecklist component for smart dashboard"
```

---

## Task 3: Embed SetupChecklist in ChatView

**Files:**
- Modify: `packages/client/src/views/hermes/ChatView.vue`

**Step 1: Add import and component**

Replace the entire file content with:

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import ChatPanel from '@/components/hermes/chat/ChatPanel.vue'
import SetupChecklist from '@/components/hermes/chat/SetupChecklist.vue'
import { useAppStore } from '@/stores/hermes/app'
import { useChatStore } from '@/stores/hermes/chat'
import { useProfilesStore } from '@/stores/hermes/profiles'

const appStore = useAppStore()
const chatStore = useChatStore()
const profilesStore = useProfilesStore()

onMounted(async () => {
  appStore.loadModels()
  await profilesStore.fetchProfiles()
  chatStore.loadSessions()
})
</script>

<template>
  <div class="chat-view">
    <SetupChecklist />
    <ChatPanel />
  </div>
</template>

<style scoped lang="scss">
.chat-view {
  height: calc(100 * var(--vh));
  display: flex;
  flex-direction: column;
}
</style>
```

**Step 2: Verify ChatView renders**

Run: `npm run dev:client`
Navigate to `/hermes/chat` — SetupChecklist should appear above ChatPanel

**Step 3: Commit**

```bash
git add packages/client/src/views/hermes/ChatView.vue
git commit -m "feat: embed SetupChecklist in ChatView"
```

---

## Task 4: Remove onboarding route + guard from router

**Files:**
- Modify: `packages/client/src/router/index.ts`

**Step 1: Remove the onboarding route entry**

Delete lines 104-107 (the `hermes.onboarding` route object).

**Step 2: Remove the onboarding redirect guard**

Delete lines 129-148 (the entire onboarding check block in `beforeEach`).

The `beforeEach` should become:

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

  next()
})
```

**Step 3: Verify router compiles**

Run: `cd packages/client && npx vue-tsc --noEmit`
Expected: No type errors

**Step 4: Commit**

```bash
git add packages/client/src/router/index.ts
git commit -m "feat: remove onboarding route and redirect guard"
```

---

## Task 5: Remove HealthDashboard from SettingsView

**Files:**
- Modify: `packages/client/src/views/hermes/SettingsView.vue`

**Step 1: Remove HealthDashboard import**

Delete line 20:
```typescript
import HealthDashboard from "@/components/hermes/onboarding/HealthDashboard.vue";
```

**Step 2: Remove HealthDashboard from template**

Delete line 37:
```html
      <HealthDashboard />
```

**Step 3: Commit**

```bash
git add packages/client/src/views/hermes/SettingsView.vue
git commit -m "feat: remove HealthDashboard from SettingsView"
```

---

## Task 6: Clean up settings store

**Files:**
- Modify: `packages/client/src/stores/hermes/settings.ts`

**Step 1: Remove onboardingDone computed**

Delete line 42:
```typescript
  const onboardingDone = computed(() => !!display.value?.onboarding_done)
```

**Step 2: Remove from return statement**

Remove `onboardingDone,` from the return object (line 101).

**Step 3: Verify TypeScript compiles**

Run: `cd packages/client && npx vue-tsc --noEmit`
Expected: No type errors (note: the router guard that used `onboardingDone` was already removed in Task 4)

**Step 4: Commit**

```bash
git add packages/client/src/stores/hermes/settings.ts
git commit -m "refactor: remove onboardingDone from settings store"
```

---

## Task 7: Update i18n translations

**Files:**
- Modify: `packages/client/src/i18n/locales/en.ts`
- Modify: `packages/client/src/i18n/locales/zh.ts`
- Modify: `packages/client/src/i18n/locales/de.ts`
- Modify: `packages/client/src/i18n/locales/es.ts`
- Modify: `packages/client/src/i18n/locales/fr.ts`
- Modify: `packages/client/src/i18n/locales/ja.ts`
- Modify: `packages/client/src/i18n/locales/ko.ts`
- Modify: `packages/client/src/i18n/locales/pt.ts`

**Step 1: Add `setup` section and trim `onboarding` section in `en.ts`**

Add `setup` section after the `onboarding` section. Keep the `onboarding.soul.presets` keys since SetupChecklist uses them:

```typescript
  // In en.ts — add after onboarding section:
  setup: {
    title: 'Setup Checklist',
    remaining: 'remaining',
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

Keep only the `onboarding.soul.presets` and `onboarding.soul.presetDesc` keys in the `onboarding` section (SetupChecklist references them). Remove all other `onboarding` sub-keys.

**Step 2: Add corresponding `setup` section to `zh.ts`**

```typescript
  setup: {
    title: '配置清单',
    remaining: '项待完成',
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

**Step 3: Add English placeholder for other 6 locales**

For `de.ts`, `es.ts`, `fr.ts`, `ja.ts`, `ko.ts`, `pt.ts` — add the English `setup` section as fallback.

**Step 4: Commit**

```bash
git add packages/client/src/i18n/locales/
git commit -m "feat: add setup checklist i18n, trim wizard translations"
```

---

## Task 8: Delete old onboarding files

**Files:**
- Delete: `packages/client/src/components/hermes/onboarding/` (entire directory)
- Delete: `packages/client/src/views/hermes/OnboardingView.vue`

**Step 1: Delete the files**

```bash
rm -rf packages/client/src/components/hermes/onboarding/
rm packages/client/src/views/hermes/OnboardingView.vue
```

**Step 2: Verify no broken imports**

Run: `cd packages/client && npx vue-tsc --noEmit`
Expected: No type errors (all references removed in Tasks 4-5)

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor: remove onboarding wizard (replaced by SetupChecklist)"
```

---

## Task 9: End-to-end verification

**Step 1: Start dev server**

Run: `npm run dev`

**Step 2: Test SetupChecklist behavior**

1. Navigate to `/hermes/chat`
2. If Provider not configured: checklist should show "○ AI Provider — No provider connected"
3. Click "AI Provider" row → expand inline form → select provider → enter key → validate
4. Item should turn ✓ green, checklist updates
5. Click "SOUL.md" → choose preset → generate → save
6. Click "Memory" → enable → turns ✓
7. Platforms shows ⚠ (optional, doesn't block)
8. All items done → checklist auto-collapses
9. Refresh page → collapsed state remembered
10. Settings page still works without HealthDashboard

**Step 3: Final commit**

```bash
git commit --allow-empty -m "test: e2e verification passed for SetupChecklist"
```

---

## Execution Notes

- **Dependencies:** Tasks 1-2 are independent. Task 3 depends on Task 2. Tasks 4-8 are independent of each other but must come after Task 3. Task 9 is last.
- **Critical path:** Task 1 → Task 2 → Task 3 → Task 8 → Task 9
- **Rollback:** If anything breaks, revert to the commit before Task 4 (the onboarding files are still intact until Task 8).
- **No new backend endpoints needed.** All APIs already exist.
