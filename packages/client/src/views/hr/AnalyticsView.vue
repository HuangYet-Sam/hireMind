<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  NCard, NGrid, NGridItem, NSpin, NEmpty, NDatePicker, NStatistic,
  NTabs, NTabPane, NSelect, NDataTable, NSpace, NTag, NButton,
  NButtonGroup, NProgress,
  useMessage,
} from 'naive-ui'
import { h } from 'vue'
import { useAnalyticsStore } from '@/stores/hr/analytics'
import {
  fetchFunnel as fetchAnalyticsFunnel,
  fetchTrends as fetchAnalyticsTrends,
  fetchChannelROI,
  fetchPositionPerformance,
  fetchFunnelComparison,
  fetchTrendPrediction,
  fetchPositionAnalytics,
  fetchChannelROIEnhanced,
} from '@/api/hr/analytics'
import type {
  FunnelStageDetailed, TrendPoint, ChannelROI, PositionPerformance,
  AnalyticsParams, ComparisonMode, ComparisonFunnelData,
  TrendWithPrediction, PositionAnalysisData, ChannelROIEnhanced,
} from '@/api/hr/analytics'
import FunnelChart from '@/components/hr/FunnelChart.vue'
import TrendChart from '@/components/hr/TrendChart.vue'
import PredictionChart from '@/components/hr/PredictionChart.vue'
import PositionAnalysis from '@/components/hr/PositionAnalysis.vue'

const analyticsStore = useAnalyticsStore()
const message = useMessage()

const activeTab = ref('funnel')
const loading = ref(false)
const dateRange = ref<[number, number] | null>(null)
const selectedPosition = ref<string | null>(null)
const trendPeriod = ref<'day' | 'week' | 'month'>('week')
const showPrediction = ref(false)

const funnelStages = ref<FunnelStageDetailed[]>([])
const channelROI = ref<ChannelROI[]>([])
const trendData = ref<TrendPoint[]>([])
const positionPerformance = ref<PositionPerformance[]>([])

const comparisonMode = ref<ComparisonMode>('none')
const comparisonData = ref<ComparisonFunnelData | null>(null)

const trendWithPrediction = ref<TrendWithPrediction | null>(null)

const positionAnalysisData = ref<PositionAnalysisData[]>([])

const channelROIEnhanced = ref<ChannelROIEnhanced[]>([])

// M8: Expanded position row tracking
const expandedPositionId = ref<string | null>(null)

// M8: Comparison quick period buttons
const comparisonPeriodOptions = [
  { label: '无对比', value: 'none' },
  { label: '上周', value: 'mom' as ComparisonMode },
  { label: '上月', value: 'mom' as ComparisonMode },
  { label: '去年', value: 'yoy' as ComparisonMode },
]

const positionOptions = computed(() => {
  return positionPerformance.value.map(p => ({
    label: p.position_title,
    value: p.position_id,
  }))
})

function getDateParams(): AnalyticsParams {
  if (!dateRange.value) return {}
  return {
    date_from: new Date(dateRange.value[0]).toISOString().split('T')[0],
    date_to: new Date(dateRange.value[1]).toISOString().split('T')[0],
  }
}

const comparisonModeOptions = [
  { label: '无对比', value: 'none' },
  { label: '同比 (去年同期)', value: 'yoy' },
  { label: '环比 (上一周期)', value: 'mom' },
]

const channelColumns = computed(() => {
  const useEnhanced = channelROIEnhanced.value.length > 0
  const data = useEnhanced ? channelROIEnhanced.value : channelROI.value

  if (useEnhanced) {
    // Sort by ROI score descending
    const sorted = [...(data as ChannelROIEnhanced[])].sort((a, b) => b.roi_score - a.roi_score)

    return [
      { title: '排名', key: 'rank', width: 55,
        render: (_: ChannelROIEnhanced, index: number) => {
          const color = index === 0 ? '#18a058' : index === 1 ? '#4a90d9' : index === 2 ? '#f0a020' : '#999'
          return h('span', { style: { fontWeight: 600, color } }, `#${index + 1}`)
        },
      },
      { title: '来源渠道', key: 'source', width: 120,
        render: (row: ChannelROIEnhanced) => {
          const gradeColor = row.roi_grade === 'A' ? '#18a058' : row.roi_grade === 'B' ? '#4a90d9' : row.roi_grade === 'C' ? '#f0a020' : '#d03050'
          return h('span', { style: { fontWeight: 500, borderLeft: `3px solid ${gradeColor}`, paddingLeft: '8px' } }, row.source)
        },
      },
      {
        title: '简历量',
        key: 'resume_count',
        width: 85,
        sorter: (a: ChannelROIEnhanced, b: ChannelROIEnhanced) => a.resume_count - b.resume_count,
      },
      {
        title: '面试率',
        key: 'interview_rate',
        width: 85,
        render: (row: ChannelROIEnhanced) => `${(row.interview_rate * 100).toFixed(1)}%`,
        sorter: (a: ChannelROIEnhanced, b: ChannelROIEnhanced) => a.interview_rate - b.interview_rate,
      },
      {
        title: 'Offer率',
        key: 'offer_rate',
        width: 85,
        render: (row: ChannelROIEnhanced) => `${(row.offer_rate * 100).toFixed(1)}%`,
        sorter: (a: ChannelROIEnhanced, b: ChannelROIEnhanced) => a.offer_rate - b.offer_rate,
      },
      {
        title: '总成本',
        key: 'total_cost',
        width: 100,
        render: (row: ChannelROIEnhanced) => `¥${row.total_cost.toLocaleString()}`,
        sorter: (a: ChannelROIEnhanced, b: ChannelROIEnhanced) => a.total_cost - b.total_cost,
      },
      {
        title: '单聘成本',
        key: 'cost_per_hire',
        width: 100,
        render: (row: ChannelROIEnhanced) => `¥${row.cost_per_hire.toLocaleString()}`,
        sorter: (a: ChannelROIEnhanced, b: ChannelROIEnhanced) => a.cost_per_hire - b.cost_per_hire,
      },
      {
        title: '成本效率',
        key: 'cost_efficiency_score',
        width: 100,
        render: (row: ChannelROIEnhanced) => {
          return h(NProgress, {
            type: 'line',
            percentage: Math.round(row.cost_efficiency_score),
            indicatorPlacement: 'inside',
            height: 16,
            railColor: '#e8e8e8',
          })
        },
        sorter: (a: ChannelROIEnhanced, b: ChannelROIEnhanced) => a.cost_efficiency_score - b.cost_efficiency_score,
      },
      {
        title: '质量评分',
        key: 'quality_score',
        width: 85,
        render: (row: ChannelROIEnhanced) => {
          const type = row.quality_score >= 80 ? 'success' : row.quality_score >= 50 ? 'warning' : 'error'
          return h(NTag, { size: 'small', type }, { default: () => row.quality_score.toFixed(0) })
        },
        sorter: (a: ChannelROIEnhanced, b: ChannelROIEnhanced) => a.quality_score - b.quality_score,
      },
      {
        title: 'ROI评分',
        key: 'roi_score',
        width: 85,
        defaultSortOrder: 'descend',
        render: (row: ChannelROIEnhanced) => {
          const score = row.roi_score
          const type = score >= 80 ? 'success' : score >= 50 ? 'warning' : 'error'
          return h(NTag, { size: 'small', type }, { default: () => score.toFixed(0) })
        },
        sorter: (a: ChannelROIEnhanced, b: ChannelROIEnhanced) => a.roi_score - b.roi_score,
      },
      {
        title: '等级',
        key: 'roi_grade',
        width: 60,
        render: (row: ChannelROIEnhanced) => {
          const gradeMap: Record<string, string> = { A: 'success', B: 'warning', C: 'error', D: 'error' }
          return h(NTag, { size: 'small', type: gradeMap[row.roi_grade] ?? 'default' }, { default: () => row.roi_grade })
        },
      },
    ]
  }

  return [
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
      title: '总成本',
      key: 'total_cost',
      width: 100,
      render: (row: ChannelROI) => `¥${row.total_cost.toLocaleString()}`,
      sorter: (a: ChannelROI, b: ChannelROI) => a.total_cost - b.total_cost,
    },
    {
      title: '单聘成本',
      key: 'cost_per_hire',
      width: 100,
      render: (row: ChannelROI) => `¥${row.cost_per_hire.toLocaleString()}`,
      sorter: (a: ChannelROI, b: ChannelROI) => a.cost_per_hire - b.cost_per_hire,
    },
    {
      title: 'ROI评分',
      key: 'roi_score',
      width: 90,
      defaultSortOrder: 'descend',
      render: (row: ChannelROI) => {
        const score = row.roi_score
        const type = score >= 80 ? 'success' : score >= 50 ? 'warning' : 'error'
        return h(NTag, { size: 'small', type: type }, { default: () => score.toFixed(0) })
      },
      sorter: (a: ChannelROI, b: ChannelROI) => a.roi_score - b.roi_score,
    },
  ]
})

const channelData = computed(() => {
  const raw = channelROIEnhanced.value.length > 0 ? channelROIEnhanced.value : channelROI.value
  // Sort by ROI score descending
  return [...raw].sort((a, b) => b.roi_score - a.roi_score)
})

const positionColumns = computed(() => [
  {
    title: '展开',
    key: 'expand',
    width: 50,
    render: (row: PositionPerformance) => {
      return h(NButton, {
        text: true,
        size: 'small',
        type: expandedPositionId.value === row.position_id ? 'primary' : 'default',
        onClick: () => {
          expandedPositionId.value = expandedPositionId.value === row.position_id ? null : row.position_id
        },
      }, { default: () => expandedPositionId.value === row.position_id ? '▼' : '▶' })
    },
  },
  { title: '排名', key: 'rank', width: 55, render: (_: PositionPerformance, index: number) => index + 1 },
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
])

const selectedPositionFunnel = computed(() => {
  if (!selectedPosition.value) return funnelStages.value
  const pos = positionPerformance.value.find(p => p.position_id === selectedPosition.value)
  return pos?.funnel_stages ?? funnelStages.value
})

const expandedPositionFunnel = computed(() => {
  if (!expandedPositionId.value) return null
  const pos = positionPerformance.value.find(p => p.position_id === expandedPositionId.value)
  return pos?.funnel_stages ?? null
})

const comparisonPreviousFunnel = computed(() => {
  if (!comparisonData.value) return null
  return comparisonData.value.previous
})

const comparisonLabel = computed(() => {
  if (!comparisonData.value) return ''
  return comparisonData.value.previous_period_label
})

// M8: Comparison delta calculation per stage
const comparisonDeltas = computed(() => {
  if (!comparisonData.value || !comparisonPreviousFunnel.value) return []
  return selectedPositionFunnel.value.map((stage, i) => {
    const prev = comparisonPreviousFunnel.value?.[i]
    if (!prev) return { stage: stage.stage, delta: 0, deltaPercent: 0 }
    const delta = stage.count - prev.count
    const deltaPercent = prev.count > 0 ? (delta / prev.count) * 100 : 0
    return { stage: stage.stage, delta, deltaPercent }
  })
})

onMounted(async () => {
  await Promise.allSettled([loadAll()])
})

async function loadAll() {
  loading.value = true
  try {
    await analyticsStore.fetchAll()
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
    funnelStages.value = analyticsStore.funnel.map(s => ({
      stage: s.stage,
      count: s.count,
      percentage: 0,
      conversion_rate: 0,
    }))
  }
}

async function loadComparisonFunnel() {
  if (comparisonMode.value === 'none') {
    comparisonData.value = null
    return
  }
  try {
    comparisonData.value = await fetchFunnelComparison({
      ...getDateParams(),
      comparison_mode: comparisonMode.value,
    })
  } catch {
    comparisonData.value = null
    message.warning('同比/环比数据暂不可用')
  }
}

async function loadChannelROI() {
  try {
    channelROIEnhanced.value = await fetchChannelROIEnhanced(getDateParams())
  } catch {
    channelROIEnhanced.value = []
    try {
      channelROI.value = await fetchChannelROI(getDateParams())
    } catch {
      channelROI.value = []
    }
  }
}

async function loadTrends() {
  try {
    if (showPrediction.value) {
      trendWithPrediction.value = await fetchTrendPrediction({
        period: trendPeriod.value,
        predict_periods: 3,
        ...getDateParams(),
      })
      trendData.value = trendWithPrediction.value.historical
    } else {
      trendData.value = await fetchAnalyticsTrends({ period: trendPeriod.value, ...getDateParams() })
      trendWithPrediction.value = null
    }
  } catch {
    if (showPrediction.value) {
      trendWithPrediction.value = null
    }
    try {
      trendData.value = await fetchAnalyticsTrends({ period: trendPeriod.value, ...getDateParams() })
    } catch {
      trendData.value = analyticsStore.timeToHire.map(t => ({
        date: t.period,
        resumes: t.count,
        matches: Math.round(t.count * 0.6),
        interviews: Math.round(t.count * 0.3),
        offers: Math.round(t.count * 0.1),
      }))
    }
  }
}

async function loadPositionPerformance() {
  try {
    positionPerformance.value = await fetchPositionPerformance(getDateParams())
  } catch {
    positionPerformance.value = []
  }

  try {
    positionAnalysisData.value = await fetchPositionAnalytics(getDateParams())
  } catch {
    positionAnalysisData.value = []
  }
}

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

async function handleComparisonModeChange(val: ComparisonMode) {
  comparisonMode.value = val
  await loadComparisonFunnel()
}

async function handlePredictionToggle() {
  showPrediction.value = !showPrediction.value
  await loadTrends()
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

        <NCard style="margin-top: 16px;">
          <NTabs v-model:value="activeTab" type="line" animated @update:value="handleTabChange">
            <!-- Tab 1: Funnel Analysis with YoY/MoM Comparison -->
            <NTabPane name="funnel" tab="漏斗分析">
              <div class="tab-content">
                <div class="tab-toolbar">
                  <NSpace>
                    <NSelect
                      v-model:value="selectedPosition"
                      placeholder="全部岗位"
                      clearable
                      :options="positionOptions"
                      style="width: 200px;"
                      @update:value="handlePositionFilter"
                    />
                    <NSelect
                      :value="comparisonMode"
                      :options="comparisonModeOptions"
                      style="width: 180px;"
                      @update:value="handleComparisonModeChange"
                    />
                  </NSpace>
                </div>

                <div class="funnel-container">
                  <FunnelChart
                    v-if="selectedPositionFunnel.length"
                    :stages="selectedPositionFunnel"
                  />
                  <NEmpty v-else description="暂无漏斗数据" />
                </div>

                <!-- M8: Comparison side-by-side view -->
                <div v-if="comparisonPreviousFunnel && comparisonPreviousFunnel.length" class="comparison-section">
                  <h4 class="comparison-title">
                    {{ comparisonLabel }} 对比
                  </h4>
                  <div class="comparison-grid">
                    <div class="comparison-col">
                      <span class="comparison-label">当前周期</span>
                      <FunnelChart :stages="selectedPositionFunnel" />
                    </div>
                    <div class="comparison-col">
                      <span class="comparison-label">{{ comparisonLabel }}</span>
                      <FunnelChart :stages="comparisonPreviousFunnel" />
                    </div>
                  </div>

                  <!-- M8: Delta indicators -->
                  <div v-if="comparisonDeltas.length" class="delta-table">
                    <h5 class="delta-title">变化详情</h5>
                    <div class="delta-rows">
                      <div
                        v-for="d in comparisonDeltas"
                        :key="d.stage"
                        class="delta-row"
                      >
                        <span class="delta-stage">{{ d.stage }}</span>
                        <span
                          class="delta-value"
                          :class="{
                            'delta-positive': d.delta > 0,
                            'delta-negative': d.delta < 0,
                            'delta-neutral': d.delta === 0,
                          }"
                        >
                          {{ d.delta > 0 ? '+' : '' }}{{ d.delta }}
                          ({{ d.deltaPercent > 0 ? '+' : '' }}{{ d.deltaPercent.toFixed(1) }}%)
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </NTabPane>

            <!-- Tab 2: Channel ROI Enhanced (sorted, color-coded) -->
            <NTabPane name="channel" tab="渠道ROI">
              <div class="tab-content">
                <NDataTable
                  v-if="channelData.length"
                  :columns="channelColumns"
                  :data="channelData"
                  :bordered="false"
                  size="small"
                  :pagination="{ pageSize: 10 }"
                  striped
                />
                <NEmpty v-else description="暂无渠道数据" />
              </div>
            </NTabPane>

            <!-- Tab 3: Time Trends with Prediction -->
            <NTabPane name="trends" tab="时间趋势">
              <div class="tab-content">
                <div class="tab-toolbar">
                  <NSpace>
                    <NButtonGroup size="small">
                      <NButton
                        :type="trendPeriod === 'day' ? 'primary' : 'default'"
                        @click="handleTrendPeriodChange('day')"
                      >
                        按日
                      </NButton>
                      <NButton
                        :type="trendPeriod === 'week' ? 'primary' : 'default'"
                        @click="handleTrendPeriodChange('week')"
                      >
                        按周
                      </NButton>
                      <NButton
                        :type="trendPeriod === 'month' ? 'primary' : 'default'"
                        @click="handleTrendPeriodChange('month')"
                      >
                        按月
                      </NButton>
                    </NButtonGroup>
                    <NButton
                      size="small"
                      :type="showPrediction ? 'primary' : 'default'"
                      @click="handlePredictionToggle"
                    >
                      {{ showPrediction ? '隐藏预测' : '显示预测' }}
                    </NButton>
                  </NSpace>
                </div>

                <!-- M8: Prediction chart with dashed line + confidence interval -->
                <PredictionChart
                  v-if="showPrediction && trendWithPrediction"
                  :historical="trendWithPrediction.historical"
                  :prediction="trendWithPrediction.prediction"
                  :period="trendPeriod"
                />
                <TrendChart
                  v-else-if="trendData.length"
                  :data="trendData"
                  :period="trendPeriod"
                />
                <NEmpty v-else description="暂无趋势数据" />
              </div>
            </NTabPane>

            <!-- Tab 4: Position Performance with expandable funnel -->
            <NTabPane name="positions" tab="岗位效能">
              <div class="tab-content">
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

                <!-- M8: Expandable position funnel detail -->
                <div v-if="expandedPositionFunnel" class="position-funnel-detail">
                  <h4 class="detail-title">
                    {{ positionPerformance.find(p => p.position_id === expandedPositionId)?.position_title }} — 完整漏斗
                  </h4>
                  <FunnelChart :stages="expandedPositionFunnel" />
                </div>
              </div>
            </NTabPane>

            <!-- Tab 5: Position Analysis (detailed) -->
            <NTabPane name="position-analysis" tab="岗位分析">
              <div class="tab-content">
                <PositionAnalysis :data="positionAnalysisData" />
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

.comparison-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid $border-light;

  .comparison-title {
    font-size: 15px;
    font-weight: 600;
    color: $text-primary;
    margin: 0 0 16px;
    text-align: center;
  }

  .comparison-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;

    @media (max-width: $breakpoint-mobile) {
      grid-template-columns: 1fr;
    }
  }

  .comparison-col {
    display: flex;
    flex-direction: column;
    align-items: center;

    .comparison-label {
      font-size: 12px;
      color: $text-muted;
      margin-bottom: 8px;
      font-weight: 500;
    }
  }
}

// M8: Delta table
.delta-table {
  margin-top: 20px;
  padding: 12px 16px;
  background: $bg-secondary;
  border-radius: $radius-sm;

  .delta-title {
    font-size: 13px;
    font-weight: 600;
    color: $text-primary;
    margin: 0 0 12px;
  }

  .delta-rows {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 8px;
  }

  .delta-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 10px;
    background: $bg-card;
    border-radius: $radius-sm;
    font-size: 12px;

    .delta-stage {
      color: $text-secondary;
      font-weight: 500;
    }

    .delta-value {
      font-weight: 600;
    }

    .delta-positive {
      color: var(--success);
    }

    .delta-negative {
      color: var(--error);
    }

    .delta-neutral {
      color: $text-muted;
    }
  }
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
