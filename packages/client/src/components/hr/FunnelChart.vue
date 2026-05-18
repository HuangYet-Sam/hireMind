<script setup lang="ts">
/**
 * FunnelChart — M7 招聘漏斗 SVG 图表
 *
 * Props: stages (FunnelStage[])
 * 纵向漏斗形状，每阶段显示标签+人数+转化率
 * 纯 SVG 实现，响应式宽度
 */
import { computed, ref } from 'vue'
import type { FunnelStage } from '@/api/hr/dashboard'

const props = defineProps<{
  stages: FunnelStage[]
}>()

const hoveredIndex = ref<number | null>(null)

// ── Config ───────────────────────────────────────────────────

const SVG_WIDTH = 400
const SVG_HEIGHT = 360
const PADDING_TOP = 20
const PADDING_BOTTOM = 20
const PADDING_LEFT = 20
const PADDING_RIGHT = 20

const COLORS = [
  '#4a90d9', '#5ba0e0', '#6bb0e7',
  '#7bc0ee', '#8bd0f5', '#9bdef8',
  '#a8e6fb', '#b8edfd', '#c8f4fe',
]

// ── Computed layout ──────────────────────────────────────────

const maxCount = computed(() => {
  if (!props.stages.length) return 0
  return Math.max(...props.stages.map(s => s.count))
})

const stageCount = computed(() => props.stages.length)

const stageHeight = computed(() => {
  if (stageCount.value === 0) return 0
  const available = SVG_HEIGHT - PADDING_TOP - PADDING_BOTTOM
  return Math.min(available / stageCount.value, 60)
})

const gap = computed(() => Math.max(2, stageHeight.value * 0.06))

const totalHeight = computed(() => {
  return stageCount.value * stageHeight.value + (stageCount.value - 1) * gap.value
})

const offsetY = computed(() => {
  return PADDING_TOP + (SVG_HEIGHT - PADDING_TOP - PADDING_BOTTOM - totalHeight.value) / 2
})

// ── Stage geometry ───────────────────────────────────────────

interface StageGeom {
  topY: number
  bottomY: number
  topLeftX: number
  topRightX: number
  bottomLeftX: number
  bottomRightX: number
  centerX: number
  color: string
  label: string
  count: number
  conversionRate?: number
  percentage: number
}

const stageGeoms = computed<StageGeom[]>(() => {
  const geoms: StageGeom[] = []
  const centerX = SVG_WIDTH / 2
  const maxWidth = SVG_WIDTH - PADDING_LEFT - PADDING_RIGHT

  props.stages.forEach((stage, i) => {
    const ratio = maxCount.value > 0 ? stage.count / maxCount.value : 0
    // Minimum width ratio so labels fit
    const widthRatio = Math.max(ratio, 0.15)
    const topWidth = i === 0 ? maxWidth : maxWidth * Math.max(props.stages[Math.max(0, i - 1)].count / maxCount.value, 0.15)
    const bottomWidth = maxWidth * widthRatio

    const topY = offsetY.value + i * (stageHeight.value + gap.value)
    const bottomY = topY + stageHeight.value

    geoms.push({
      topY,
      bottomY,
      topLeftX: centerX - topWidth / 2,
      topRightX: centerX + topWidth / 2,
      bottomLeftX: centerX - bottomWidth / 2,
      bottomRightX: centerX + bottomWidth / 2,
      centerX,
      color: COLORS[i % COLORS.length],
      label: stage.stage,
      count: stage.count,
      conversionRate: stage.conversion_rate,
      percentage: maxCount.value > 0 ? (stage.count / maxCount.value) * 100 : 0,
    })
  })

  return geoms
})

// ── SVG path builder ─────────────────────────────────────────

function buildTrapezoidPath(geom: StageGeom): string {
  return [
    `M ${geom.topLeftX} ${geom.topY}`,
    `L ${geom.topRightX} ${geom.topY}`,
    `L ${geom.bottomRightX} ${geom.bottomY}`,
    `L ${geom.bottomLeftX} ${geom.bottomY}`,
    'Z',
  ].join(' ')
}

function getStageOpacity(index: number): number {
  if (hoveredIndex.value === null) return 0.9
  return hoveredIndex.value === index ? 1.0 : 0.5
}

function getStrokeWidth(index: number): number {
  if (hoveredIndex.value === null) return 1
  return hoveredIndex.value === index ? 2.5 : 0.5
}

function handleMouseEnter(index: number) {
  hoveredIndex.value = index
}

function handleMouseLeave() {
  hoveredIndex.value = null
}

function formatConversion(rate?: number): string {
  if (rate == null) return '-'
  return `${(rate * 100).toFixed(1)}%`
}
</script>

<template>
  <div class="funnel-chart">
    <svg
      :viewBox="`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`"
      class="funnel-svg"
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <filter id="funnel-shadow" x="-2%" y="-2%" width="104%" height="104%">
          <feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="#000" flood-opacity="0.08" />
        </filter>
      </defs>

      <g
        v-for="(geom, index) in stageGeoms"
        :key="index"
        class="funnel-stage-group"
        @mouseenter="handleMouseEnter(index)"
        @mouseleave="handleMouseLeave"
      >
        <!-- Trapezoid shape -->
        <path
          :d="buildTrapezoidPath(geom)"
          :fill="geom.color"
          :fill-opacity="getStageOpacity(index)"
          :stroke="geom.color"
          :stroke-width="getStrokeWidth(index)"
          stroke-linejoin="round"
          filter="url(#funnel-shadow)"
          class="funnel-trapezoid"
        />

        <!-- Label text -->
        <text
          :x="geom.centerX"
          :y="geom.topY + stageHeight / 2 - 4"
          text-anchor="middle"
          dominant-baseline="middle"
          fill="#fff"
          font-size="13"
          font-weight="600"
          class="funnel-label"
        >
          {{ geom.label }}
        </text>

        <!-- Count + percentage -->
        <text
          :x="geom.centerX"
          :y="geom.topY + stageHeight / 2 + 12"
          text-anchor="middle"
          dominant-baseline="middle"
          fill="rgba(255,255,255,0.85)"
          font-size="11"
          class="funnel-count"
        >
          {{ geom.count }} 人 ({{ geom.percentage.toFixed(1) }}%)
        </text>

        <!-- Conversion rate arrow (between stages) -->
        <g v-if="index > 0" class="conversion-indicator">
          <text
            :x="SVG_WIDTH - PADDING_RIGHT + 4"
            :y="geom.topY - gap / 2"
            text-anchor="start"
            dominant-baseline="middle"
            fill="#888"
            font-size="10"
          >
            ↓ {{ formatConversion(stageGeoms[index - 1] ? stageGeoms[index].conversionRate : undefined) }}
          </text>
        </g>
      </g>
    </svg>

    <!-- Tooltip -->
    <div
      v-if="hoveredIndex !== null && stageGeoms[hoveredIndex]"
      class="funnel-tooltip"
      :style="{
        top: `${(stageGeoms[hoveredIndex].topY / SVG_HEIGHT) * 100}%`,
      }"
    >
      <div class="tooltip-title">{{ stageGeoms[hoveredIndex].label }}</div>
      <div class="tooltip-row">
        <span class="tooltip-label">人数:</span>
        <span class="tooltip-value">{{ stageGeoms[hoveredIndex].count }}</span>
      </div>
      <div class="tooltip-row">
        <span class="tooltip-label">占比:</span>
        <span class="tooltip-value">{{ stageGeoms[hoveredIndex].percentage.toFixed(1) }}%</span>
      </div>
      <div v-if="hoveredIndex > 0" class="tooltip-row">
        <span class="tooltip-label">转化率:</span>
        <span class="tooltip-value">{{ formatConversion(stageGeoms[hoveredIndex].conversionRate) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.funnel-chart {
  position: relative;
  width: 100%;
  min-height: 300px;
}

.funnel-svg {
  width: 100%;
  height: 100%;
  display: block;
}

.funnel-trapezoid {
  cursor: pointer;
  transition: fill-opacity 0.2s ease, stroke-width 0.2s ease;
}

.funnel-stage-group {
  .funnel-label,
  .funnel-count {
    pointer-events: none;
    user-select: none;
  }
}

// Tooltip
.funnel-tooltip {
  position: absolute;
  right: 0;
  transform: translateY(-50%);
  background: var(--bg-card);
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  padding: 8px 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 10;
  min-width: 120px;
  pointer-events: none;

  .tooltip-title {
    font-size: 13px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 4px;
  }

  .tooltip-row {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    gap: 12px;

    .tooltip-label {
      color: $text-muted;
    }

    .tooltip-value {
      font-weight: 500;
      color: $text-primary;
    }
  }
}
</style>
