<script setup lang="ts">
import { NTag, NEmpty } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import type { GatewayInfo } from '@/api/hermes/agents'

defineProps<{ gateways: GatewayInfo[] }>()

const { t } = useI18n()
</script>

<template>
  <div class="gateway-list">
    <div class="section-title">{{ t('agents.gateways') }}</div>
    <NEmpty v-if="gateways.length === 0" :description="t('agents.noGateways')" size="small" />
    <div v-else class="gateway-items">
      <div v-for="gw in gateways" :key="gw.profile" class="gateway-card">
        <div class="gateway-header">
          <span class="gateway-profile">{{ gw.profile }}</span>
          <NTag size="small" :type="gw.running ? 'success' : 'default'" round>
            {{ gw.running ? t('agents.running') : t('agents.stopped') }}
          </NTag>
        </div>
        <div class="gateway-meta">
          <span v-if="gw.running">{{ t('agents.port') }}: {{ gw.port }}</span>
          <span v-if="gw.pid">PID: {{ gw.pid }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.gateway-list {
  margin-bottom: 20px;
}

.section-title {
  font-size: 12px;
  color: $text-muted;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.gateway-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.gateway-card {
  padding: 8px 12px;
  border: 1px solid $border-light;
  border-radius: 6px;
  background: $bg-card;
}

.gateway-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.gateway-profile {
  font-size: 13px;
  font-weight: 600;
  color: $text-primary;
}

.gateway-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: $text-muted;
  margin-top: 4px;
}
</style>
