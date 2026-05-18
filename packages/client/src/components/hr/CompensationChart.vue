<script setup lang="ts">
import { computed } from 'vue'
import { NTooltip } from 'naive-ui'
import type { CompensationBenchmark } from '@/api/hr/offers'

const props = defineProps<{
  benchmark: CompensationBenchmark
}>()

/** 最大值用于计算条形宽度百分比 */
const maxVal = computed(() => {
  const b = props.benchmark
  return Math.max(b.internal_p90, b.market_p75, b.current_offer) * 1.2
})

/** 条形宽度百分比 */
function barWidth(value: number): number {
  return Math.min((value / maxVal.value) * 100, 100)
}

/** 公平性分数对应的颜色 */
const fairnessColor = computed(() => {
  const s = props.benchmark.fairness_score
  if (s >= 70) return 'var(--success)'
  if (s >= 40) return 'var(--warning)'
  return 'var(--error)'
})

/** Offer vs 市场的比较状态 */
const marketComparison = computed(() => {
  const diff = props.benchmark.current_offer - props.benchmark.market_p50
  if (diff < -props.benchmark.market_p50 * 0.1) return 'below'
  if (diff > props.benchmark.market_p50 * 0.1) return 'above'
  return 'at'
})

/** 对比颜色 */
const comparisonColor = computed(() => {
  if (marketComparison.value === 'below') return 'var(--error)'
  if (marketComparison.value === 'above') return 'var(--success)'
  return 'var(--warning)'
})

const comparisonLabel = computed(() => {
  if (marketComparison.value === 'below') return '低于市场'
  if (marketComparison.value === 'above') return '高于市场'
  return '与市场持平'
})

/** 格式化金额 */
function formatVal(v: number): string {
  return `¥${v.toLocaleString('zh-CN')}`
}

/** 仪表盘弧度参数 */
const gaugeAngle = computed(() => {
  const score = props.benchmark.fairness_score
  return (score / 100) * 180
})

const gaugePath = computed(() => {
  const angle = gaugeAngle.value
  const rad = (angle * Math.PI) / 180
  const r = 60
  const cx = 70
  const cy = 70
  const x = cx + r * Math.cos(Math.PI - rad)
  const y = cy - r * Math.sin(rad)
  const largeArc = angle > 90 ? 1 : 0
  return `M ${cx - r} ${cy} A ${r} ${r} 0 ${largeArc} 1 ${x} ${y}`
})
</script>

<template>
  <div class="compensation-chart">
    <div class="chart-section">
      <h4 class="section-title">薪资对标分析</h4>

      <!-- 横向柱状图 -->
      <div class="bar-chart">
        <!-- 内部 P50 -->
        <div class="bar-row">
          <span class="bar-label">内部 P50</span>
          <div class="bar-track">
            <NTooltip trigger="hover">
              <template #trigger>
                <div class="bar-fill bar-internal-p50" :style="{ width: barWidth(benchmark.internal_p50) + '%' }" />
              </template>
              {{ formatVal(benchmark.internal_p50) }}
            </NTooltip>
          </div>
          <span class="bar-value">{{ formatVal(benchmark.internal_p50) }}</span>
        </div>

        <!-- 内部 P75 -->
        <div class="bar-row">
          <span class="bar-label">内部 P75</span>
          <div class="bar-track">
            <NTooltip trigger="hover">
              <template #trigger>
                <div class="bar-fill bar-internal-p75" :style="{ width: barWidth(benchmark.internal_p75) + '%' }" />
              </template>
              {{ formatVal(benchmark.internal_p75) }}
            </NTooltip>
          </div>
          <span class="bar-value">{{ formatVal(benchmark.internal_p75) }}</span>
        </div>

        <!-- 内部 P90 -->
        <div class="bar-row">
          <span class="bar-label">内部 P90</span>
          <div class="bar-track">
            <NTooltip trigger="hover">
              <template #trigger>
                <div class="bar-fill bar-internal-p90" :style="{ width: barWidth(benchmark.internal_p90) + '%' }" />
              </template>
              {{ formatVal(benchmark.internal_p90) }}
            </NTooltip>
          </div>
          <span class="bar-value">{{ formatVal(benchmark.internal_p90) }}</span>
        </div>

        <!-- 分隔线 -->
        <div class="bar-divider" />

        <!-- 市场 P50 -->
        <div class="bar-row">
          <span class="bar-label">市场 P50</span>
          <div class="bar-track">
            <NTooltip trigger="hover">
              <template #trigger>
                <div class="bar-fill bar-market-p50" :style="{ width: barWidth(benchmark.market_p50) + '%' }" />
              </template>
              {{ formatVal(benchmark.market_p50) }}
            </NTooltip>
          </div>
          <span class="bar-value">{{ formatVal(benchmark.market_p50) }}</span>
        </div>

        <!-- 市场 P75 -->
        <div class="bar-row">
          <span class="bar-label">市场 P75</span>
          <div class="bar-track">
            <NTooltip trigger="hover">
              <template #trigger>
                <div class="bar-fill bar-market-p75" :style="{ width: barWidth(benchmark.market_p75) + '%' }" />
              </template>
              {{ formatVal(benchmark.market_p75) }}
            </NTooltip>
          </div>
          <span class="bar-value">{{ formatVal(benchmark.market_p75) }}</span>
        </div>

        <!-- 分隔线 -->
        <div class="bar-divider" />

        <!-- 当前 Offer -->
        <div class="bar-row bar-row-highlight">
          <span class="bar-label">本 Offer</span>
          <div class="bar-track">
            <NTooltip trigger="hover">
              <template #trigger>
                <div
                  class="bar-fill bar-current-offer"
                  :style="{ width: barWidth(benchmark.current_offer) + '%', background: comparisonColor }"
                />
              </template>
              {{ formatVal(benchmark.current_offer) }}
            </NTooltip>
          </div>
          <span class="bar-value" :style="{ color: comparisonColor }">
            {{ formatVal(benchmark.current_offer) }}
          </span>
        </div>
      </div>
    </div>

    <!-- 公平性仪表盘 -->
    <div class="gauge-section">
      <h4 class="section-title">公平性评分</h4>
      <div class="gauge-wrapper">
        <svg viewBox="0 0 140 85" class="gauge-svg">
          <!-- 底部弧线 -->
          <path d="M 10 70 A 60 60 0 0 1 130 70" fill="none" stroke="var(--border-light)" stroke-width="12" stroke-linecap="round" />
          <!-- 分数弧线 -->
          <path :d="gaugePath" fill="none" :stroke="fairnessColor" stroke-width="12" stroke-linecap="round" />
          <!-- 分数文本 -->
          <text x="70" y="65" text-anchor="middle" font-size="24" font-weight="bold" :fill="fairnessColor">
            {{ benchmark.fairness_score }}
          </text>
        </svg>
        <div class="gauge-labels">
          <span class="gauge-min">0</span>
          <span class="gauge-max">100</span>
        </div>
      </div>
      <div class="comparison-badge" :style="{ color: comparisonColor, borderColor: comparisonColor }">
        {{ comparisonLabel }}
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.compensation-chart {
  display: grid;
  grid-template-columns: 1fr 200px;
  gap: 24px;
  padding: 8px 0;

  @media (max-width: $breakpoint-mobile) {
    grid-template-columns: 1fr;
  }
}

.section-title {
  font-size: 14px;
  font-weight: 500;
  color: $text-primary;
  margin: 0 0 12px 0;
}

.bar-chart {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bar-row {
  display: grid;
  grid-template-columns: 80px 1fr 100px;
  align-items: center;
  gap: 8px;

  &.bar-row-highlight {
    .bar-label {
      font-weight: 600;
    }
  }
}

.bar-label {
  font-size: 12px;
  color: $text-secondary;
  text-align: right;
}

.bar-track {
  height: 16px;
  background: $bg-secondary;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width $transition-normal;
  min-width: 2px;
  cursor: pointer;

  &:hover {
    opacity: 0.85;
  }
}

.bar-internal-p50 { background: rgba(var(--accent-info-rgb), 0.6); }
.bar-internal-p75 { background: rgba(var(--accent-info-rgb), 0.75); }
.bar-internal-p90 { background: rgba(var(--accent-info-rgb), 0.9); }
.bar-market-p50 { background: rgba(var(--success-rgb), 0.5); }
.bar-market-p75 { background: rgba(var(--success-rgb), 0.7); }
.bar-current-offer { background: var(--success); }

.bar-value {
  font-size: 12px;
  color: $text-secondary;
  font-variant-numeric: tabular-nums;
}

.bar-divider {
  height: 1px;
  background: $border-light;
  margin: 2px 0;
}

.gauge-section {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.gauge-wrapper {
  position: relative;
  width: 160px;
  margin-bottom: 8px;
}

.gauge-svg {
  width: 100%;
  height: auto;
}

.gauge-labels {
  display: flex;
  justify-content: space-between;
  padding: 0 16px;
  margin-top: -4px;

  span {
    font-size: 11px;
    color: $text-muted;
  }
}

.comparison-badge {
  display: inline-block;
  padding: 4px 12px;
  border: 1px solid;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  margin-top: 8px;
}
</style>
