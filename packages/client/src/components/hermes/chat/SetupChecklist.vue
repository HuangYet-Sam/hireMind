<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, NInput, NSelect, NSpin, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useSmartConfig } from '@/composables/useSmartConfig'
import { useSettingsStore } from '@/stores/hermes/settings'
import { useModelsStore } from '@/stores/hermes/models'
import { updateProvider } from '@/api/hermes/system'
import { fetchModels } from '@/api/hermes/chat'
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
const selectedProvider = ref<string | null>(null)
const apiKey = ref('')
const providerSaving = ref(false)
const soulDescription = ref('')
const soulContent = ref('')
const soulGenerating = ref(false)
const soulEditing = ref(false)
const soulEditText = ref('')
const soulSaving = ref(false)
const collapsed = ref(false)

const SOUL_PRESETS = [
  { key: 'customerService', desc: 'A professional customer service assistant for handling user inquiries with patience and accuracy' },
  { key: 'coding', desc: 'A technical coding assistant skilled in software development, debugging, and code review' },
  { key: 'writing', desc: 'A creative writing assistant for content creation, editing, and style guidance' },
  { key: 'general', desc: 'A versatile general-purpose assistant for Q&A, analysis, and recommendations' },
]

onMounted(() => {
  refresh().catch(() => {})
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

async function saveProvider() {
  if (!selectedProvider.value || !apiKey.value.trim()) return
  providerSaving.value = true
  try {
    await updateProvider(selectedProvider.value, { api_key: apiKey.value.trim() })
    await fetchModels()
    markResolved('health:provider-empty')
    await refresh()
    message.success(t('setup.provider.validated'))
  } catch (e: any) {
    message.error(e.message || t('setup.provider.validateFailed'))
  } finally {
    providerSaving.value = false
  }
}

function handleGenerateSoul() {
  if (!soulDescription.value.trim()) {
    message.warning(t('setup.soul.describeFirst'))
    return
  }
  if (generating.value || soulGenerating.value) return
  soulGenerating.value = true
  generateSoul(soulDescription.value).then(({ text, error }) => {
    soulGenerating.value = false
    if (error) { message.error(error) }
    else if (text) { soulContent.value = text; soulEditText.value = text; soulEditing.value = false }
  })
}

async function saveSoul() {
  const content = soulEditing.value ? soulEditText.value : soulContent.value
  if (!content?.trim() || soulSaving.value) return
  soulSaving.value = true
  try {
    await saveMemory('soul', content)
    soulEditing.value = false
    markResolved('health:soul-empty')
    await refresh()
    message.success(t('setup.soul.saved'))
  } catch {
    message.error(t('setup.soul.saveFailed'))
  } finally {
    soulSaving.value = false
  }
}

async function handleInlineAction(item: typeof items.value[0]) {
  const target = item.action?.target
  const payload = item.action?.payload
  try {
    if (target === 'memory') {
      await settingsStore.saveSection('memory', { memory_enabled: true })
    } else if (target === 'agent.max_turns') {
      await settingsStore.saveSection('agent', { max_turns: payload?.value ?? 30 })
    } else if (target === 'agent.gateway_timeout') {
      await settingsStore.saveSection('agent', { gateway_timeout: payload?.value ?? 120 })
    } else if (payload?.platform) {
      await settingsStore.saveSection('platforms', { [payload.platform]: { enabled: true } })
    }
    markResolved(item.id)
    await refresh()
    message.success(t('common.saved'))
  } catch {
    message.error(t('common.saveFailed'))
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
            :class="[item.severity, { expanded: expandedKey === (item.action?.target || item.id) }]"
          >
            <div class="item-row" @click="item.action && toggleExpand(item.action.target || item.id)">
              <span class="item-icon" :class="item.severity">{{ severityIcon(item.severity) }}</span>
              <span class="item-label">{{ item.title }}</span>
              <span class="item-detail">{{ item.detail }}</span>

              <NButton
                v-if="item.action?.type === 'inline' && item.action.target !== 'provider' && item.action.target !== 'soul'"
                size="tiny"
                quaternary
                class="item-action-btn"
                @click.stop="handleInlineAction(item)"
              >
                {{ item.action.label }}
              </NButton>
              <NButton
                v-else-if="item.action?.type === 'navigate'"
                size="tiny"
                quaternary
                class="item-action-btn"
                @click.stop="$router.push({ name: item.action.target as any })"
              >
                {{ item.action.label }}
              </NButton>
              <span v-else-if="item.action && expandedKey !== (item.action.target || item.id)" class="item-action">→</span>
              <span
                v-if="item.severity !== 'error' && item.action?.type !== 'inline'"
                class="item-dismiss"
                role="button"
                :aria-label="t('setup.dismiss')"
                tabindex="0"
                @click.stop="dismiss(item.id)"
                @keydown.enter.stop="dismiss(item.id)"
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
            <div v-if="item.action?.target === 'soul' && expandedKey === 'soul'" class="item-form">
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
              <div v-if="generating && streamContent" class="soul-preview streaming">
                <pre>{{ streamContent }}</pre>
              </div>
              <div v-if="soulContent && !generating" class="soul-preview">
                <div class="preview-header">
                  <span>{{ t('setup.soul.preview') }}</span>
                  <div class="preview-actions">
                    <NButton size="tiny" :disabled="generating || soulGenerating" @click="handleGenerateSoul">{{ t('setup.soul.regenerate') }}</NButton>
                    <NButton size="tiny" @click="soulEditing = !soulEditing">
                      {{ soulEditing ? t('setup.soul.preview') : t('common.edit') }}
                    </NButton>
                  </div>
                </div>
                <pre v-if="!soulEditing">{{ soulContent }}</pre>
                <div v-else>
                  <NInput v-model:value="soulEditText" type="textarea" :rows="8" />
                </div>
                <NButton type="primary" size="small" :loading="soulSaving" @click="saveSoul">{{ t('common.save') }}</NButton>
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
  color: $warning;
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

  &:hover,
  &:focus-visible { color: $text-secondary; outline: none; }
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

  &.streaming { border-color: rgba(128, 128, 128, 0.3); }

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

@media (max-width: $breakpoint-mobile) {
  .checklist-header { padding: 6px 12px; }
  .checklist-body { padding: 6px 12px 10px; }
  .item-row { gap: 6px; padding: 5px 6px; }
  .item-label { font-size: 12px; }
  .item-detail { display: none; }
}
</style>
