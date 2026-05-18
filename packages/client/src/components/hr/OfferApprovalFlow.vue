<script setup lang="ts">
import { computed } from 'vue'
import { NAvatar, NTooltip, NButton, NSpace } from 'naive-ui'
import type { ApprovalNode } from '@/api/hr/offers'

const props = defineProps<{
  approvals: ApprovalNode[]
  currentStatus: string
}>()

const emit = defineEmits<{
  approve: [nodeId: string]
  reject: [nodeId: string]
}>()

/** 节点图标映射 */
const statusIconMap: Record<string, string> = {
  approved: '✅',
  rejected: '❌',
  pending: '⏳',
  waiting: '⏸️',
}

/** 节点样式类 */
function getNodeClass(node: ApprovalNode, index: number): string {
  const classes: string[] = ['approval-node']

  // 找到当前激活节点
  const activeIndex = props.approvals.findIndex(n => n.status === 'pending')
  const currentIndex = activeIndex >= 0 ? activeIndex : props.approvals.length

  if (node.status === 'approved') {
    classes.push('node-completed')
  } else if (node.status === 'rejected') {
    classes.push('node-rejected')
  } else if (index === currentIndex) {
    classes.push('node-active')
  } else {
    classes.push('node-waiting')
  }

  return classes.join(' ')
}

/** 连接线样式 */
function getConnectorClass(node: ApprovalNode): string {
  if (node.status === 'approved') return 'connector-completed'
  if (node.status === 'rejected') return 'connector-rejected'
  return 'connector-waiting'
}

function formatTime(dateStr?: string): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}

function getAvatarText(name: string): string {
  return name ? name.charAt(0) : '?'
}

/** 是否可以操作（当前待审批节点） */
function canAct(node: ApprovalNode): boolean {
  const activeNode = props.approvals.find(n => n.status === 'pending')
  return activeNode?.id === node.id && props.currentStatus === 'pending_approval'
}
</script>

<template>
  <div class="offer-approval-flow">
    <div v-if="!approvals.length" class="empty-flow">暂无审批流程</div>
    <div v-else class="flow-chain">
      <div
        v-for="(node, index) in approvals"
        :key="node.id"
        class="flow-step"
      >
        <!-- 节点内容 -->
        <div :class="getNodeClass(node, index)">
          <div class="node-avatar-wrapper">
            <NAvatar
              v-if="node.approver_avatar"
              :src="node.approver_avatar"
              :size="40"
              round
            />
            <NAvatar v-else :size="40" round class="avatar-fallback">
              {{ getAvatarText(node.approver_name) }}
            </NAvatar>
            <span class="node-status-icon">{{ statusIconMap[node.status] }}</span>
          </div>
          <div class="node-info">
            <span class="node-label">{{ node.label }}</span>
            <span class="node-approver">{{ node.approver_name }}</span>
            <span v-if="node.acted_at" class="node-time">{{ formatTime(node.acted_at) }}</span>
            <NTooltip v-if="node.comment" trigger="hover">
              <template #trigger>
                <span class="node-comment-preview">{{ node.comment }}</span>
              </template>
              {{ node.comment }}
            </NTooltip>
          </div>
          <!-- 操作按钮 -->
          <NSpace v-if="canAct(node)" size="tiny" class="node-actions">
            <NButton size="tiny" type="success" @click="emit('approve', node.id)">
              审批通过
            </NButton>
            <NButton size="tiny" type="error" @click="emit('reject', node.id)">
              拒绝
            </NButton>
          </NSpace>
        </div>
        <!-- 连接线 -->
        <div v-if="index < approvals.length - 1" :class="['flow-connector', getConnectorClass(node)]" />
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.offer-approval-flow {
  padding: 16px 0;
}

.empty-flow {
  text-align: center;
  padding: 24px;
  color: $text-muted;
  font-size: 14px;
}

.flow-chain {
  display: flex;
  align-items: flex-start;
  gap: 0;
  overflow-x: auto;
  padding-bottom: 8px;
}

.flow-step {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.approval-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 16px;
  border-radius: $radius-md;
  background: $bg-card;
  border: 2px solid $border-light;
  min-width: 120px;
  transition: border-color $transition-fast, box-shadow $transition-fast;

  .node-avatar-wrapper {
    position: relative;
    margin-bottom: 8px;

    .node-status-icon {
      position: absolute;
      bottom: -2px;
      right: -4px;
      font-size: 14px;
    }
  }

  .avatar-fallback {
    background: $bg-secondary;
    color: $text-secondary;
    font-size: 14px;
    font-weight: 500;
  }

  .node-info {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;

    .node-label {
      font-size: 13px;
      font-weight: 500;
      color: $text-primary;
    }

    .node-approver {
      font-size: 12px;
      color: $text-secondary;
    }

    .node-time {
      font-size: 11px;
      color: $text-muted;
    }

    .node-comment-preview {
      font-size: 11px;
      color: $text-muted;
      max-width: 100px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      display: inline-block;
    }
  }

  .node-actions {
    margin-top: 8px;
  }

  &.node-completed {
    border-color: var(--success);
    background: rgba(var(--success-rgb), 0.04);
  }

  &.node-rejected {
    border-color: var(--error);
    background: rgba(var(--error-rgb), 0.04);
  }

  &.node-active {
    border-color: var(--accent-info);
    box-shadow: 0 0 0 3px rgba(var(--accent-info-rgb), 0.15);
    animation: pulse-border 2s ease-in-out infinite;
  }

  &.node-waiting {
    opacity: 0.5;
    border-style: dashed;
  }
}

@keyframes pulse-border {
  0%, 100% { box-shadow: 0 0 0 3px rgba(var(--accent-info-rgb), 0.15); }
  50% { box-shadow: 0 0 0 6px rgba(var(--accent-info-rgb), 0.08); }
}

.flow-connector {
  width: 40px;
  height: 2px;
  margin: 0 -2px;
  align-self: center;
  margin-top: -20px;

  &.connector-completed {
    background: var(--success);
  }

  &.connector-rejected {
    background: var(--error);
  }

  &.connector-waiting {
    background: $border-light;
  }
}
</style>
