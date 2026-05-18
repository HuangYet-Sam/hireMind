<script setup lang="ts">
/**
 * PositionAnalysis — M8 岗位级分析组件
 *
 * Props: positionId, data (PositionAnalysisData[])
 * 内容：岗位漏斗 + 匹配质量评分(雷达图占位) + 招聘时间线 + 面试通过率 + Offer接受率
 * 指标卡片：平均匹配分/平均招聘天数/面试通过率/Offer接受率
 * Emits: close
 */
import { computed, ref } from 'vue'
import {
  NCard, NGrid, NGridItem, NStatistic, NTag, NButton, NSpace,
  NEmpty, NSelect, NProgress,
} from 'naive-ui'
import FunnelChart from '@/components/hr/FunnelChart.vue'
import type { PositionAnalysisData } from '@/api/hr/analytics'

const props = defineProps<{
  positionId?: string
  data: PositionAnalysisData[]
}>()

const emit = defineEmits<{
  close: []
}>()

const selectedPosition = ref<string | null>(props.positionId ?? null)

const positionOptions = computed(() => {
  return props.data.map(p => ({
    label: `${p.position_title} (${p.department})`,
    value: p.position_id,
  }))
})

const currentPosition = computed(() => {
  if (!selectedPosition.value && props.data.length > 0) {
    return props.data[0]
  }
  return props.data.find(p => p.position_id === selectedPosition.value) ?? null
})

// ── Metric cards ─────────────────────────────────────────────

const avgMatchScore = computed(() => {
  if (!currentPosition.value) return '-'
  // Use performance_score as proxy for match quality
  return currentPosition.value.performance_score.toFixed(0)
})

const avgHireDays = computed(() => {
  if (!currentPosition.value) return '-'
  return currentPosition.value.avg_time_to_hire.toFixed(1)
})

const interviewPassRate = computed(() => {
  if (!currentPosition.value) return '-'
  return `${(currentPosition.value.interview_rate * 100).toFixed(1)}%`
})

const offerAcceptRate = computed(() => {
  if (!currentPosition.value) return '-'
  return `${(currentPosition.value.offer_rate * 100).toFixed(1)}%`
})

// ── Radar chart placeholder data ─────────────────────────────

const radarMetrics = computed(() => {
  if (!currentPosition.value) return []
  const pos = currentPosition.value
  return [
    { label: '候选人量', value: Math.min(pos.total_candidates / 50, 1), raw: pos.total_candidates },
    { label: '面试通过率', value: pos.interview_rate, raw: `${(pos.interview_rate * 100).toFixed(0)}%` },
    { label: 'Offer接受率', value: pos.offer_rate, raw: `${(pos.offer_rate * 100).toFixed(0)}%` },
    { label: '招聘速度', value: Math.max(0, 1 - pos.avg_time_to_hire / 60), raw: `${pos.avg_time_to_hire.toFixed(0)}天` },
    { label: '效能评分', value: pos.performance_score / 100, raw: pos.performance_score.toFixed(0) },
  ]
})

// ── Radar SVG ────────────────────────────────────────────────

const RADAR_SIZE = 200
const RADAR_CENTER = 100
const RADAR_MAX_R = 80

function polarToCartesian(angle: number, radius: number): { x: number; y: number } {
  const rad = (angle - 90) * (Math.PI / 180)
  return {
    x: RADAR_CENTER + radius * Math.cos(rad),
    y: RADAR_CENTER + radius * Math.sin(rad),
  }
}

const radarPoints = computed(() => {
  const n = radarMetrics.value.length
  if (n === 0) return ''
  const angleStep = 360 / n
  return radarMetrics.value.map((m, i) => {
    const pt = polarToCartesian(i * angleStep, m.value * RADAR_MAX_R)
    return `${pt.x},${pt.y}`
  }).join(' ')
})

const radarGridRings = [0.2, 0.4, 0.6, 0.8, 1.0]

function buildRingPath(radius: number, count: number): string {
  const points: string[] = []
  for (let i = 0; i < count; i++) {
    const pt = polarToCartesian(i * (360 / count), radius)
    points.push(`${i === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`)
  }
  points.push('Z')
  return points.join(' ')
}

// ── Timeline ─────────────────────────────────────────────────

const timelineStages = computed(() => {
  if (!currentPosition.value) return []
  return currentPosition.value.funnel_stages.map(s => ({
    label: s.stage,
    count: s.count,
    avgDays: s.avg_days_in_stage,
    conversionRate: s.conversion_rate,
  }))
})

function getPerformanceColor(score: number): string {
  if (score >= 80) return 'var(--success)'
  if (score >= 50) return 'var(--warning)'
  return 'var(--error)'
}

function getPerformanceTagType(score: number): 'success' | 'warning' | 'error' {
  if (score >= 80) return 'success'
  if (score >= 50) return 'warning'
  return 'error'
}
</script>

<template>
  <div class="position-analysis">
    <!-- Header -->
    <div class="analysis-header">
      <div class="header-left">
        <h3 class="analysis-title">岗位深度分析</h3>
        <NSelect
          v-if="positionOptions.length > 1"
          :value="selectedPosition"
          :options="positionOptions"
          placeholder="选择岗位"
          style="width: 260px;"
          @update:value="selectedPosition = $event"
        />
      </div>
      <NButton text @click="emit('close')">✕ 关闭</NButton>
    </div>

    <div v-if="!currentPosition" class="analysis-empty">
      <NEmpty description="请选择一个岗位查看分析" />
    </div>

    <div v-else class="analysis-content">
      <!-- Metric Cards -->
      <NGrid :cols="4" :x-gap="12" :y-gap="12" responsive="screen" item-responsive>
        <NGridItem span="0:4 640:2 1024:1">
          <NCard size="small" class="metric-card">
            <NStatistic label="平均匹配分">
              <template #prefix>
                <span class="metric-prefix">🎯</span>
              </template>
              {{ avgMatchScore }}
            </NStatistic>
          </NCard>
        </NGridItem>
        <NGridItem span="0:4 640:2 1024:1">
          <NCard size="small" class="metric-card">
            <NStatistic label="平均招聘天数">
              <template #prefix>
                <span class="metric-prefix">⏱️</span>
              </template>
              {{ avgHireDays }}
            </NStatistic>
          </NCard>
        </NGridItem>
        <NGridItem span="0:4 640:2 1024:1">
          <NCard size="small" class="metric-card">
            <NStatistic label="面试通过率">
              <template #prefix>
                <span class="metric-prefix">📋</span>
              </template>
              {{ interviewPassRate }}
            </NStatistic>
          </NCard>
        </NGridItem>
        <NGridItem span="0:4 640:2 1024:1">
          <NCard size="small" class="metric-card">
            <NStatistic label="Offer接受率">
              <template #prefix>
                <span class="metric-prefix">✅</span>
              </template>
              {{ offerAcceptRate }}
            </NStatistic>
          </NCard>
        </NGridItem>
      </NGrid>

      <!-- Two column layout -->
      <div class="analysis-grid">
        <!-- Left: Funnel -->
        <NCard size="small" title="招聘漏斗" class="analysis-panel">
          <FunnelChart
            v-if="currentPosition.funnel_stages.length"
            :stages="currentPosition.funnel_stages"
          />
          <NEmpty v-else description="暂无漏斗数据" size="small" />
        </NCard>

        <!-- Right: Radar chart placeholder -->
        <NCard size="small" title="匹配质量评分" class="analysis-panel">
          <div v-if="radarMetrics.length" class="radar-container">
            <svg
              :width="RADAR_SIZE"
              :height="RADAR_SIZE"
              :viewBox="`0 0 ${RADAR_SIZE} ${RADAR_SIZE}`"
              class="radar-svg"
            >
              <!-- Grid rings -->
              <path
                v-for="(ring, ri) in radarGridRings"
                :key="'ring-' + ri"
                :d="buildRingPath(ring * RADAR_MAX_R, radarMetrics.length)"
                fill="none"
                stroke="#e0e0e0"
                stroke-width="0.5"
              />

              <!-- Axis lines -->
              <line
                v-for="(_, ai) in radarMetrics"
                :key="'axis-' + ai"
                :x1="RADAR_CENTER"
                :y1="RADAR_CENTER"
                :x2="polarToCartesian(ai * (360 / radarMetrics.length), RADAR_MAX_R).x"
                :y2="polarToCartesian(ai * (360 / radarMetrics.length), RADAR_MAX_R).y"
                stroke="#e0e0e0"
                stroke-width="0.5"
              />

              <!-- Data polygon -->
              <polygon
                :points="radarPoints"
                fill="rgba(74, 144, 217, 0.2)"
                stroke="#4a90d9"
                stroke-width="2"
              />

              <!-- Data points -->
              <circle
                v-for="(m, mi) in radarMetrics"
                :key="'dp-' + mi"
                :cx="polarToCartesian(mi * (360 / radarMetrics.length), m.value * RADAR_MAX_R).x"
                :cy="polarToCartesian(mi * (360 / radarMetrics.length), m.value * RADAR_MAX_R).y"
                r="3"
                fill="#4a90d9"
                stroke="#fff"
                stroke-width="1.5"
              />

              <!-- Labels -->
              <text
                v-for="(m, mi) in radarMetrics"
                :key="'label-' + mi"
                :x="polarToCartesian(mi * (360 / radarMetrics.length), RADAR_MAX_R + 16).x"
                :y="polarToCartesian(mi * (360 / radarMetrics.length), RADAR_MAX_R + 16).y"
                text-anchor="middle"
                dominant-baseline="middle"
                fill="#666"
                font-size="10"
              >
                {{ m.label }}
              </text>
            </svg>

            <!-- Radar metrics list -->
            <div class="radar-legend">
              <div v-for="m in radarMetrics" :key="m.label" class="radar-legend-item">
                <span class="radar-legend-label">{{ m.label }}</span>
                <span class="radar-legend-value">{{ m.raw }}</span>
              </div>
            </div>
          </div>
          <NEmpty v-else description="暂无评分数据" size="small" />
        </NCard>
      </div>

      <!-- Timeline -->
      <NCard size="small" title="招聘时间线" class="analysis-panel">
        <div v-if="timelineStages.length" class="timeline-container">
          <div
            v-for="(stage, i) in timelineStages"
            :key="stage.label"
            class="timeline-item"
          >
            <div class="timeline-dot" :class="{ active: i === 0 }" />
            <div class="timeline-content">
              <div class="timeline-label">
                {{ stage.label }}
                <NTag size="tiny" :type="getPerformanceTagType(stage.conversionRate * 100)">
                  {{ (stage.conversionRate * 100).toFixed(1) }}%
                </NTag>
              </div>
              <div class="timeline-meta">
                <span>{{ stage.count }} 人</span>
                <span v-if="stage.avgDays"> · 平均 {{ stage.avgDays.toFixed(1) }} 天</span>
              </div>
            </div>
          </div>
        </div>
        <NEmpty v-else description="暂无时间线数据" size="small" />
      </NCard>

      <!-- Performance bar -->
      <NCard size="small" class="analysis-panel">
        <div class="performance-section">
          <span class="performance-label">综合效能评分</span>
          <NProgress
            type="line"
            :percentage="Math.round(currentPosition.performance_score)"
            :color="getPerformanceColor(currentPosition.performance_score)"
            :height="20"
            indicator-placement="inside"
          />
        </div>
      </NCard>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.position-analysis {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.analysis-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .analysis-title {
    font-size: 16px;
    font-weight: 600;
    color: $text-primary;
    margin: 0;
  }
}

.analysis-empty {
  padding: 40px 0;
}

.analysis-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.metric-card {
  .metric-prefix {
    font-size: 14px;
  }
}

.analysis-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;

  @media (max-width: $breakpoint-mobile) {
    grid-template-columns: 1fr;
  }
}

.analysis-panel {
  // consistent panels
}

// Radar chart
.radar-container {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
  justify-content: center;
}

.radar-svg {
  flex-shrink: 0;
}

.radar-legend {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 120px;
}

.radar-legend-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  gap: 8px;

  .radar-legend-label {
    color: $text-muted;
  }

  .radar-legend-value {
    font-weight: 600;
    color: $text-primary;
  }
}

// Timeline
.timeline-container {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding-left: 8px;
}

.timeline-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  position: relative;
  padding: 8px 0 8px 20px;

  &::before {
    content: '';
    position: absolute;
    left: 5px;
    top: 20px;
    bottom: -8px;
    width: 1px;
    background: $border-color;
  }

  &:last-child::before {
    display: none;
  }
}

.timeline-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: $border-color;
  flex-shrink: 0;
  margin-top: 4px;

  &.active {
    background: #4a90d9;
  }
}

.timeline-content {
  flex: 1;
  min-width: 0;
}

.timeline-label {
  font-size: 13px;
  font-weight: 600;
  color: $text-primary;
  display: flex;
  align-items: center;
  gap: 8px;
}

.timeline-meta {
  font-size: 12px;
  color: $text-muted;
  margin-top: 2px;
}

// Performance section
.performance-section {
  display: flex;
  align-items: center;
  gap: 16px;

  .performance-label {
    font-size: 13px;
    color: $text-secondary;
    white-space: nowrap;
    font-weight: 500;
  }

  .n-progress {
    flex: 1;
  }
}
</style>
