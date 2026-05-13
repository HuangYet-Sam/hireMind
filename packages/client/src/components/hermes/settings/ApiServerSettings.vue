<script setup lang="ts">
import { computed } from 'vue'
import { NInput, NInputNumber, NSwitch, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useSettingsStore } from '@/stores/hermes/settings'
import { useAppStore } from '@/stores/hermes/app'
import SettingRow from './SettingRow.vue'

const settingsStore = useSettingsStore()
const appStore = useAppStore()
const message = useMessage()
const { t } = useI18n()

const apiServer = computed(() => settingsStore.platforms?.api_server || {} as any)
const extra = computed(() => apiServer.value.extra || {} as any)

const endpointUrl = computed(() => {
  const host = extra.value.host || '127.0.0.1'
  const port = extra.value.port || 8642
  return `http://${host}:${port}/v1`
})

async function save(values: Record<string, any>) {
  try {
    await settingsStore.saveSection('platforms', { api_server: values })
    message.success(t('settings.saved'))
  } catch (err: any) {
    message.error(t('settings.saveFailed'))
  }
}

function copyEndpoint() {
  navigator.clipboard.writeText(endpointUrl.value)
  message.success('Copied!')
}
</script>

<template>
  <section class="settings-section">
    <SettingRow :label="t('settings.apiServer.enable')" :hint="t('settings.apiServer.enableHint')">
      <NSwitch
        :value="!!apiServer.enabled"
        @update:value="v => save({ enabled: v })"
      />
    </SettingRow>
    <SettingRow :label="t('settings.apiServer.host')" :hint="t('settings.apiServer.hostHint')">
      <NInput
        :value="extra.host || '127.0.0.1'"
        size="small" class="input-sm"
        @update:value="v => save({ extra: { ...extra, host: v } })"
      />
    </SettingRow>
    <SettingRow :label="t('settings.apiServer.port')" :hint="t('settings.apiServer.portHint')">
      <NInputNumber
        :value="extra.port || 8642"
        :min="1" :max="65535"
        size="small" class="input-sm"
        @update:value="v => v != null && save({ extra: { ...extra, port: v } })"
      />
    </SettingRow>
    <SettingRow :label="t('settings.apiServer.key')" :hint="t('settings.apiServer.keyHint')">
      <NInput
        :value="extra.key || ''"
        type="password" show-password-on="click"
        size="small" class="input-sm"
        @update:value="v => save({ extra: { ...extra, key: v } })"
      />
    </SettingRow>
    <SettingRow :label="t('settings.apiServer.cors')" :hint="t('settings.apiServer.corsHint')">
      <NInput
        :value="extra.cors || '*'"
        size="small" class="input-sm"
        @update:value="v => save({ extra: { ...extra, cors: v } })"
      />
    </SettingRow>

    <div v-if="appStore.connected" class="endpoint-info">
      <div class="endpoint-label">API Endpoint</div>
      <div class="endpoint-url">
        <code>{{ endpointUrl }}</code>
        <button class="copy-btn" @click="copyEndpoint" :title="'Copy'">&#x2398;</button>
      </div>
      <div class="endpoint-hint">
        Use this endpoint to connect OpenAI-compatible clients (LobeChat, Open WebUI, ChatBox, etc.)
      </div>
    </div>
  </section>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.settings-section {
  margin-top: 16px;
}

.endpoint-info {
  margin-top: 20px;
  padding: 16px;
  border: 1px solid $border-light;
  border-radius: 8px;
  background: var(--n-color-modal, #fafafa);
}

.endpoint-label {
  font-size: 12px;
  color: $text-muted;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.endpoint-url {
  display: flex;
  align-items: center;
  gap: 8px;

  code {
    font-size: 14px;
    color: $text-primary;
    background: var(--n-color-action, #f0f0f0);
    padding: 6px 12px;
    border-radius: 4px;
    flex: 1;
    overflow-x: auto;
    white-space: nowrap;
  }
}

.copy-btn {
  background: none;
  border: 1px solid $border-light;
  border-radius: 4px;
  padding: 4px 8px;
  cursor: pointer;
  font-size: 16px;
  color: $text-muted;

  &:hover {
    color: $text-primary;
    border-color: $text-muted;
  }
}

.endpoint-hint {
  font-size: 12px;
  color: $text-muted;
  margin-top: 8px;
}

.input-sm {
  width: 220px;
}
</style>
