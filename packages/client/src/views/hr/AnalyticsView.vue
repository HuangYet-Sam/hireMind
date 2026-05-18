<script setup lang="ts">
/**
 * AnalyticsView — M7 增强版
 *
 * Tab 切换：漏斗分析 / 渠道ROI / 时间趋势 / 岗位效能
 * 复用 FunnelChart + TrendChart 组件
 */
import { ref, computed, onMounted } from 'vue'
import {
  NCard, NGrid, NGridItem, NSpin, NEmpty, NDatePicker, NStatistic,
  NTabs, NTabPane, NSelect, NDataTable, NSpace, NTag, NButton,
  useMessage,
} from 'naive-ui'
import { useAnalyticsStore } from '@/stores/hr/analytics'
import {
  fetchFunnel as fetchAnalyticsFunnel,
  fetchTrends as fetchAnalyticsTrends,
  fetchChannelROI,
  fetchPositionPerformance,
} from '@/api/hr/analytics'
import type {
  FunnelStageDetailed, TrendPoint, ChannelROI, PositionPerformance,
  AnalyticsParams,
} from '@/api/hr/analytics'
import FunnelChart from '@/components/hr/FunnelChart.vue'
import TrendChart from '@/components/hr/TrendChart.vue'

const analyticsStore = useAnalyticsStore()
const message = useMessage()

// ── State ────────────────────────────────────────────────────

const activeTab = ref('funnel')
const loading = ref(false)
const dateRange = ref<[number, number] | null>(null)
const selectedPosition = ref<string | null>(null)
const trendPeriod = ref<'day' | 'week' | 'month'>('week')

// Funnel tab
const funnelStages = ref<FunnelStageDetailed[]>([])

// Channel ROI tab
const channelROI = ref<ChannelROI[]>([])

// Trend tab
const trendData = ref<TrendPoint[]>([])

// Position performance tab
const positionPerformance = ref<PositionPerformance[]>([])

// ── Position options for dropdown ────────────────────────────

const positionOptions = computed(() => {
  return positionPerformance.value.map(p => ({
    label: p.position_title,
    value: p.position_id,
  }))
})

// ── Date params ──────────────────────────────────────────────

function getDateParams(): AnalyticsParams {
  if (!dateRange.value) return {}
  return {
    date_from: new Date(dateRange.value[0]).toISOString().split('T')[0],
    date_to: new Date(dateRange.value[1]).toISOString().split('T')[0],
  }
}

// ── Channel ROI table columns ────────────────────────────────

const channelColumns = [
  { title: '来源渠道', key: 'source', width: 120 },
  {
    title: '简历量',
    key: 'resume_count',
    width: 90,
    sorter: (a: ChannelROI, b: ChannelROI) => a.resume_count - b.resume_count,
  },
  {
    title: '面试率',
    key: 'interview_rate',
    width: 90,
    render: (row: ChannelROI) => `${(row.interview_rate * 100).toFixed(1)}%`,
    sorter: (a: ChannelROI, b: ChannelROI) => a.interview_rate - b.interview_rate,
  },
  {
    title: 'Offer率',
    key: 'offer_rate',
    width: 90,
    render: (row: ChannelROI) => `${(row.offer_rate * 100).toFixed(1)}%`,
    sorter: (a: ChannelROI, b: ChannelROI) => a.offer_rate - b.offer_rate,
  },
  {
    title: '单均成本',
    key: 'cost_per_hire',
    width: 100,
    render: (row: ChannelROI) => `¥${row.cost_per_hire.toLocaleString()}`,
    sorter: (a: ChannelROI, b: ChannelROI) => a.cost_per_hire - b.cost_per_hire,
  },
  {
    title: '总成本',
    key: 'total_cost',
    width: 100,
    render: (row: ChannelROI) => `¥${row.total_cost.toLocaleString()}`,
    sorter: (a: ChannelROI, b: ChannelROI) => a.total_cost - b.total_cost,
  },
  {
    title: 'ROI评分',
    key: 'roi_score',
    width: 90,
    render: (row: ChannelROI) => {
      const score = row.roi_score
      const type = score >= 80 ? 'success' : score >= 50 ? 'warning' : 'error'
      return h(NTag, { size: 'small', type: type }, { default: () => score.toFixed(0) })
    },
    sorter: (a: ChannelROI, b: ChannelROI) => a.roi_score - b.roi_score,
  },
]

// ── Position performance columns ─────────────────────────────

const positionColumns = [
  { title: '排名', key: 'rank', width: 60, render: (_: PositionPerformance, index: number) => index + 1 },
  { title: '岗位', key: 'position_title', width: 140 },
  { title: '部门', key: 'department', width: 100 },
  {
    title: '候选人',
    key: 'total_candidates',
    width: 80,
    sorter: (a: PositionPerformance, b: PositionPerformance) => a.total_candidates - b.total_candidates,
  },
  {
    title: '面试率',
    key: 'interview_rate',
    width: 80,
    render: (row: PositionPerformance) => `${(row.interview_rate * 100).toFixed(1)}%`,
  },
  {
    title: 'Offer率',
    key: 'offer_rate',
    width: 80,
    render: (row: PositionPerformance) => `${(row.offer_rate * 100).toFixed(1)}%`,
  },
  {
    title: '平均周期(天)',
    key: 'avg_time_to_hire',
    width: 110,
    render: (row: PositionPerformance) => row.avg_time_to_hire.toFixed(1),
    sorter: (a: PositionPerformance, b: PositionPerformance) => a.avg_time_to_hire - b.avg_time_to_hire,
  },
  {
    title: '效能评分',
    key: 'performance_score',
    width: 90,
    render: (row: PositionPerformance) => {
      const score = row.performance_score
      const type = score >= 80 ? 'success' : score >= 50 ? 'warning' : 'error'
      return h(NTag, { size: 'small', type: type }, { default: () => score.toFixed(0) })
    },
    sorter: (a: PositionPerformance, b: PositionPerformance) => a.performance_score - b.performance_score,
  },
]

// ── h helper (import from vue) ───────────────────────────────

import { h } from 'vue'

// ── Selected position funnel ─────────────────────────────────

const selectedPositionFunnel = computed(() => {
  if (!selectedPosition.value) return funnelStages.value
  const pos = positionPerformance.value.find(p => p.position_id === selectedPosition.value)
  return pos?.funnel_stages ?? funnelStages.value
})

// ── Data loading ─────────────────────────────────────────────

onMounted(async () => {
  await Promise.allSettled([
    loadAll(),
  ])
})

async function loadAll() {
  loading.value = true
  try {
    await analyticsStore.fetchAll()
    // Load M7 data in parallel
    await Promise.allSettled([
      loadFunnel(),
      loadChannelROI(),
      loadTrends(),
      loadPositionPerformance(),
    ])
  } finally {
    loading.value = false
  }
}

async function loadFunnel() {
  try {
    funnelStages.value = await fetchAnalyticsFunnel(getDateParams())
  } catch {
    // Fallback to store
    funnelStages.value = analyticsStore.funnel.map(s => ({
      stage: s.stage,
      count: s.count,
      percentage: 0,
      conversion_rate: 0,
    }))
  }
}

async function loadChannelROI() {
  try {
    channelROI.value = await fetchChannelROI(getDateParams())
  } catch {
    // No fallback — use empty
    channelROI.value = []
  }
}

async function loadTrends() {
  try {
    trendData.value = await fetchAnalyticsTrends({ period: trendPeriod.value, ...getDateParams() })
  } catch {
    // Fallback to store
    trendData.value = analyticsStore.timeToHire.map(t => ({
      date: t.period,
      resumes: t.count,
      matches: Math.round(t.count * 0.6),
      interviews: Math.round(t.count * 0.3),
      offers: Math.round(t.count * 0.1),
    }))
  }
}

async function loadPositionPerformance() {
  try {
    positionPerformance.value = await fetchPositionPerformance(getDateParams())
  } catch {
    positionPerformance.value = []
  }
}

// ── Event handlers ───────────────────────────────────────────

function handleDateChange(range: [number, number] | null) {
  dateRange.value = range
  loadAll()
}

async function handleTabChange(tab: string) {
  activeTab.value = tab
}

async function handleTrendPeriodChange(val: 'day' | 'week' | 'month') {
  trendPeriod.value = val
  await loadTrends()
}

function handlePositionFilter(val: string) {
  selectedPosition.value = val || null
}
</script>

<template>
  <div class="analytics-view">
    <header class="page-header">
      <div class="header-row">
        <div>
          <h2 class="header-title">招聘分析</h2>
          <p class="header-desc">漏斗转化、趋势分析与关键指标</p>
        </div>
        <NDatePicker type="daterange" clearable @update:value="handleDateChange" />
      </div>
    </header>

    <NSpin :show="loading">
      <div class="analytics-content">
        <!-- KPI Summary Row -->
        <NGrid :cols="4" :x-gap="16" :y-gap="16" responsive="screen" item-responsive>
          <NGridItem span="0:4 640:2 1024:1">
            <NCard size="small">
              <NStatistic label="候选人总数" :value="analyticsStore.kpi?.candidates_in_pipeline ?? '-'" />
            </NCard>
          </NGridItem>
          <NGridItem span="0:4 640:2 1024:1">
            <NCard size="small">
              <NStatistic label="平均招聘周期(天)" :value="analyticsStore.kpi?.avg_time_to_hire ?? '-'" />
            </NCard>
          </NGridItem>
          <NGridItem span="0:4 640:2 1024:1">
            <NCard size="small">
              <NStatistic label="在招岗位" :value="analyticsStore.kpi?.open_positions ?? '-'" />
            </NCard>
          </NGridItem>
          <NGridItem span="0:4 640:2 1024:1">
            <NCard size="small">
              <NStatistic label="待处理Offer" :value="analyticsStore.kpi?.offers_pending ?? '-'" />
            </NCard>
          </NGridItem>
        </NGrid>

        <!-- Tab Panels -->
        <NCard style="margin-top: 16px;">
          <NTabs v-model:value="activeTab" type="line" animated @update:value="handleTabChange">
            <!-- ── Tab 1: Funnel Analysis ── -->
            <NTabPane name="funnel" tab="漏斗分析">
              <div class="tab-content">
                <div class="tab-toolbar">
                  <NSelect
                    v-model:value="selectedPosition"
                    placeholder="全部岗位"
                    clearable
                    :options="positionOptions"
                    style="width: 200px;"
                    @update:value="handlePositionFilter"
                  />
                </div>
                <div class="funnel-container">
                  <FunnelChart
                    v-if="selectedPositionFunnel.length"
                    :stages="selectedPositionFunnel"
                  />
                  <NEmpty v-else description="暂无漏斗数据" />
                </div>
              </div>
            </NTabPane>

            <!-- ── Tab 2: Channel ROI ── -->
            <NTabPane name="channel" tab="渠道ROI">
              <div class="tab-content">
                <NDataTable
                  v-if="channelROI.length"
                  :columns="channelColumns"
                  :data="channelROI"
                  :bordered="false"
                  size="small"
                  :pagination="{ pageSize: 10 }"
                  striped
                />
                <NEmpty v-else description="暂无渠道数据" />
              </div>
            </NTabPane>

            <!-- ── Tab 3: Time Trends ── -->
            <NTabPane name="trends" tab="时间趋势">
              <div class="tab-content">
                <div class="tab-toolbar">
                  <NSpace>
                    <NButton
                      size="small"
                      :type="trendPeriod === 'day' ? 'primary' : 'default'"
                      @click="handleTrendPeriodChange('day')"
                    >
                      按日
                    </NButton>
                    <NButton
                      size="small"
                      :type="trendPeriod === 'week' ? 'primary' : 'default'"
                      @click="handleTrendPeriodChange('week')"
                    >
                      按周
                    </NButton>
                    <NButton
                      size="small"
                      :type="trendPeriod === 'month' ? 'primary' : 'default'"
                      @click="handleTrendPeriodChange('month')"
                    >
                      按月
                    </NButton>
                  </NSpace>
                </div>
                <TrendChart
                  v-if="trendData.length"
                  :data="trendData"
                  :period="trendPeriod"
                />
                <NEmpty v-else description="暂无趋势数据" />
              </div>
            </NTabPane>

            <!-- ── Tab 4: Position Performance ── -->
            <NTabPane name="positions" tab="岗位效能">
              <div class="tab-content">
                <!-- Position ranking table -->
                <NDataTable
                  v-if="positionPerformance.length"
                  :columns="positionColumns"
                  :data="positionPerformance"
                  :bordered="false"
                  size="small"
                  :pagination="{ pageSize: 10 }"
                  striped
                />
                <NEmpty v-else description="暂无岗位效能数据" />

                <!-- Position funnel comparison -->
                <div v-if="selectedPosition && selectedPositionFunnel.length" class="position-funnel-detail">
                  <h4 class="detail-title">{{ positionPerformance.find(p => p.position_id === selectedPosition)?.position_title }} — 漏斗详情</h4>
                  <FunnelChart :stages="selectedPositionFunnel" />
                </div>
              </div>
            </NTabPane>
          </NTabs>
        </NCard>
      </div>
    </NSpin>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.analytics-view {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;

  .header-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
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

.analytics-content {
  display: flex;
  flex-direction: column;
}

.tab-content {
  min-height: 400px;
}

.tab-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  gap: 12px;
}

.funnel-container {
  min-height: 320px;
}

.position-funnel-detail {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid $border-light;

  .detail-title {
    font-size: 15px;
    font-weight: 600;
    color: $text-primary;
    margin: 0 0 16px;
  }
}
</style>
