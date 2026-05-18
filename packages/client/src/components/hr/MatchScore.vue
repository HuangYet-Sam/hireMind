<script setup lang="ts">
import { computed } from 'vue'
import { NTooltip, NProgress } from 'naive-ui'

const props = withDefaults(defineProps<{
  score: number
  size?: 'small' | 'medium' | 'large'
  showLabel?: boolean
}>(), {
  size: 'medium',
  showLabel: true,
})

const percentage = computed(() => Math.round(props.score * 100))

const tier = computed<'strong' | 'good' | 'fair' | 'poor'>(() => {
  if (props.score >= 0.8) return 'strong'
  if (props.score >= 0.6) return 'good'
  if (props.score >= 0.4) return 'fair'
  return 'poor'
})

const tierColors: Record<string, string> = {
  strong: '#18a058',
  good: '#2080f0',
  fair: '#f0a020',
  poor: '#d03050',
}

const color = computed(() => tierColors[tier.value])

const tierLabels: Record<string, string> = {
  strong: 'Strong',
  good: 'Good',
  fair: 'Fair',
  poor: 'Poor',
}

const tierLabel = computed(() => tierLabels[tier.value])

const sizeMap: Record<string, number> = { small: 40, medium: 64, large: 80 }
const actualSize = computed(() => sizeMap[props.size])
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
          :size="size"
        />
        <span v-if="showLabel" class="score-label" :style="{ color }">{{ percentage }}</span>
      </div>
    </template>
    {{ tierLabel }} — {{ percentage }}%
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
