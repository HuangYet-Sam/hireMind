<script setup lang="ts">
import { computed } from 'vue'
import { NEmpty, NTag } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useSettingsStore } from '@/stores/hermes/settings'

const settingsStore = useSettingsStore()
const { t } = useI18n()

const mcpServers = computed(() => {
  const config = settingsStore.platforms as any
  // mcp_servers can be at top level or under auxiliary
  return config?.mcp_servers || (settingsStore as any).config?.mcp_servers || {}
})

const serverList = computed(() => {
  const servers = mcpServers.value
  if (!servers || typeof servers !== 'object') return []
  return Object.entries(servers).map(([name, config]) => ({
    name,
    ...(config as Record<string, any>),
  })) as Array<{ name: string; command?: string; args?: string[]; url?: string; timeout?: number; [key: string]: any }>
})

function getTransport(server: Record<string, any>): string {
  if (server.command) return 'stdio'
  if (server.url) return 'http'
  return 'unknown'
}
</script>

<template>
  <section class="settings-section">
    <div v-if="serverList.length === 0" class="empty-section">
      <NEmpty :description="t('settings.mcp.noServers')" />
    </div>

    <div v-else class="mcp-server-list">
      <div v-for="server in serverList" :key="server.name" class="mcp-server-card">
        <div class="server-header">
          <span class="server-name">{{ server.name }}</span>
          <NTag size="small" round :type="getTransport(server) === 'stdio' ? 'info' : 'success'">
            {{ getTransport(server) }}
          </NTag>
        </div>
        <div class="server-details">
          <div v-if="server.command" class="detail-row">
            <span class="detail-label">Command:</span>
            <code class="detail-value">{{ server.command }} {{ (server.args || []).join(' ') }}</code>
          </div>
          <div v-if="server.url" class="detail-row">
            <span class="detail-label">URL:</span>
            <code class="detail-value">{{ server.url }}</code>
          </div>
          <div v-if="server.timeout" class="detail-row">
            <span class="detail-label">Timeout:</span>
            <span class="detail-value">{{ server.timeout }}s</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.settings-section {
  margin-top: 16px;
}

.empty-section {
  padding: 20px 0;
}

.mcp-server-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mcp-server-card {
  padding: 12px 16px;
  border: 1px solid $border-light;
  border-radius: 8px;
}

.server-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.server-name {
  font-size: 14px;
  font-weight: 600;
  color: $text-primary;
}

.server-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 12px;
}

.detail-label {
  color: $text-muted;
  min-width: 70px;
}

.detail-value {
  color: $text-secondary;
  word-break: break-all;
}

code.detail-value {
  background: var(--n-color-action, #f0f0f0);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
}
</style>
