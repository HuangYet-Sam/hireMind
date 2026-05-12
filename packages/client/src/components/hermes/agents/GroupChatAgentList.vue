<script setup lang="ts">
import { NTag, NEmpty } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import type { GroupChatAgentInfo } from '@/api/hermes/agents'

defineProps<{ agents: GroupChatAgentInfo[] }>()

const { t } = useI18n()

function formatTime(ts: number | null): string {
  if (!ts) return ''
  return new Date(ts).toLocaleString()
}
</script>

<template>
  <div class="gc-agent-list">
    <div class="section-title">{{ t('agents.groupChatAgents') }}</div>
    <NEmpty v-if="agents.length === 0" :description="t('agents.noGroupChatAgents')" size="small" />
    <div v-else class="gc-agent-items">
      <div v-for="agent in agents" :key="`${agent.roomId}-${agent.agentId}`" class="gc-agent-card">
        <div class="gc-agent-header">
          <span class="gc-agent-name">{{ agent.name }}</span>
          <div class="gc-agent-tags">
            <NTag size="small" :type="agent.connected ? 'success' : 'default'" round>
              {{ agent.connected ? t('agents.online') : t('agents.offline') }}
            </NTag>
          </div>
        </div>
        <div class="gc-agent-meta">
          <span>{{ t('agents.roomName') }}: {{ agent.roomName }}</span>
          <span>{{ t('agents.profile') }}: {{ agent.profile }}</span>
        </div>
        <div v-if="agent.description" class="gc-agent-desc">{{ agent.description }}</div>
        <div v-if="agent.lastMessage" class="gc-agent-last-msg">
          <span class="gc-msg-label">{{ t('agents.lastMessage') }}:</span>
          <span class="gc-msg-content">{{ agent.lastMessage }}</span>
          <span v-if="agent.lastMessageTime" class="gc-msg-time">{{ formatTime(agent.lastMessageTime) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.gc-agent-list {
  margin-bottom: 20px;
}

.section-title {
  font-size: 12px;
  color: $text-muted;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.gc-agent-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.gc-agent-card {
  padding: 10px 12px;
  border: 1px solid $border-light;
  border-radius: 6px;
  background: $bg-card;
}

.gc-agent-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.gc-agent-name {
  font-size: 13px;
  font-weight: 600;
  color: $text-primary;
}

.gc-agent-tags {
  display: flex;
  gap: 4px;
}

.gc-agent-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: $text-muted;
  margin-bottom: 4px;
}

.gc-agent-desc {
  font-size: 12px;
  color: $text-secondary;
  margin-bottom: 4px;
}

.gc-agent-last-msg {
  padding-top: 6px;
  border-top: 1px solid $border-light;
  font-size: 12px;
  color: $text-secondary;
}

.gc-msg-label {
  color: $text-muted;
  margin-right: 4px;
}

.gc-msg-content {
  word-break: break-all;
}

.gc-msg-time {
  display: block;
  font-size: 11px;
  color: $text-muted;
  margin-top: 2px;
}
</style>
