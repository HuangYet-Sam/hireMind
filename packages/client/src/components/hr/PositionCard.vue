<script setup lang="ts">
import { computed } from 'vue'
import { NCard, NTag, NButton, NSpace } from 'naive-ui'
import type { Position } from '@/api/hr/positions'

const props = defineProps<{
  position: Position
}>()

const emit = defineEmits<{
  edit: [id: string]
  close: [id: string]
}>()

const statusColor = computed(() => {
  const map: Record<string, string> = { draft: 'default', open: 'success', paused: 'warning', closed: 'error', archived: 'info' }
  return map[props.position.status] || 'default'
})
</script>

<template>
  <NCard size="small" class="position-card" hoverable>
    <div class="card-header">
      <span class="title">{{ position.title }}</span>
      <NTag :type="statusColor" size="small">{{ position.status }}</NTag>
    </div>
    <div class="card-body">
      <div class="meta-row">
        <span>{{ position.location || '-' }}</span>
      </div>
      <div class="meta-row">
        <span>人数: {{ position.headcount }}</span>
        <NTag v-if="position.priority === 'urgent'" type="error" size="small">紧急</NTag>
        <NTag v-else-if="position.priority === 'high'" type="warning" size="small">高优</NTag>
      </div>
    </div>
    <div class="card-footer">
      <NSpace size="small">
        <NButton size="tiny" @click="emit('edit', position.id)">编辑</NButton>
        <NButton v-if="position.status === 'open'" size="tiny" type="error" @click="emit('close', position.id)">关闭</NButton>
      </NSpace>
    </div>
  </NCard>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.position-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;

    .title {
      font-weight: 600;
      font-size: 15px;
      color: $text-primary;
    }
  }

  .card-body {
    .meta-row {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 13px;
      color: $text-secondary;
      margin-bottom: 4px;
    }
  }

  .card-footer {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid $border-light;
  }
}
</style>
