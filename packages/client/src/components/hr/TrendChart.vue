<script setup lang="ts">
/**
 * TrendChart — M7 趋势折线 SVG 图表
 *
 * Props: data (TrendDataPoint[]), period
 * 多条折线：简历/匹配/面试/Offer
 * 纯 SVG 实现，响应式
 */
import { computed, ref } from 'vue'
import type { TrendDataPoint } from '@/api/hr/dashboard'

const props = defineProps<{
  data: TrendDataPoint[]
  period?: 'day' | 'week' | 'month'
}>()

const emit = defineEmits<{
  'update:period': [period: 'day' | 'week' | 'month']
}>()

// ── Config ───────────────────────────────────────────────────

const SVG_WIDTH = 600
const SVG_HEIGHT = 300
const MARGIN = { top: 20, right: 20, bottom: 40, left: 50 }

interface LineConfig {
  key: keyof TrendDataPoint
  label: string
  color: string
}

const lines: LineConfig[] = [
  { key: 'resumes', label: '简历', color: '#4a90d9' },
  { key: 'matches', label: '匹配', color: '#18a058' },
  { key: 'interviews', label: '面试', color: '#f0a020' },
  { key: 'offers', label: 'Offer', color: '#d03050' },
]

// ── State ────────────────────────────────────────────────────

const tooltipIndex = ref<number | null>(null)
const tooltipKey = ref<string | null>(null)

// ── Computed scales ──────────────────────────────────────────

const chartWidth = computed(() => SVG_WIDTH - MARGIN.left - MARGIN.right)
const chartHeight = computed(() => SVG_HEIGHT - MARGIN.top - MARGIN.bottom)

const dataPoints = computed(() => props.data ?? [])

const maxValue = computed(() => {
  if (!dataPoints.value.length) return 100
  let max = 0
  for (const point of dataPoints.value) {
    for (const line of lines) {
      const val = point[line.key] as number
      if (val > max) max = val
    }
  }
  return Math.max(max * 1.15, 10)
})

// ── Scales ───────────────────────────────────────────────────

function xScale(index: number): number {
  const n = dataPoints.value.length
  if (n <= 1) return MARGIN.left + chartWidth.value / 2
  return MARGIN.left + (index / (n - 1)) * chartWidth.value
}

function yScale(value: number): number {
  const ratio = value / maxValue.value
  return MARGIN.top + chartHeight.value - ratio * chartHeight.value
}

// ── Line path builder ────────────────────────────────────────

function buildLinePath(dataKey: keyof TrendDataPoint): string {
  if (dataPoints.value.length < 2) return ''
  const points = dataPoints.value.map((d, i) => ({
    x: xScale(i),
    y: yScale(d[dataKey] as number),
  }))
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
}

function buildAreaPath(dataKey: keyof TrendDataPoint): string {
  if (dataPoints.value.length < 2) return ''
  const points = dataPoints.value.map((d, i) => ({
    x: xScale(i),
    y: yScale(d[dataKey] as number),
  }))
  const bottomY = MARGIN.top + chartHeight.value
  const pathParts = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`)
  pathParts.push(`L ${points[points.length - 1].x} ${bottomY}`)
  pathParts.push(`L ${points[0].x} ${bottomY}`)
  pathParts.push('Z')
  return pathParts.join(' ')
}

// ── Y-axis ticks ─────────────────────────────────────────────

const yTicks = computed(() => {
  const ticks: { y: number; label: string }[] = []
  const steps = 5
  for (let i = 0; i <= steps; i++) {
    const val = (maxValue.value / steps) * i
    ticks.push({
      y: yScale(val),
      label: Math.round(val).toString(),
    })
  }
  return ticks
})

// ── X-axis labels ────────────────────────────────────────────

const xLabels = computed(() => {
  return dataPoints.value.map((d, i) => ({
    x: xScale(i),
    label: formatDateLabel(d.date),
  }))
})

function formatDateLabel(dateStr: string): string {
  const d = new Date(dateStr)
  if (props.period === 'day') {
    return `${d.getMonth() + 1}/${d.getDate()}`
  }
  if (props.period === 'week') {
    return `W${Math.ceil(d.getDate() / 7)}`
  }
  // month
  return `${d.getMonth() + 1}月`
}

// ── Interaction ──────────────────────────────────────────────

function handlePointHover(index: number, key: string) {
  tooltipIndex.value = index
  tooltipKey.value = key
}

function handlePointLeave() {
  tooltipIndex.value = null
  tooltipKey.value = null
}

function getPointRadius(index: number, key: string): number {
  if (tooltipIndex.value === index && tooltipKey.value === key) return 5
  return 3
}

function getPointOpacity(index: number, key: string): number {
  if (tooltipIndex.value === null) return 1
  return tooltipIndex.value === index ? 1 : 0.4
}
</script>

<template>
  <div class="trend-chart">
    <!-- Legend -->
    <div class="trend-legend">
      <div
        v-for="line in lines"
        :key="line.key"
        class="legend-item"
      >
        <span class="legend-dot" :style="{ background: line.color }" />
        <span class="legend-label">{{ line.label }}</span>
      </div>
    </div>

    <svg
      :viewBox="`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`"
      class="trend-svg"
      preserveAspectRatio="xMidYMid meet"
    >
      <!-- Grid lines -->
      <g class="grid-lines">
        <line
          v-for="tick in yTicks"
          :key="'grid-' + tick.y"
          :x1="MARGIN.left"
          :y1="tick.y"
          :x2="SVG_WIDTH - MARGIN.right"
          :y2="tick.y"
          stroke="#e8e8e8"
          stroke-width="0.5"
          stroke-dasharray="4 2"
        />
      </g>

      <!-- Y axis labels -->
      <g class="axis-labels">
        <text
          v-for="tick in yTicks"
          :key="'y-' + tick.y"
          :x="MARGIN.left - 8"
          :y="tick.y"
          text-anchor="end"
          dominant-baseline="middle"
          fill="#999"
          font-size="11"
        >
          {{ tick.label }}
        </text>
      </g>

      <!-- X axis labels -->
      <g class="axis-labels">
        <text
          v-for="(label, i) in xLabels"
          :key="'x-' + i"
          :x="label.x"
          :y="SVG_HEIGHT - MARGIN.bottom + 20"
          text-anchor="middle"
          dominant-baseline="middle"
          fill="#999"
          font-size="10"
        >
          {{ label.label }}
        </text>
      </g>

      <!-- Lines + Areas + Points -->
      <g v-for="line in lines" :key="line.key" class="line-group">
        <!-- Area fill -->
        <path
          :d="buildAreaPath(line.key)"
          :fill="line.color"
          fill-opacity="0.06"
        />

        <!-- Line -->
        <path
          :d="buildLinePath(line.key)"
          :stroke="line.color"
          stroke-width="2"
          fill="none"
          stroke-linejoin="round"
          stroke-linecap="round"
        />

        <!-- Data points -->
        <g
          v-for="(point, i) in dataPoints"
          :key="`${line.key}-${i}`"
        >
          <circle
            :cx="xScale(i)"
            :cy="yScale(point[line.key] as number)"
            :r="getPointRadius(i, line.key)"
            :fill="line.color"
            :opacity="getPointOpacity(i, line.key)"
            stroke="#fff"
            stroke-width="1.5"
            class="data-point"
            @mouseenter="handlePointHover(i, line.key)"
            @mouseleave="handlePointLeave"
          />
        </g>
      </g>

      <!-- Tooltip crosshair -->
      <g v-if="tooltipIndex !== null" class="tooltip-crosshair">
        <line
          :x1="xScale(tooltipIndex)"
          :y1="MARGIN.top"
          :x2="xScale(tooltipIndex)"
          :y2="MARGIN.top + chartHeight"
          stroke="#ccc"
          stroke-width="1"
          stroke-dasharray="3 3"
        />
      </g>
    </svg>

    <!-- Tooltip overlay -->
    <div
      v-if="tooltipIndex !== null && dataPoints[tooltipIndex]"
      class="trend-tooltip"
      :style="{
        left: `${(xScale(tooltipIndex) / SVG_WIDTH) * 100}%`,
      }"
    >
      <div class="tooltip-date">{{ dataPoints[tooltipIndex].date }}</div>
      <div
        v-for="line in lines"
        :key="line.key"
        class="tooltip-row"
      >
        <span class="tooltip-dot" :style="{ background: line.color }" />
        <span class="tooltip-label">{{ line.label }}:</span>
        <span class="tooltip-value">{{ dataPoints[tooltipIndex][line.key] }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.trend-chart {
  position: relative;
  width: 100%;
  min-height: 280px;
}

.trend-svg {
  width: 100%;
  height: 100%;
  display: block;
}

// Legend
.trend-legend {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-label {
  font-size: 12px;
  color: $text-secondary;
}

// Data point interaction
.data-point {
  cursor: pointer;
  transition: r 0.15s ease, opacity 0.15s ease;
}

// Tooltip
.trend-tooltip {
  position: absolute;
  top: 10px;
  transform: translateX(-50%);
  background: var(--bg-card);
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  padding: 8px 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 10;
  min-width: 130px;
  pointer-events: none;

  .tooltip-date {
    font-size: 11px;
    color: $text-muted;
    margin-bottom: 4px;
    font-weight: 500;
  }

  .tooltip-row {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    line-height: 1.6;

    .tooltip-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    .tooltip-label {
      color: $text-muted;
    }

    .tooltip-value {
      font-weight: 600;
      color: $text-primary;
      margin-left: auto;
    }
  }
}
</style>
