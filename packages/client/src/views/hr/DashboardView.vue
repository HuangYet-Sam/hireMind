<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NGrid, NGridItem, NSpin, NEmpty, NStatistic } from 'naive-ui'
import { useAnalyticsStore } from '@/stores/hr/analytics'

const analyticsStore = useAnalyticsStore()

onMounted(() => {
  analyticsStore.fetchDashboard()
})
</script>

<template>
  <div class="dashboard-view">
    <header class="page-header">
      <h2 class="header-title">工作台</h2>
      <p class="header-desc">招聘数据概览与待办事项</p>
    </header>

    <NSpin :show="analyticsStore.loading">
      <div class="dashboard-content">
        <!-- KPI Cards -->
        <NGrid :cols="4" :x-gap="16" :y-gap="16" responsive="screen" item-responsive>
          <NGridItem span="0:4 640:2 1024:1">
            <NCard size="small" class="kpi-card">
              <NStatistic label="在招岗位" :value="analyticsStore.kpi?.total_open_positions ?? '-'" />
            </NCard>
          </NGridItem>
          <NGridItem span="0:4 640:2 1024:1">
            <NCard size="small" class="kpi-card">
              <NStatistic label="候选人总数" :value="analyticsStore.kpi?.total_candidates ?? '-'" />
            </NCard>
          </NGridItem>
          <NGridItem span="0:4 640:2 1024:1">
            <NCard size="small" class="kpi-card">
              <NStatistic label="本周面试" :value="analyticsStore.kpi?.interviews_this_week ?? '-'" />
            </NCard>
          </NGridItem>
          <NGridItem span="0:4 640:2 1024:1">
            <NCard size="small" class="kpi-card">
              <NStatistic label="本月入职" :value="analyticsStore.kpi?.hires_this_month ?? '-'" />
            </NCard>
          </NGridItem>
        </NGrid>

        <!-- TODO: 待办列表 -->
        <NCard title="待办事项" size="small" style="margin-top: 16px;">
          <NEmpty description="暂无待办事项" />
        </NCard>

        <!-- TODO: 最近活动 -->
        <NCard title="最近活动" size="small" style="margin-top: 16px;">
          <NEmpty description="暂无最近活动" />
        </NCard>
      </div>
    </NSpin>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.dashboard-view {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;

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

.kpi-card {
  text-align: center;
}
</style>
