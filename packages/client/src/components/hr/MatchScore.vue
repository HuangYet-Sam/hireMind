<script setup lang="ts">
import { computed } from 'vue'
import { NTooltip, NProgress } from 'naive-ui'

const props = defineProps<{
  score: number
  size?: 'small' | 'medium' | 'large'
  showLabel?: boolean
}>()

const percentage = computed(() => Math.round(props.score * 100))
const color = computed(() => {
  if (props.score >= 0.8) return '#18a058'
  if (props.score >= 0.6) return '#f0a020'
  return '#d03050'
})
const sizeMap = { small: 40, medium: 64, large: 80 }
const actualSize = computed(() => sizeMap[props.size ?? 'medium'])
</script>

<template>
  <NTooltip>
    <template #trigger>
      <div class="match-score" :style="{ width: actualSize + 'px', height: actualSize + 'px' }">
        <NProgress
          type="circle"
          :percentage="percentage"
          :color="color"
          :rail-color="'rgba(var(--accent-primary-rgb), 0.1)'"
          :stroke-width="4"
          :show-indicator="false"
          :size="size ?? 'medium'"
        />
        <span class="score-label" :style="{ color }">{{ percentage }}%</span>
      </div>
    </template>
    匹配分数: {{ percentage }}%
  </NTooltip>
</template>

<style scoped lang="scss">
.match-score {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;

  .score-label {
    position: absolute;
    font-size: 13px;
    font-weight: 600;
  }
}
</style>
