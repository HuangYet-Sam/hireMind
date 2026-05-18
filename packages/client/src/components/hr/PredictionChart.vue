<script setup lang="ts">
/**
 * PredictionChart — M8 预测折线 SVG 图表
 *
 * Props: historical (TrendDataPoint[]), prediction (PredictionPoint[]), period
 * 实际数据实线 + 预测数据虚线 + 置信区间阴影
 * 纯 SVG 实现
 */
import { computed, ref } from 'vue'
import type { TrendDataPoint } from '@/api/hr/dashboard'
import type { PredictionPoint } from '@/api/hr/analytics'

const props = defineProps<{
  historical: TrendDataPoint[]
  prediction: PredictionPoint[]
  period?: 'day' | 'week' | 'month'
}>()

// ── Config ───────────────────────────────────────────────────

const SVG_WIDTH = 700
const SVG_HEIGHT = 320
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

// ── Computed scales ──────────────────────────────────────────

const chartWidth = computed(() => SVG_WIDTH - MARGIN.left - MARGIN.right)
const chartHeight = computed(() => SVG_HEIGHT - MARGIN.top - MARGIN.bottom)

// Merge all dates into one timeline
const allDates = computed(() => {
  const dates: string[] = []
  for (const d of props.historical) dates.push(d.date)
  for (const d of props.prediction) {
    if (!dates.includes(d.date)) dates.push(d.date)
  }
  return dates
})

const historicalCount = computed(() => props.historical.length)

// Max value across all lines
const maxValue = computed(() => {
  let max = 0
  for (const point of props.historical) {
    for (const line of lines) {
      const val = point[line.key] as number
      if (val > max) max = val
    }
  }
  for (const point of props.prediction) {
    if (point.predicted > max) max = point.predicted
    if (point.upper_bound && point.upper_bound > max) max = point.upper_bound
  }
  return Math.max(max * 1.15, 10)
})

// ── Scales ───────────────────────────────────────────────────

function xScale(index: number): number {
  const n = allDates.value.length
  if (n <= 1) return MARGIN.left + chartWidth.value / 2
  return MARGIN.left + (index / (n - 1)) * chartWidth.value
}

function yScale(value: number): number {
  const ratio = value / maxValue.value
  return MARGIN.top + chartHeight.value - ratio * chartHeight.value
}

// ── Historical line path ────────────────────────────────────

function buildHistoricalLinePath(dataKey: keyof TrendDataPoint): string {
  if (props.historical.length < 2) return ''
  return props.historical
    .map((d, i) => {
      const x = xScale(i)
      const y = yScale(d[dataKey] as number)
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`
    })
    .join(' ')
}

// ── Prediction line path (dashed) ──────────────────────────

function buildPredictionLinePath(): string {
  if (props.prediction.length < 2) return ''
  // Start from last historical point, connect to prediction
  const pts: { x: number; y: number }[] = []

  // Bridge from last historical to first prediction
  if (props.historical.length > 0) {
    const lastHist = props.historical[props.historical.length - 1]
    const lastIdx = props.historical.length - 1
    pts.push({ x: xScale(lastIdx), y: yScale(lastHist.resumes) })
  }

  for (let i = 0; i < props.prediction.length; i++) {
    const globalIdx = historicalCount.value + i
    // Only add if not duplicate date with last historical
    if (i === 0 && props.historical.length > 0) {
      const overlapDate = props.historical[props.historical.length - 1]?.date
      if (props.prediction[i].date === overlapDate) {
        pts[0] = { x: xScale(globalIdx), y: yScale(props.prediction[i].predicted) }
        continue
      }
    }
    pts.push({ x: xScale(globalIdx), y: yScale(props.prediction[i].predicted) })
  }

  return pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
}

// ── Confidence interval ────────────────────────────────────

function buildConfidenceArea(): string {
  if (props.prediction.length < 2) return ''
  const upperPts: { x: number; y: number }[] = []
  const lowerPts: { x: number; y: number }[] = []

  for (let i = 0; i < props.prediction.length; i++) {
    const globalIdx = historicalCount.value + i
    const p = props.prediction[i]
    const x = xScale(globalIdx)
    upperPts.push({ x, y: yScale(p.upper_bound ?? p.predicted * 1.2) })
    lowerPts.push({ x, y: yScale(p.lower_bound ?? p.predicted * 0.8) })
  }

  const pathParts: string[] = []
  // Forward along upper
  upperPts.forEach((p, i) => pathParts.push(`${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`))
  // Backward along lower
  lowerPts.reverse().forEach((p, i) => pathParts.push(`L ${p.x} ${p.y}`))
  pathParts.push('Z')
  return pathParts.join(' ')
}

// ── Y-axis ticks ─────────────────────────────────────────────

const yTicks = computed(() => {
  const ticks: { y: number; label: string }[] = []
  const steps = 5
  for (let i = 0; i <= steps; i++) {
    const val = (maxValue.value / steps) * i
    ticks.push({ y: yScale(val), label: Math.round(val).toString() })
  }
  return ticks
})

// ── X-axis labels ────────────────────────────────────────────

const xLabels = computed(() => {
  return allDates.value.map((date, i) => ({
    x: xScale(i),
    label: formatDateLabel(date),
    isPrediction: i >= historicalCount.value,
  }))
})

function formatDateLabel(dateStr: string): string {
  const d = new Date(dateStr)
  if (props.period === 'day') return `${d.getMonth() + 1}/${d.getDate()}`
  if (props.period === 'week') return `W${Math.ceil(d.getDate() / 7)}`
  return `${d.getMonth() + 1}月`
}

// ── Interaction ──────────────────────────────────────────────

function handlePointHover(index: number) {
  tooltipIndex.value = index
}

function handlePointLeave() {
  tooltipIndex.value = null
}

function getPointRadius(index: number): number {
  return tooltipIndex.value === index ? 5 : 3
}

function getPointOpacity(index: number): number {
  if (tooltipIndex.value === null) return 1
  return tooltipIndex.value === index ? 1 : 0.4
}

// ── Historical last index for prediction separator ──────────

const separatorX = computed(() => {
  if (historicalCount.value === 0) return MARGIN.left
  if (props.prediction.length === 0) return SVG_WIDTH - MARGIN.right
  const lastHistX = xScale(historicalCount.value - 1)
  const firstPredX = xScale(historicalCount.value)
  return (lastHistX + firstPredX) / 2
})
</script>

<template>
  <div class="prediction-chart">
    <!-- Legend -->
    <div class="prediction-legend">
      <div v-for="line in lines" :key="'hist-' + line.key" class="legend-item">
        <span class="legend-line" :style="{ background: line.color }" />
        <span class="legend-label">{{ line.label }} (实际)</span>
      </div>
      <div class="legend-item">
        <span class="legend-line legend-line-dashed" />
        <span class="legend-label">预测</span>
      </div>
      <div class="legend-item">
        <span class="legend-area-indicator" />
        <span class="legend-label">置信区间</span>
      </div>
    </div>

    <svg
      :viewBox="`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`"
      class="prediction-svg"
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
          :fill="label.isPrediction ? '#4a90d9' : '#999'"
          font-size="10"
        >
          {{ label.label }}
        </text>
      </g>

      <!-- Prediction separator line -->
      <line
        :x1="separatorX"
        :y1="MARGIN.top"
        :x2="separatorX"
        :y2="MARGIN.top + chartHeight"
        stroke="#4a90d9"
        stroke-width="1"
        stroke-dasharray="6 4"
        opacity="0.5"
      />

      <!-- Confidence interval area -->
      <path
        v-if="prediction.length >= 2"
        :d="buildConfidenceArea()"
        fill="#4a90d9"
        fill-opacity="0.1"
        stroke="none"
      />

      <!-- Historical lines -->
      <g v-for="line in lines" :key="line.key" class="line-group">
        <!-- Area fill (historical only) -->
        <path
          v-if="historical.length >= 2"
          :d="(function() {
            const pts = historical.map((d, i) => ({ x: xScale(i), y: yScale(d[line.key] as number) }))
            const bottomY = MARGIN.top + chartHeight
            const parts = pts.map((p, i) => (i === 0 ? 'M' : 'L') + ' ' + p.x + ' ' + p.y)
            parts.push('L ' + pts[pts.length - 1].x + ' ' + bottomY)
            parts.push('L ' + pts[0].x + ' ' + bottomY)
            parts.push('Z')
            return parts.join(' ')
          })()"
          :fill="line.color"
          fill-opacity="0.06"
        />

        <!-- Historical line (solid) -->
        <path
          :d="buildHistoricalLinePath(line.key)"
          :stroke="line.color"
          stroke-width="2"
          fill="none"
          stroke-linejoin="round"
          stroke-linecap="round"
        />

        <!-- Historical data points -->
        <circle
          v-for="(point, i) in historical"
          :key="`${line.key}-h-${i}`"
          :cx="xScale(i)"
          :cy="yScale(point[line.key] as number)"
          :r="getPointRadius(i)"
          :fill="line.color"
          :opacity="getPointOpacity(i)"
          stroke="#fff"
          stroke-width="1.5"
          class="data-point"
          @mouseenter="handlePointHover(i)"
          @mouseleave="handlePointLeave"
        />
      </g>

      <!-- Prediction line (dashed) -->
      <path
        v-if="prediction.length >= 1"
        :d="buildPredictionLinePath()"
        stroke="#4a90d9"
        stroke-width="2"
        stroke-dasharray="8 4"
        fill="none"
        stroke-linejoin="round"
        stroke-linecap="round"
      />

      <!-- Prediction data points -->
      <circle
        v-for="(point, i) in prediction"
        :key="'pred-' + i"
        :cx="xScale(historicalCount + i)"
        :cy="yScale(point.predicted)"
        :r="getPointRadius(historicalCount + i)"
        fill="#4a90d9"
        :opacity="getPointOpacity(historicalCount + i)"
        stroke="#fff"
        stroke-width="1.5"
        class="data-point"
        @mouseenter="handlePointHover(historicalCount + i)"
        @mouseleave="handlePointLeave"
      />

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
      v-if="tooltipIndex !== null && allDates[tooltipIndex]"
      class="prediction-tooltip"
      :style="{ left: `${(xScale(tooltipIndex) / SVG_WIDTH) * 100}%` }"
    >
      <div class="tooltip-date">{{ allDates[tooltipIndex] }}</div>
      <div v-if="tooltipIndex < historicalCount" class="tooltip-section">
        <div
          v-for="line in lines"
          :key="line.key"
          class="tooltip-row"
        >
          <span class="tooltip-dot" :style="{ background: line.color }" />
          <span class="tooltip-label">{{ line.label }}:</span>
          <span class="tooltip-value">{{ historical[tooltipIndex][line.key] }}</span>
        </div>
      </div>
      <div v-else class="tooltip-section">
        <div class="tooltip-row">
          <span class="tooltip-dot" style="background: #4a90d9" />
          <span class="tooltip-label">预测:</span>
          <span class="tooltip-value">{{ prediction[tooltipIndex - historicalCount]?.predicted }}</span>
        </div>
        <div
          v-if="prediction[tooltipIndex - historicalCount]?.upper_bound"
          class="tooltip-row"
        >
          <span class="tooltip-label" style="margin-left: 14px">区间:</span>
          <span class="tooltip-value">
            {{ prediction[tooltipIndex - historicalCount]?.lower_bound?.toFixed(0) }} ~
            {{ prediction[tooltipIndex - historicalCount]?.upper_bound?.toFixed(0) }}
          </span>
        </div>
      </div>
      <div class="tooltip-tag">
        {{ tooltipIndex < historicalCount ? '实际' : '预测' }}
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.prediction-chart {
  position: relative;
  width: 100%;
  min-height: 300px;
}

.prediction-svg {
  width: 100%;
  height: 100%;
  display: block;
}

// Legend
.prediction-legend {
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

.legend-line {
  width: 16px;
  height: 2px;
  border-radius: 1px;
  flex-shrink: 0;

  &.legend-line-dashed {
    background: repeating-linear-gradient(
      90deg,
      #4a90d9 0px,
      #4a90d9 4px,
      transparent 4px,
      transparent 6px
    );
    height: 2px;
  }
}

.legend-area-indicator {
  width: 16px;
  height: 10px;
  border-radius: 2px;
  background: rgba(74, 144, 217, 0.2);
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
.prediction-tooltip {
  position: absolute;
  top: 10px;
  transform: translateX(-50%);
  background: var(--bg-card);
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  padding: 8px 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 10;
  min-width: 140px;
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

  .tooltip-tag {
    margin-top: 4px;
    font-size: 10px;
    color: #4a90d9;
    font-weight: 600;
  }
}
</style>
