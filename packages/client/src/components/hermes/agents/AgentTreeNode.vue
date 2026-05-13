<script setup lang="ts">
import { NTag } from 'naive-ui'
import type { AgentNode } from '@/api/hermes/agents'

defineProps<{ node: AgentNode; depth?: number }>()

function formatTime(ts: number | null): string {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleString()
}

function statusType(status: string): 'success' | 'warning' | 'error' | 'default' {
  if (status === 'running') return 'warning'
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'error'
  return 'default'
}
</script>

<template>
  <div class="tree-node" :style="{ paddingLeft: `${(depth || 0) * 24}px` }">
    <div class="node-card">
      <div class="node-header">
        <NTag size="small" :type="statusType(node.status)" round>{{ node.status }}</NTag>
        <span class="node-model">{{ node.model }}</span>
        <span v-if="node.source" class="node-source">{{ node.source }}</span>
      </div>
      <div v-if="node.title" class="node-title">{{ node.title }}</div>
      <div class="node-meta">
        <span class="node-id">{{ node.session_id.slice(0, 12) }}</span>
        <span v-if="node.started_at" class="node-time">{{ formatTime(node.started_at) }}</span>
      </div>
    </div>
    <div v-if="node.children.length > 0" class="node-children">
      <AgentTreeNode v-for="child in node.children" :key="child.session_id" :node="child" :depth="(depth || 0) + 1" />
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.tree-node {
  margin-bottom: 4px;
}

.node-card {
  padding: 8px 12px;
  border: 1px solid $border-light;
  border-radius: 6px;
  background: $bg-card;
}

.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.node-model {
  font-size: 12px;
  font-weight: 600;
  color: $text-primary;
}

.node-source {
  font-size: 11px;
  color: $text-muted;
}

.node-title {
  font-size: 13px;
  color: $text-secondary;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: $text-muted;
}

.node-id {
  font-family: monospace;
}

.node-time {
  margin-left: auto;
}

.node-children {
  margin-top: 4px;
  border-left: 2px solid $border-light;
  margin-left: 12px;
}
</style>
