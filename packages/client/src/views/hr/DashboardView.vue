<script setup lang="ts">
/**
 * DashboardView — M7 重构版
 *
 * NGrid 响应式布局 Dashboard 主页面
 * 顶部 KPI 卡片 → 待办 + AI洞察 → 漏斗 + 趋势 → 来源分布 + 快捷操作
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard, NGrid, NGridItem, NSpin, NEmpty, NTag, NSpace, NButton,
  useMessage, NRadioGroup, NRadioButton,
} from 'naive-ui'

import { useAnalyticsStore } from '@/stores/hr/analytics'
import {
  getDashboardTodos, getDashboardSchedule, getDashboardAiInsights,
  fetchMetrics, fetchFunnel, fetchTrends, fetchSources, fetchInsights,
} from '@/api/hr/dashboard'
import type {
  TodoItem, ScheduleEvent, AiInsight, KpiMetrics,
  FunnelStage, TrendDataPoint, SourceDistribution, AIInsight,
} from '@/api/hr/dashboard'

import DashboardTodoList from '@/components/hr/DashboardTodoList.vue'
import DashboardInsights from '@/components/hr/DashboardInsights.vue'
import FunnelChart from '@/components/hr/FunnelChart.vue'
import TrendChart from '@/components/hr/TrendChart.vue'

const router = useRouter()
const analyticsStore = useAnalyticsStore()
const message = useMessage()

// ── Data refs ────────────────────────────────────────────────

const todos = ref<TodoItem[]>([])
const scheduleEvents = ref<ScheduleEvent[]>([])
const aiInsights = ref<AiInsight[]>([])
const kpiMetrics = ref<KpiMetrics | null>(null)
const funnelStages = ref<FunnelStage[]>([])
const trendData = ref<TrendDataPoint[]>([])
const sourceData = ref<SourceDistribution[]>([])
const insightsData = ref<AIInsight[]>([])

const trendPeriod = ref<'day' | 'week' | 'month'>('week')

const loadingSections = ref({
  kpi: false,
  todos: false,
  insights: false,
  charts: false,
  sources: false,
})

// ── KPI Cards config ─────────────────────────────────────────

const kpiCards = computed(() => {
  const kpi = kpiMetrics.value
  return [
    {
      label: '在招岗位',
      value: kpi?.open_positions ?? '-',
      icon: '📋',
      trend: kpi?.open_positions_trend,
      route: '/hr/positions',
      color: '#4a90d9',
    },
    {
      label: '候选人总数',
      value: kpi?.candidates_in_pipeline ?? '-',
      icon: '👥',
      trend: kpi?.candidates_trend,
      route: '/hr/candidates',
      color: '#18a058',
    },
    {
      label: '本周面试',
      value: kpi?.interviews_this_week ?? '-',
      icon: '🎯',
      trend: kpi?.interviews_trend,
      route: '/hr/interviews',
      color: '#f0a020',
    },
    {
      label: '待处理Offer',
      value: kpi?.offers_pending ?? '-',
      icon: '📝',
      trend: kpi?.offers_trend,
      route: '/hr/offers',
      color: '#d03050',
    },
  ]
})

// ── Source pie chart data (SVG) ──────────────────────────────

const SOURCE_COLORS = ['#4a90d9', '#18a058', '#f0a020', '#d03050', '#8b5cf6', '#06b6d4', '#f97316']

const sourcePieData = computed(() => {
  if (!sourceData.value.length) return []
  const total = sourceData.value.reduce((sum, s) => sum + s.count, 0)
  let currentAngle = -Math.PI / 2

  return sourceData.value.map((s, i) => {
    const fraction = s.count / total
    const startAngle = currentAngle
    const endAngle = currentAngle + fraction * 2 * Math.PI
    currentAngle = endAngle

    const cx = 100
    const cy = 100
    const r = 80
    const ir = 50

    const x1 = cx + r * Math.cos(startAngle)
    const y1 = cy + r * Math.sin(startAngle)
    const x2 = cx + r * Math.cos(endAngle)
    const y2 = cy + r * Math.sin(endAngle)
    const ix1 = cx + ir * Math.cos(endAngle)
    const iy1 = cy + ir * Math.sin(endAngle)
    const ix2 = cx + ir * Math.cos(startAngle)
    const iy2 = cy + ir * Math.sin(startAngle)

    const largeArc = fraction > 0.5 ? 1 : 0

    const path = [
      `M ${x1} ${y1}`,
      `A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`,
      `L ${ix1} ${iy1}`,
      `A ${ir} ${ir} 0 ${largeArc} 0 ${ix2} ${iy2}`,
      'Z',
    ].join(' ')

    // Label position (midpoint angle)
    const midAngle = (startAngle + endAngle) / 2
    const labelR = (r + ir) / 2
    const lx = cx + labelR * Math.cos(midAngle)
    const ly = cy + labelR * Math.sin(midAngle)

    return {
      source: s.source,
      count: s.count,
      percentage: s.percentage,
      color: s.color ?? SOURCE_COLORS[i % SOURCE_COLORS.length],
      path,
      labelX: lx,
      labelY: ly,
      fraction,
    }
  })
})

// ── Quick actions ────────────────────────────────────────────

const quickActions = [
  { label: '创建岗位', icon: '📋', route: '/hr/positions' },
  { label: '添加候选人', icon: '👤', route: '/hr/candidates' },
  { label: '安排面试', icon: '🎯', route: '/hr/interviews' },
  { label: '发Offer', icon: '📝', route: '/hr/offers' },
  { label: '招聘分析', icon: '📊', route: '/hr/analytics' },
]

// ── Schedule helpers ─────────────────────────────────────────

const eventTypeMap: Record<string, 'info' | 'success' | 'warning' | 'error'> = {
  interview: 'info', meeting: 'success', deadline: 'warning', reminder: 'error',
}

const eventTypeLabel: Record<string, string> = {
  interview: '面试', meeting: '会议', deadline: '截止', reminder: '提醒',
}

// ── Data loading ─────────────────────────────────────────────

onMounted(async () => {
  await Promise.allSettled([
    loadKpi(),
    loadTodos(),
    loadInsights(),
    loadCharts(),
    loadSources(),
  ])
})

async function loadKpi() {
  loadingSections.value.kpi = true
  try {
    kpiMetrics.value = await fetchMetrics()
  } catch {
    // Fallback to analytics store KPI
    await analyticsStore.fetchDashboard()
    const kpi = analyticsStore.kpi
    if (kpi) {
      kpiMetrics.value = {
        open_positions: kpi.open_positions,
        candidates_in_pipeline: kpi.candidates_in_pipeline,
        interviews_this_week: kpi.interviews_this_week,
        offers_pending: kpi.offers_pending,
      }
    }
  } finally {
    loadingSections.value.kpi = false
  }
}

async function loadTodos() {
  loadingSections.value.todos = true
  try {
    const res = await getDashboardTodos()
    todos.value = res.items
  } catch {
    message.error('加载待办事项失败')
  } finally {
    loadingSections.value.todos = false
  }
}

async function loadInsights() {
  loadingSections.value.insights = true
  try {
    insightsData.value = await fetchInsights()
  } catch {
    // Fallback to old API
    try {
      const res = await getDashboardAiInsights()
      aiInsights.value = res.insights
    } catch {
      message.error('加载 AI 洞察失败')
    }
  } finally {
    loadingSections.value.insights = false
  }
}

async function loadCharts() {
  loadingSections.value.charts = true
  try {
    const [funnelData, trends] = await Promise.all([
      fetchFunnel(),
      fetchTrends({ period: trendPeriod.value }),
    ])
    funnelStages.value = funnelData
    trendData.value = trends
  } catch {
    // Fallback to analytics store
    await Promise.all([
      analyticsStore.fetchFunnel(),
      analyticsStore.fetchTimeToHire({ group_by: trendPeriod.value }),
    ])
    funnelStages.value = analyticsStore.funnel.map(s => ({
      stage: s.stage,
      count: s.count,
      percentage: s.count > 0 ? (s.count / (analyticsStore.funnel[0]?.count || 1)) * 100 : 0,
      conversion_rate: 0,
    }))
    trendData.value = analyticsStore.timeToHire.map(t => ({
      date: t.period,
      resumes: t.count,
      matches: Math.round(t.count * 0.6),
      interviews: Math.round(t.count * 0.3),
      offers: Math.round(t.count * 0.1),
    }))
  } finally {
    loadingSections.value.charts = false
  }
}

async function loadSources() {
  loadingSections.value.sources = true
  try {
    sourceData.value = await fetchSources()
  } catch {
    // Fallback to analytics store
    await analyticsStore.fetchSourceEffectiveness()
    sourceData.value = analyticsStore.sourceEffectiveness.map(s => ({
      source: s.source,
      count: s.total,
      percentage: s.conversion_rate * 100,
    }))
  } finally {
    loadingSections.value.sources = false
  }
}

// ── Event handlers ───────────────────────────────────────────

async function handleTrendPeriodChange(val: 'day' | 'week' | 'month') {
  trendPeriod.value = val
  try {
    trendData.value = await fetchTrends({ period: val })
  } catch {
    await analyticsStore.fetchTimeToHire({ group_by: val })
    trendData.value = analyticsStore.timeToHire.map(t => ({
      date: t.period,
      resumes: t.count,
      matches: Math.round(t.count * 0.6),
      interviews: Math.round(t.count * 0.3),
      offers: Math.round(t.count * 0.1),
    }))
  }
}

function handleTodoClick(todo: TodoItem) {
  if (todo.related_type) {
    router.push(`/hr/${todo.related_type}s`)
  }
}

async function handleRefreshTodos() {
  await loadTodos()
}

async function handleRefreshInsights() {
  await loadInsights()
}

function navigateTo(route: string) {
  router.push(route)
}

function formatTime(dateStr: string) {
  const d = new Date(dateStr)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function formatTrend(trend?: number): string {
  if (trend == null) return ''
  const sign = trend >= 0 ? '↑' : '↓'
  return `${sign} ${Math.abs(trend).toFixed(1)}%`
}

function trendClass(trend?: number): string {
  if (trend == null) return ''
  return trend >= 0 ? 'trend-up' : 'trend-down'
}
</script>

<template>
  <div class="dashboard-view">
    <header class="page-header">
      <div class="header-row">
        <div>
          <h2 class="header-title">工作台</h2>
          <p class="header-desc">招聘数据概览与待办事项</p>
        </div>
        <NSpace>
          <NButton size="small" @click="navigateTo('/hr/analytics')">
            📊 查看分析
          </NButton>
        </NSpace>
      </div>
    </header>

    <div class="dashboard-content">
      <!-- ═══ Row 1: KPI Cards ═══ -->
      <NSpin :show="loadingSections.kpi">
        <NGrid :cols="4" :x-gap="16" :y-gap="16" responsive="screen" item-responsive>
          <NGridItem v-for="card in kpiCards" :key="card.label" span="0:4 640:2 1024:1">
            <NCard size="small" class="kpi-card" hoverable @click="navigateTo(card.route)">
              <div class="kpi-card-inner">
                <div class="kpi-icon" :style="{ background: `${card.color}15`, color: card.color }">
                  {{ card.icon }}
                </div>
                <div class="kpi-info">
                  <div class="kpi-label">{{ card.label }}</div>
                  <div class="kpi-value-row">
                    <span class="kpi-value">{{ card.value }}</span>
                    <span
                      v-if="card.trend != null"
                      class="kpi-trend"
                      :class="trendClass(card.trend)"
                    >
                      {{ formatTrend(card.trend) }}
                    </span>
                  </div>
                </div>
              </div>
            </NCard>
          </NGridItem>
        </NGrid>
      </NSpin>

      <!-- ═══ Row 2: Todo List + AI Insights ═══ -->
      <NGrid :cols="24" :x-gap="16" :y-gap="16" responsive="screen" item-responsive style="margin-top: 16px;">
        <!-- Left: Todo List -->
        <NGridItem span="0:24 1024:14">
          <NCard title="待办清单" size="small">
            <template #header-extra>
              <NTag v-if="todos.length" size="small" type="info" round>{{ todos.length }}</NTag>
            </template>
            <DashboardTodoList
              :todos="todos"
              :loading="loadingSections.todos"
              @item-click="handleTodoClick"
              @refresh="handleRefreshTodos"
            />
          </NCard>
        </NGridItem>

        <!-- Right: AI Insights -->
        <NGridItem span="0:24 1024:10">
          <NCard title="AI 洞察" size="small">
            <template #header-extra>
              <NTag v-if="insightsData.length" size="small" type="warning" round>
                {{ insightsData.length }}
              </NTag>
            </template>
            <DashboardInsights
              :insights="insightsData"
              :loading="loadingSections.insights"
              @refresh="handleRefreshInsights"
            />
          </NCard>
        </NGridItem>
      </NGrid>

      <!-- ═══ Row 3: Funnel + Trend ═══ -->
      <NSpin :show="loadingSections.charts">
        <NGrid :cols="24" :x-gap="16" :y-gap="16" responsive="screen" item-responsive style="margin-top: 16px;">
          <!-- Funnel Chart -->
          <NGridItem span="0:24 1024:10">
            <NCard title="招聘漏斗" size="small">
              <FunnelChart v-if="funnelStages.length" :stages="funnelStages" />
              <NEmpty v-else description="暂无漏斗数据" size="small" />
            </NCard>
          </NGridItem>

          <!-- Trend Chart -->
          <NGridItem span="0:24 1024:14">
            <NCard size="small">
              <template #header>
                <NSpace justify="space-between" align="center" style="width: 100%;">
                  <span>趋势折线图</span>
                  <NRadioGroup
                    :value="trendPeriod"
                    size="small"
                    @update:value="handleTrendPeriodChange"
                  >
                    <NRadioButton value="day">日</NRadioButton>
                    <NRadioButton value="week">周</NRadioButton>
                    <NRadioButton value="month">月</NRadioButton>
                  </NRadioGroup>
                </NSpace>
              </template>
              <TrendChart
                v-if="trendData.length"
                :data="trendData"
                :period="trendPeriod"
              />
              <NEmpty v-else description="暂无趋势数据" size="small" />
            </NCard>
          </NGridItem>
        </NGrid>
      </NSpin>

      <!-- ═══ Row 4: Source Distribution + Quick Actions ═══ -->
      <NGrid :cols="24" :x-gap="16" :y-gap="16" responsive="screen" item-responsive style="margin-top: 16px;">
        <!-- Source Distribution -->
        <NGridItem span="0:24 1024:14">
          <NCard title="来源分布" size="small">
            <NSpin :show="loadingSections.sources">
              <div v-if="sourcePieData.length" class="source-chart-area">
                <svg viewBox="0 0 200 200" class="source-pie-svg">
                  <g v-for="(slice, i) in sourcePieData" :key="i">
                    <path
                      :d="slice.path"
                      :fill="slice.color"
                      stroke="#fff"
                      stroke-width="1"
                      class="pie-slice"
                    />
                    <text
                      v-if="slice.fraction > 0.08"
                      :x="slice.labelX"
                      :y="slice.labelY"
                      text-anchor="middle"
                      dominant-baseline="middle"
                      fill="#fff"
                      font-size="10"
                      font-weight="600"
                    >
                      {{ slice.percentage.toFixed(0) }}%
                    </text>
                  </g>
                </svg>
                <div class="source-legend">
                  <div v-for="(slice, i) in sourcePieData" :key="'legend-' + i" class="source-legend-item">
                    <span class="legend-dot" :style="{ background: slice.color }" />
                    <span class="legend-name">{{ slice.source }}</span>
                    <span class="legend-count">{{ slice.count }}</span>
                    <span class="legend-pct">{{ slice.percentage.toFixed(1) }}%</span>
                  </div>
                </div>
              </div>
              <NEmpty v-else description="暂无来源数据" size="small" />
            </NSpin>
          </NCard>
        </NGridItem>

        <!-- Quick Actions -->
        <NGridItem span="0:24 1024:10">
          <NCard title="快捷操作" size="small">
            <div class="quick-actions">
              <div
                v-for="action in quickActions"
                :key="action.label"
                class="action-item"
                @click="navigateTo(action.route)"
              >
                <span class="action-icon">{{ action.icon }}</span>
                <span class="action-label">{{ action.label }}</span>
              </div>
            </div>

            <!-- Today's schedule snippet -->
            <div v-if="scheduleEvents.length" class="schedule-snippet">
              <div class="snippet-title">今日日程</div>
              <div class="schedule-mini-list">
                <div v-for="event in scheduleEvents.slice(0, 4)" :key="event.id" class="schedule-mini-item">
                  <span class="mini-time">{{ formatTime(event.start_time) }}</span>
                  <NTag size="tiny" :type="eventTypeMap[event.type] ?? 'info'">
                    {{ eventTypeLabel[event.type] ?? event.type }}
                  </NTag>
                  <span class="mini-title">{{ event.title }}</span>
                </div>
                <div v-if="scheduleEvents.length > 4" class="more-schedule">
                  还有 {{ scheduleEvents.length - 4 }} 项...
                </div>
              </div>
            </div>
          </NCard>
        </NGridItem>
      </NGrid>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.dashboard-view {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;

  .header-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
  }

  .header-title {
    font-size: 22px;
    font-weight: 600;
    color: $text-primary;
    margin: 0 0 4px;
  }

  .header-desc {
    font-size: 14px;
    color: $text-muted;
    margin: 0;
  }
}

// KPI Cards
.kpi-card {
  cursor: pointer;
  transition: transform $transition-fast, box-shadow $transition-fast;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }
}

.kpi-card-inner {
  display: flex;
  align-items: center;
  gap: 16px;
}

.kpi-icon {
  font-size: 28px;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: $radius-md;
  flex-shrink: 0;
}

.kpi-info {
  flex: 1;
  min-width: 0;
}

.kpi-label {
  font-size: 13px;
  color: $text-muted;
  margin-bottom: 4px;
}

.kpi-value-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: $text-primary;
  line-height: 1.2;
}

.kpi-trend {
  font-size: 12px;
  font-weight: 500;

  &.trend-up { color: var(--success); }
  &.trend-down { color: var(--error); }
}

// Source distribution chart
.source-chart-area {
  display: flex;
  align-items: center;
  gap: 24px;
}

.source-pie-svg {
  width: 180px;
  height: 180px;
  flex-shrink: 0;

  .pie-slice {
    transition: opacity 0.2s ease;
    cursor: pointer;

    &:hover {
      opacity: 0.85;
    }
  }
}

.source-legend {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;

  .legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .legend-name {
    color: $text-primary;
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .legend-count {
    color: $text-secondary;
    font-weight: 500;
  }

  .legend-pct {
    color: $text-muted;
    font-size: 12px;
    min-width: 45px;
    text-align: right;
  }
}

// Quick actions
.quick-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 16px;
}

.action-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-radius: $radius-sm;
  border: 1px solid $border-light;
  cursor: pointer;
  transition: background $transition-fast, border-color $transition-fast;

  &:hover {
    background: $bg-card-hover;
    border-color: $border-color;
  }

  .action-icon {
    font-size: 18px;
  }

  .action-label {
    font-size: 14px;
    color: $text-primary;
    font-weight: 500;
  }
}

// Schedule snippet
.schedule-snippet {
  border-top: 1px solid $border-light;
  padding-top: 12px;
  margin-top: 4px;
}

.snippet-title {
  font-size: 13px;
  font-weight: 600;
  color: $text-secondary;
  margin-bottom: 8px;
}

.schedule-mini-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.schedule-mini-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;

  .mini-time {
    font-size: 12px;
    color: $text-muted;
    min-width: 44px;
    font-variant-numeric: tabular-nums;
  }

  .mini-title {
    color: $text-primary;
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.more-schedule {
  font-size: 12px;
  color: $text-muted;
  text-align: center;
  padding-top: 4px;
}
</style>
