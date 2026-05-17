<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NGrid, NGridItem, NSpin, NEmpty, NDatePicker, NStatistic, NTabs, NTabPane } from 'naive-ui'
import { useAnalyticsStore } from '@/stores/hr/analytics'
import RecruitmentFunnelChart from '@/components/hr/RecruitmentFunnelChart.vue'
import TimeToHireTrendChart from '@/components/hr/TimeToHireTrendChart.vue'
import SourceEffectivenessChart from '@/components/hr/SourceEffectivenessChart.vue'
import DepartmentSummaryChart from '@/components/hr/DepartmentSummaryChart.vue'

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

        <!-- Charts Row 1: Funnel + Trend -->
        <NGrid :cols="2" :x-gap="16" :y-gap="16" responsive="screen" item-responsive style="margin-top: 16px;">
          <NGridItem span="0:2 1024:1">
            <NCard title="招聘漏斗" size="small">
              <RecruitmentFunnelChart v-if="analyticsStore.funnel.length" :data="analyticsStore.funnel" />
              <NEmpty v-else description="暂无漏斗数据" />
            </NCard>
          </NGridItem>
          <NGridItem span="0:2 1024:1">
            <NCard title="招聘周期趋势" size="small">
              <TimeToHireTrendChart v-if="analyticsStore.timeToHire.length" :data="analyticsStore.timeToHire" />
              <NEmpty v-else description="暂无趋势数据" />
            </NCard>
          </NGridItem>
        </NGrid>

        <!-- Charts Row 2: Source + Department -->
        <NGrid :cols="2" :x-gap="16" :y-gap="16" responsive="screen" item-responsive style="margin-top: 16px;">
          <NGridItem span="0:2 1024:1">
            <NCard title="渠道转化效果" size="small">
              <SourceEffectivenessChart v-if="analyticsStore.sourceEffectiveness.length" :data="analyticsStore.sourceEffectiveness" />
              <NEmpty v-else description="暂无渠道数据" />
            </NCard>
          </NGridItem>
          <NGridItem span="0:2 1024:1">
            <NCard title="部门招聘分布" size="small">
              <NTabs type="segment" size="small">
                <NTabPane name="positions" tab="按岗位">
                  <DepartmentSummaryChart v-if="analyticsStore.departmentSummary.length" :data="analyticsStore.departmentSummary" metric="positions" />
                  <NEmpty v-else description="暂无部门数据" />
                </NTabPane>
                <NTabPane name="candidates" tab="按候选人">
                  <DepartmentSummaryChart v-if="analyticsStore.departmentSummary.length" :data="analyticsStore.departmentSummary" metric="candidates" />
                  <NEmpty v-else description="暂无部门数据" />
                </NTabPane>
              </NTabs>
            </NCard>
          </NGridItem>
        </NGrid>
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
</style>
