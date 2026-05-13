<script setup lang="ts">
import { NTag, NTooltip } from 'naive-ui'

defineProps<{
  label: string
  confidence?: number
  source?: string
}>()
</script>

<template>
  <NTooltip>
    <template #trigger>
      <NTag size="small" :bordered="false" type="info" class="ai-inference-tag">
        <span class="tag-icon">✦</span>
        {{ label }}
        <span v-if="confidence" class="confidence">{{ Math.round(confidence * 100) }}%</span>
      </NTag>
    </template>
    <div v-if="source">来源: {{ source }}</div>
    <div v-if="confidence">置信度: {{ Math.round(confidence * 100) }}%</div>
  </NTooltip>
</template>

<style scoped lang="scss">
.ai-inference-tag {
  .tag-icon {
    margin-right: 2px;
    font-size: 10px;
  }

  .confidence {
    margin-left: 4px;
    opacity: 0.7;
    font-size: 10px;
  }
}
</style>
