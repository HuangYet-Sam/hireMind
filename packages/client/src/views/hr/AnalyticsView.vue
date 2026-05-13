<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NGrid, NGridItem, NSpin, NEmpty, NDatePicker, NStatistic } from 'naive-ui'
import { useAnalyticsStore } from '@/stores/hr/analytics'

const analyticsStore = useAnalyticsStore()
const dateRange = ref<[number, number] | null>(null)

onMounted(() => {
  analyticsStore.fetchAll()
})

function handleDateChange(range: [number, number] | null) {
  dateRange.value = range
  if (range) {
    const params = {
      date_from: new Date(range[0]).toISOString().split('T')[0],
      date_to: new Date(range[1]).toISOString().split('T')[0],
    }
    analyticsStore.fetchAll(params)
  } else {
    analyticsStore.fetchAll()
  }
}
</script>

<template>
  <div class="analytics-view">
    <header class="page-header">
      <h2 class="header-title">招聘分析</h2>
      <p class="header-desc">漏斗转化、趋势分析与关键指标</p>
    </header>

    <div class="analytics-controls">
      <NDatePicker type="daterange" clearable @update:value="handleDateChange" />
    </div>

    <NSpin :show="analyticsStore.loading">
      <div class="analytics-content">
        <!-- KPI Row -->
        <NGrid :cols="4" :x-gap="16" :y-gap="16" responsive="screen" item-responsive>
          <NGridItem span="0:4 640:2 1024:1">
            <NCard size="small">
              <NStatistic label="Offer接受率" :value="analyticsStore.kpi ? Math.round(analyticsStore.kpi.offer_acceptance_rate * 100) + '%' : '-'" />
            </NCard>
          </NGridItem>
          <NGridItem span="0:4 640:2 1024:1">
            <NCard size="small">
              <NStatistic label="平均招聘周期(天)" :value="analyticsStore.kpi?.avg_time_to_hire ?? '-'" />
            </NCard>
          </NGridItem>
          <NGridItem span="0:4 640:2 1024:1">
            <NCard size="small">
              <NStatistic label="在招岗位" :value="analyticsStore.kpi?.total_open_positions ?? '-'" />
            </NCard>
          </NGridItem>
          <NGridItem span="0:4 640:2 1024:1">
            <NCard size="small">
              <NStatistic label="待处理Offer" :value="analyticsStore.kpi?.offers_pending ?? '-'" />
            </NCard>
          </NGridItem>
        </NGrid>

        <!-- Recruitment Funnel -->
        <NCard title="招聘漏斗" size="small" style="margin-top: 16px;">
          <div v-if="analyticsStore.funnel.length" class="funnel-chart">
            <div v-for="stage in analyticsStore.funnel" :key="stage.stage" class="funnel-stage">
              <div class="funnel-bar" :style="{ width: stage.conversion_rate * 100 + '%' }">
                {{ stage.stage }}: {{ stage.count }}
              </div>
            </div>
          </div>
          <NEmpty v-else description="暂无漏斗数据" />
        </NCard>

        <!-- Trend Chart Placeholder -->
        <NCard title="招聘趋势" size="small" style="margin-top: 16px;">
          <NEmpty description="趋势图表开发中（集成 ECharts）" />
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

.analytics-controls {
  margin-bottom: 16px;
}

.funnel-chart {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.funnel-stage {
  .funnel-bar {
    height: 32px;
    background: rgba(var(--accent-primary-rgb), 0.15);
    border-radius: $radius-sm;
    display: flex;
    align-items: center;
    padding: 0 12px;
    font-size: 13px;
    color: $text-primary;
    min-width: 80px;
  }
}
</style>
