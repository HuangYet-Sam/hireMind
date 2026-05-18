<script setup lang="ts">
import { ref, onMounted, h, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton, NDataTable, NTag, NSpace, NSelect, NButtonGroup,
  NCard, NStatistic, NGrid, NGi, NIcon, NInput, NDatePicker,
  NCollapse, NCollapseItem, useMessage,
} from 'naive-ui'
import type { DataTableColumns, DataTableSortState } from 'naive-ui'
import { useInterviewStore, type ViewMode } from '@/stores/hr/interviews'
import type { Interview, CalendarViewMode } from '@/api/hr/interviews'
import InterviewCreateModal from '@/components/hr/InterviewCreateModal.vue'
import InterviewCalendar from '@/components/hr/InterviewCalendar.vue'
import InterviewBoard from '@/components/hr/InterviewBoard.vue'
import ErrorBoundary from '@/components/hr/ErrorBoundary.vue'
import TableSkeleton from '@/components/hr/TableSkeleton.vue'

type TagType = 'default' | 'info' | 'success' | 'warning' | 'error'

const router = useRouter()
const interviewStore = useInterviewStore()
const message = useMessage()
const showCreateModal = ref(false)
const sortBy = ref<string>('scheduled_at')
const sortOrder = ref<'ascend' | 'descend'>('descend')
const showWorkloadSidebar = ref(true)

// ─── Enhanced Filters ─────────────────────────────────────────────
const filterCandidate = ref<string>('')
const filterInterviewer = ref<string>('')
const filterDateRange = ref<[number, number] | null>(null)
const filterType = ref<string>('')

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '待确认', value: 'pending' },
  { label: '已安排', value: 'scheduled' },
  { label: '已确认', value: 'confirmed' },
  { label: '进行中', value: 'in_progress' },
  { label: '已完成', value: 'completed' },
  { label: '已取消', value: 'cancelled' },
]

const typeOptions = [
  { label: '全部类型', value: '' },
  { label: '电话筛选', value: 'phone_screen' },
  { label: '技术面试', value: 'technical' },
  { label: '行为面试', value: 'behavioral' },
  { label: 'HR面试', value: 'hr' },
  { label: '终面', value: 'final' },
  { label: '群面', value: 'panel' },
  { label: '案例面试', value: 'case_study' },
]

const sortOptions = [
  { label: '时间', value: 'scheduled_at' },
  { label: '评分', value: 'overall_score' },
  { label: '轮次', value: 'round_number' },
  { label: '创建时间', value: 'created_at' },
]

const statusColorMap: Record<string, TagType> = {
  scheduled: 'warning',
  confirmed: 'info',
  in_progress: 'success',
  completed: 'default',
  cancelled: 'error',
  no_show: 'error',
  pending: 'default',
}

const viewModeOptions: { key: ViewMode; label: string }[] = [
  { key: 'list', label: '列表' },
  { key: 'calendar', label: '日历' },
  { key: 'board', label: '看板' },
]

// ─── Stats ────────────────────────────────────────────────────────
const statsCards = computed(() => {
  const items = interviewStore.interviews
  const total = items.length
  const scheduled = items.filter(i => i.status === 'scheduled' || i.status === 'confirmed').length
  const inProgress = items.filter(i => i.status === 'in_progress').length
  const completed = items.filter(i => i.status === 'completed').length
  const noFeedback = items.filter(i => i.status === 'completed' && i.overall_score === null).length
  return [
    { label: '总计', value: total, color: '#333' },
    { label: '已排期', value: scheduled, color: '#f0a020' },
    { label: '进行中', value: inProgress, color: '#18a058' },
    { label: '已完成', value: completed, color: '#4a90d9' },
    { label: '待反馈', value: noFeedback, color: '#d03050' },
  ]
})

const interviewerStats = computed(() => {
  return interviewStore.interviewerWorkload
})

// ─── Table Columns ────────────────────────────────────────────────
const columns: DataTableColumns<Interview> = [
  {
    title: '候选人',
    key: 'candidate_id',
    width: 120,
    sorter: true,
    render: (row) => h('span', { style: 'font-weight:500' }, row.candidate_id),
  },
  {
    title: '岗位',
    key: 'position_id',
    width: 140,
    ellipsis: { tooltip: true },
  },
  {
    title: '轮次',
    key: 'round_number',
    width: 60,
    sorter: true,
    render: (row) => `第${row.round_number}轮`,
  },
  {
    title: '类型',
    key: 'interview_type',
    width: 100,
    render: (row) => {
      const labels: Record<string, string> = {
        phone_screen: '电话筛选', technical: '技术面试', behavioral: '行为面试',
        hr: 'HR面试', final: '终面', panel: '群面', case_study: '案例面试',
      }
      return h(NTag, { size: 'small', bordered: false }, () => labels[row.interview_type] || row.interview_type)
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    sorter: true,
    render: (row) => {
      const statusLabels: Record<string, string> = {
        scheduled: '已安排', confirmed: '已确认', in_progress: '进行中',
        completed: '已完成', cancelled: '已取消', pending: '待确认',
      }
      return h(NTag, { size: 'small', type: statusColorMap[row.status] ?? 'default' }, () => statusLabels[row.status] || row.status)
    },
  },
  {
    title: '时间',
    key: 'scheduled_at',
    width: 160,
    sorter: true,
    render: (row) => row.scheduled_at
      ? new Date(row.scheduled_at).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
      : '-',
  },
  {
    title: '时长',
    key: 'duration_minutes',
    width: 70,
    sorter: true,
    render: (row) => `${row.duration_minutes}分`,
  },
  {
    title: '评分',
    key: 'overall_score',
    width: 70,
    sorter: true,
    render: (row) => {
      if (row.overall_score === null) return h('span', { style: 'color:#999' }, '-')
      const color = row.overall_score >= 8 ? '#18a058' : row.overall_score >= 6 ? '#f0a020' : '#d03050'
      return h('span', { style: `font-weight:600;color:${color}` }, `${row.overall_score}/10`)
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render: (row) => h(NSpace, { size: 'small' }, () => [
      h(NButton, { size: 'tiny', onClick: () => handleView(row.id) }, () => '详情'),
      h(NButton, { size: 'tiny', type: 'error', onClick: () => handleCancel(row.id) }, () => '取消'),
    ]),
  },
]

// ─── Lifecycle ────────────────────────────────────────────────────
onMounted(() => {
  interviewStore.fetchInterviews()
  interviewStore.fetchWorkload()
})

// ─── Handlers ─────────────────────────────────────────────────────
function handleViewModeChange(mode: ViewMode) {
  interviewStore.setViewMode(mode)
  if (mode === 'calendar') {
    const d = interviewStore.calendarDate
    const start = new Date(d.getFullYear(), d.getMonth(), 1)
    const end = new Date(d.getFullYear(), d.getMonth() + 1, 0)
    interviewStore.fetchCalendarData({
      date_from: start.toISOString(),
      date_to: end.toISOString(),
    })
  } else {
    handleFilter()
  }
}

function buildFilterParams() {
  const params: Record<string, string | undefined> = {
    status: interviewStore.filterStatus || undefined,
    candidate_id: filterCandidate.value || undefined,
    interviewer_id: filterInterviewer.value || undefined,
    sort_by: sortBy.value,
    sort_order: sortOrder.value === 'descend' ? 'desc' : 'asc',
  }
  if (filterType.value) params.interview_type = filterType.value
  if (filterDateRange.value) {
    params.date_from = new Date(filterDateRange.value[0]).toISOString()
    params.date_to = new Date(filterDateRange.value[1]).toISOString()
  }
  return params
}

function handleFilter() {
  interviewStore.fetchInterviews(buildFilterParams())
}

function handleSortChange() {
  handleFilter()
}

function handleResetFilters() {
  filterCandidate.value = ''
  filterInterviewer.value = ''
  filterDateRange.value = null
  filterType.value = ''
  interviewStore.filterStatus = ''
  sortBy.value = 'scheduled_at'
  sortOrder.value = 'descend'
  interviewStore.fetchInterviews()
}

function handleView(id: string) {
  router.push({ name: 'hr.interviewDetail', params: { id } })
}

async function handleCancel(id: string) {
  try {
    await interviewStore.cancelInterview(id)
    message.success('面试已取消')
  } catch {
    message.error('取消失败')
  }
}

function handleCreateSaved() {
  interviewStore.fetchInterviews()
  showCreateModal.value = false
  message.success('面试已安排')
}

async function handleReschedule(interview: Interview, newDate: string) {
  try {
    await interviewStore.rescheduleInterview(interview.id, newDate)
    message.success('面试已重新排期')
  } catch {
    message.error('排期失败')
  }
}

function handleCalendarDateChange(date: Date) {
  interviewStore.setCalendarDate(date)
  const start = new Date(date.getFullYear(), date.getMonth(), 1)
  const end = new Date(date.getFullYear(), date.getMonth() + 1, 0)
  interviewStore.fetchCalendarData({
    date_from: start.toISOString(),
    date_to: end.toISOString(),
  })
}

function handleCalendarViewModeChange(_mode: CalendarViewMode) {
  // reserved for future mode switching
}

async function handleBoardStatusChange(interview: Interview, newStatus: string) {
  try {
    await interviewStore.changeStatus(interview.id, newStatus)
    message.success('状态已更新')
  } catch {
    message.error('更新失败')
  }
}

function toggleWorkloadSidebar() {
  showWorkloadSidebar.value = !showWorkloadSidebar.value
}
</script>

<template>
  <ErrorBoundary>
    <div class="interviews-view">
      <header class="page-header">
        <h2 class="header-title">面试管理</h2>
        <div class="header-actions">
          <NButtonGroup size="small">
            <NButton
              v-for="opt in viewModeOptions"
              :key="opt.key"
              :type="interviewStore.viewMode === opt.key ? 'primary' : 'default'"
              @click="handleViewModeChange(opt.key)"
            >
              {{ opt.label }}
            </NButton>
          </NButtonGroup>
          <NButton size="small" @click="toggleWorkloadSidebar">
            {{ showWorkloadSidebar ? '隐藏工作量' : '显示工作量' }}
          </NButton>
          <NButton type="primary" @click="showCreateModal = true">安排面试</NButton>
        </div>
      </header>

      <div class="main-layout" :class="{ 'sidebar-visible': showWorkloadSidebar }">
        <!-- Main Content -->
        <div class="main-content">
          <!-- Stats Panel -->
          <div class="stats-panel">
            <NGrid :cols="5" :x-gap="12" :y-gap="12">
              <NGi v-for="card in statsCards" :key="card.label">
                <NCard size="small" class="stat-card">
                  <NStatistic :label="card.label" :value="card.value" />
                </NCard>
              </NGi>
            </NGrid>
          </div>

          <!-- List View Filters -->
          <div v-if="interviewStore.viewMode === 'list'" class="filter-bar">
            <NSelect
              v-model:value="interviewStore.filterStatus"
              :options="statusOptions"
              style="width: 120px;"
              @update:value="handleFilter"
            />
            <NSelect
              v-model:value="filterType"
              :options="typeOptions"
              style="width: 130px;"
              @update:value="handleFilter"
            />
            <NInput
              v-model:value="filterCandidate"
              placeholder="候选人ID"
              clearable
              size="small"
              style="width: 140px;"
              @clear="handleFilter"
              @keyup.enter="handleFilter"
            />
            <NInput
              v-model:value="filterInterviewer"
              placeholder="面试官ID"
              clearable
              size="small"
              style="width: 140px;"
              @clear="handleFilter"
              @keyup.enter="handleFilter"
            />
            <NDatePicker
              v-model:value="filterDateRange"
              type="daterange"
              clearable
              size="small"
              style="width: 240px;"
              @update:value="handleFilter"
            />
            <NSelect
              v-model:value="sortBy"
              :options="sortOptions"
              style="width: 110px;"
              @update:value="handleSortChange"
            />
            <NButton size="small" quaternary @click="handleResetFilters">
              重置
            </NButton>
          </div>

          <!-- Loading Skeleton -->
          <TableSkeleton v-if="interviewStore.loading" :rows="6" :columns="8" />

          <!-- Views -->
          <template v-else>
            <!-- Calendar View -->
            <InterviewCalendar
              v-if="interviewStore.viewMode === 'calendar'"
              :interviews="interviewStore.calendarInterviews"
              :current-date="interviewStore.calendarDate"
              :loading="interviewStore.loading"
              @view-detail="handleView"
              @reschedule="handleReschedule"
              @date-change="handleCalendarDateChange"
              @view-mode-change="handleCalendarViewModeChange"
              @date-click="() => { showCreateModal = true }"
            />

            <!-- Board View -->
            <InterviewBoard
              v-else-if="interviewStore.viewMode === 'board'"
              :interviews="interviewStore.interviews"
              :loading="interviewStore.loading"
              @view-detail="handleView"
              @change-status="handleBoardStatusChange"
            />

            <!-- List View (DataTable) -->
            <NDataTable
              v-else
              :columns="columns"
              :data="interviewStore.interviews"
              :row-key="(row: Interview) => row.id"
              :pagination="{ pageSize: 20 }"
              :scroll-x="1000"
              striped
            />
          </template>
        </div>

        <!-- Workload Sidebar -->
        <aside v-if="showWorkloadSidebar" class="workload-sidebar">
          <NCollapse :default-expanded-names="['workload']">
            <NCollapseItem title="面试官工作量" name="workload">
              <template v-if="interviewerStats.length">
                <div class="workload-list">
                  <NCard
                    v-for="iw in interviewerStats"
                    :key="iw.interviewer_id"
                    size="small"
                    class="workload-card"
                  >
                    <div class="workload-header">
                      <span class="workload-name">{{ iw.interviewer_id.slice(0, 8) }}…</span>
                    </div>
                    <div class="workload-stats">
                      <span class="workload-item">
                        <span class="wl-label">场次</span>
                        <span class="wl-value">{{ iw.total_interviews }}</span>
                      </span>
                      <span class="workload-item">
                        <span class="wl-label">待反馈</span>
                        <span class="wl-value pending">{{ iw.pending_feedback }}</span>
                      </span>
                      <span class="workload-item">
                        <span class="wl-label">均分</span>
                        <span class="wl-value">{{ iw.avg_score !== null ? iw.avg_score.toFixed(1) : '-' }}</span>
                      </span>
                    </div>
                  </NCard>
                </div>
              </template>
              <div v-else class="workload-empty">暂无数据</div>
            </NCollapseItem>
          </NCollapse>
        </aside>
      </div>

      <InterviewCreateModal
        :show="showCreateModal"
        @close="showCreateModal = false"
        @saved="handleCreateSaved"
      />
    </div>
  </ErrorBoundary>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.interviews-view {
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;

  @media (max-width: $breakpoint-mobile) {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .header-title {
    font-size: 22px;
    font-weight: 600;
    color: $text-primary;
    margin: 0;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }
}

.main-layout {
  display: flex;
  gap: 20px;

  .main-content {
    flex: 1;
    min-width: 0;
  }

  .workload-sidebar {
    width: 280px;
    flex-shrink: 0;

    @media (max-width: $breakpoint-mobile) {
      display: none;
    }
  }
}

.stats-panel {
  margin-bottom: 20px;

  .stat-card {
    text-align: center;

    :deep(.n-statistic .n-statistic-value) {
      font-size: 28px;
    }
  }
}

.filter-bar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.workload-sidebar {
  .workload-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .workload-card {
    .workload-header {
      margin-bottom: 6px;

      .workload-name {
        font-weight: 600;
        font-size: 12px;
        color: $text-primary;
      }
    }

    .workload-stats {
      display: flex;
      gap: 12px;

      .workload-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;

        .wl-label {
          font-size: 10px;
          color: $text-muted;
        }

        .wl-value {
          font-size: 14px;
          font-weight: 600;
          color: $text-primary;

          &.pending {
            color: var(--warning);
          }
        }
      }
    }
  }

  .workload-empty {
    text-align: center;
    padding: 16px;
    color: $text-muted;
    font-size: 13px;
  }
}

@media (max-width: $breakpoint-mobile) {
  .stats-panel {
    :deep(.n-grid) {
      grid-template-columns: repeat(2, 1fr) !important;
    }
  }

  .filter-bar {
    flex-direction: column;
    align-items: stretch;

    .n-select, .n-input, .n-date-picker {
      width: 100% !important;
    }
  }
}
</style>
