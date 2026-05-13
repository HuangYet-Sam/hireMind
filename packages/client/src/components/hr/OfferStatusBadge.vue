<script setup lang="ts">
import { computed } from 'vue'
import { NTag } from 'naive-ui'

const props = defineProps<{
  status: string
  size?: 'small' | 'medium' | 'large'
}>()

const statusConfig = computed(() => {
  const map: Record<string, { type: 'default' | 'success' | 'warning' | 'error' | 'info'; label: string }> = {
    draft: { type: 'default', label: '草稿' },
    pending_approval: { type: 'warning', label: '待审批' },
    approved: { type: 'info', label: '已审批' },
    sent: { type: 'info', label: '已发送' },
    accepted: { type: 'success', label: '已接受' },
    rejected: { type: 'error', label: '已拒绝' },
    withdrawn: { type: 'default', label: '已撤回' },
    expired: { type: 'error', label: '已过期' },
  }
  return map[props.status] || { type: 'default' as const, label: props.status }
})
</script>

<template>
  <NTag :type="statusConfig.type" :size="size ?? 'small'" round>
    {{ statusConfig.label }}
  </NTag>
</template>
