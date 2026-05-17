<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard, NGrid, NGridItem, NSpin, NEmpty, NStatistic, NList, NListItem,
  NTag, NSpace, NButton, NIcon, NThing, NDivider, useMessage,
} from 'naive-ui'
import { useAnalyticsStore } from '@/stores/hr/analytics'
import {
  getDashboardTodos, getDashboardSchedule, getDashboardMetrics, getDashboardAiInsights,
} from '@/api/hr/dashboard'
import type {
  TodoItem, ScheduleEvent, MetricItem, AiInsight,
} from '@/api/hr/dashboard'

const router = useRouter()
const analyticsStore = useAnalyticsStore()
const message = useMessage()

// Dashboard section data
const todos = ref<TodoItem[]>([])
const scheduleEvents = ref<ScheduleEvent[]>([])
const metrics = ref<MetricItem[]>([])
const aiInsights = ref<AiInsight[]>([])

const loadingSections = ref({
  kpi: false,
  todos: false,
  schedule: false,
  metrics: false,
  aiInsights: false,
})

const priorityColorMap: Record<string, 'default' | 'info' | 'warning' | 'error'> = {
  low: 'default',
  medium: 'info',
  high: 'warning',
  urgent: 'error',
}

const priorityLabelMap: Record<string, string> = {
  low: '低',
  medium: '中',
  high: '高',
  urgent: '紧急',
}

const eventTypeMap: Record<string, 'info' | 'success' | 'warning' | 'error'> = {
  interview: 'info',
  meeting: 'success',
  deadline: 'warning',
  reminder: 'error',
}

const eventTypeLabel: Record<string, string> = {
  interview: '面试',
  meeting: '会议',
  deadline: '截止',
  reminder: '提醒',
}

const insightTypeMap: Record<string, 'info' | 'success' | 'warning' | 'error'> = {
  recommendation: 'success',
  alert: 'error',
  summary: 'info',
  suggestion: 'warning',
}

const insightPriorityMap: Record<string, 'default' | 'info' | 'warning' | 'error'> = {
  low: 'default',
  medium: 'info',
  high: 'warning',
}

const trendIcon: Record<string, string> = {
  up: '↑',
  down: '↓',
  flat: '→',
}

const trendColor: Record<string, string> = {
  up: '#18a058',
  down: '#d03050',
  flat: '#909399',
}

onMounted(async () => {
  await Promise.allSettled([
    loadKpi(),
    loadTodos(),
    loadSchedule(),
    loadMetrics(),
    loadAiInsights(),
  ])
})

async function loadKpi() {
  loadingSections.value.kpi = true
  try {
    await analyticsStore.fetchDashboard()
  } catch {
    message.error('加载 KPI 数据失败')
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

async function loadSchedule() {
  loadingSections.value.schedule = true
  try {
    const res = await getDashboardSchedule()
    scheduleEvents.value = res.events
  } catch {
    message.error('加载日程失败')
  } finally {
    loadingSections.value.schedule = false
  }
}

async function loadMetrics() {
  loadingSections.value.metrics = true
  try {
    const res = await getDashboardMetrics()
    metrics.value = res.metrics
  } catch {
    message.error('加载指标失败')
  } finally {
    loadingSections.value.metrics = false
  }
}

async function loadAiInsights() {
  loadingSections.value.aiInsights = true
  try {
    const res = await getDashboardAiInsights()
    aiInsights.value = res.insights
  } catch {
    message.error('加载 AI 洞察失败')
  } finally {
    loadingSections.value.aiInsights = false
  }
}

function handleInsightAction(insight: AiInsight) {
  if (insight.action_link) {
    if (insight.action_link.startsWith('/')) {
      router.push(insight.action_link)
    } else {
      window.open(insight.action_link, '_blank')
    }
  }
}

function formatTime(dateStr: string) {
  const d = new Date(dateStr)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
</script>

<template>
  <div class="dashboard-view">
    <header class="page-header">
      <h2 class="header-title">工作台</h2>
      <p class="header-desc">招聘数据概览与待办事项</p>
    </header>

    <div class="dashboard-content">
      <!-- KPI Cards -->
      <NSpin :show="loadingSections.kpi">
        <NGrid :cols="4" :x-gap="16" :y-gap="16" responsive="screen" item-responsive>
          <NGridItem span="0:4 640:2 1024:1">
            <NCard size="small" class="kpi-card">
              <NStatistic label="在招岗位" :value="analyticsStore.kpi?.open_positions ?? '-'" />
            </NCard>
          </NGridItem>
          <NGridItem span="0:4 640:2 1024:1">
            <NCard size="small" class="kpi-card">
              <NStatistic label="候选人总数" :value="analyticsStore.kpi?.candidates_in_pipeline ?? '-'" />
            </NCard>
          </NGridItem>
          <NGridItem span="0:4 640:2 1024:1">
            <NCard size="small" class="kpi-card">
              <NStatistic label="本周面试" :value="analyticsStore.kpi?.interviews_this_week ?? '-'" />
            </NCard>
          </NGridItem>
          <NGridItem span="0:4 640:2 1024:1">
            <NCard size="small" class="kpi-card">
              <NStatistic label="待处理Offer" :value="analyticsStore.kpi?.offers_pending ?? '-'" />
            </NCard>
          </NGridItem>
        </NGrid>
      </NSpin>

      <!-- Quick Metrics -->
      <NCard v-if="metrics.length" title="快捷指标" size="small" style="margin-top: 16px;">
        <NSpin :show="loadingSections.metrics">
          <NGrid :cols="4" :x-gap="16" :y-gap="12" responsive="screen" item-responsive>
            <NGridItem v-for="m in metrics" :key="m.key" span="0:2 640:1">
              <div class="metric-item">
                <div class="metric-label">{{ m.label }}</div>
                <div class="metric-value">
                  {{ m.value }}<span v-if="m.unit" class="metric-unit">{{ m.unit }}</span>
                  <span
                    v-if="m.trend"
                    class="metric-trend"
                    :style="{ color: trendColor[m.trend ?? 'flat'] }"
                  >
                    {{ trendIcon[m.trend ?? 'flat'] }}
                    <template v-if="m.trend_value">{{ m.trend_value }}%</template>
                  </span>
                </div>
                <div v-if="m.period" class="metric-period">{{ m.period }}</div>
              </div>
            </NGridItem>
          </NGrid>
        </NSpin>
      </NCard>

      <NGrid :cols="1" :x-gap="16" :y-gap="16" responsive="screen" item-responsive style="margin-top: 16px;">
        <!-- Todos -->
        <NGridItem>
          <NCard title="待办事项" size="small">
            <template #header-extra>
              <NTag v-if="todos.length" size="small" type="info">{{ todos.length }}</NTag>
            </template>
            <NSpin :show="loadingSections.todos">
              <NList v-if="todos.length" hoverable clickable>
                <NListItem v-for="todo in todos" :key="todo.id">
                  <NThing :title="todo.title" :description="todo.description">
                    <template #header-extra>
                      <NTag size="small" :type="priorityColorMap[todo.priority] ?? 'default'">
                        {{ priorityLabelMap[todo.priority] ?? todo.priority }}
                      </NTag>
                    </template>
                    <template #description>
                      <NSpace size="small" align="center">
                        <span v-if="todo.due_date" class="todo-due">截止: {{ todo.due_date }}</span>
                        <NTag v-if="todo.related_type" size="tiny">{{ todo.related_type }}</NTag>
                      </NSpace>
                    </template>
                  </NThing>
                </NListItem>
              </NList>
              <NEmpty v-else description="暂无待办事项" />
            </NSpin>
          </NCard>
        </NGridItem>

        <!-- Schedule -->
        <NGridItem>
          <NCard title="今日日程" size="small">
            <template #header-extra>
              <NTag v-if="scheduleEvents.length" size="small" type="info">{{ scheduleEvents.length }}</NTag>
            </template>
            <NSpin :show="loadingSections.schedule">
              <div v-if="scheduleEvents.length" class="schedule-timeline">
                <div v-for="event in scheduleEvents" :key="event.id" class="schedule-item">
                  <div class="schedule-time">
                    <span class="time-start">{{ formatTime(event.start_time) }}</span>
                    <span v-if="event.end_time" class="time-end">- {{ formatTime(event.end_time) }}</span>
                  </div>
                  <div class="schedule-dot" :class="[`dot-${event.type}`]"></div>
                  <div class="schedule-content">
                    <div class="schedule-title">
                      <NTag size="tiny" :type="eventTypeMap[event.type] ?? 'info'">
                        {{ eventTypeLabel[event.type] ?? event.type }}
                      </NTag>
                      <span>{{ event.title }}</span>
                    </div>
                    <div v-if="event.candidate_name || event.location" class="schedule-meta">
                      <span v-if="event.candidate_name">👤 {{ event.candidate_name }}</span>
                      <span v-if="event.location">📍 {{ event.location }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <NEmpty v-else description="今日暂无日程" />
            </NSpin>
          </NCard>
        </NGridItem>
      </NGrid>

      <!-- AI Insights -->
      <NCard title="AI 洞察" size="small" style="margin-top: 16px;">
        <template #header-extra>
          <NTag v-if="aiInsights.length" size="small" type="warning">{{ aiInsights.length }}</NTag>
        </template>
        <NSpin :show="loadingSections.aiInsights">
          <NGrid v-if="aiInsights.length" :cols="1" :x-gap="12" :y-gap="12" responsive="screen" item-responsive>
            <NGridItem v-for="insight in aiInsights" :key="insight.id">
              <NCard size="small" embedded :bordered="true" class="insight-card">
                <template #header>
                  <NSpace align="center" size="small">
                    <NTag size="tiny" :type="insightTypeMap[insight.type] ?? 'info'">
                      {{ insight.type }}
                    </NTag>
                    <NTag size="tiny" :type="insightPriorityMap[insight.priority] ?? 'default'">
                      {{ insight.priority }}
                    </NTag>
                    <span class="insight-title">{{ insight.title }}</span>
                  </NSpace>
                </template>
                <p class="insight-content">{{ insight.content }}</p>
                <template v-if="insight.action_label" #action>
                  <NButton
                    text
                    type="primary"
                    size="small"
                    @click="handleInsightAction(insight)"
                  >
                    {{ insight.action_label }}
                  </NButton>
                </template>
              </NCard>
            </NGridItem>
          </NGrid>
          <NEmpty v-else description="暂无 AI 洞察" />
        </NSpin>
      </NCard>
    </div>
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

// Quick metrics
.metric-item {
  padding: 8px 0;
}

.metric-label {
  font-size: 13px;
  color: $text-muted;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 20px;
  font-weight: 600;
  color: $text-primary;
}

.metric-unit {
  font-size: 13px;
  color: $text-secondary;
  margin-left: 2px;
}

.metric-trend {
  font-size: 13px;
  margin-left: 6px;
}

.metric-period {
  font-size: 12px;
  color: $text-muted;
  margin-top: 2px;
}

// Schedule timeline
.schedule-timeline {
  position: relative;
}

.schedule-item {
  display: flex;
  align-items: flex-start;
  padding: 8px 0;
  position: relative;
}

.schedule-time {
  width: 90px;
  flex-shrink: 0;
  font-size: 13px;
  color: $text-secondary;
  text-align: right;
  padding-right: 12px;
  padding-top: 2px;

  .time-end {
    color: $text-muted;
  }
}

.schedule-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 6px;
  margin-right: 12px;

  &.dot-interview { background: #2080f0; }
  &.dot-meeting { background: #18a058; }
  &.dot-deadline { background: #f0a020; }
  &.dot-reminder { background: #d03050; }
}

.schedule-content {
  flex: 1;
  min-width: 0;
}

.schedule-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: $text-primary;
}

.schedule-meta {
  margin-top: 4px;
  font-size: 12px;
  color: $text-muted;
  display: flex;
  gap: 12px;
}

// Todo
.todo-due {
  font-size: 12px;
  color: $text-muted;
}

// AI Insight card
.insight-card {
  height: 100%;
}

.insight-title {
  font-weight: 500;
  font-size: 14px;
}

.insight-content {
  font-size: 13px;
  color: $text-secondary;
  line-height: 1.6;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
