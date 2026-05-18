<script setup lang="ts">
import { ref, onMounted, computed, h } from 'vue'
import {
  NButton,
  NDataTable,
  NTag,
  NSpace,
  NModal,
  NCard,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NDescriptions,
  NDescriptionsItem,
  NProgress,
  NDatePicker,
  NTabs,
  NTabPane,
  NEmpty,
  NPopconfirm,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns, FormInst } from 'naive-ui'
import * as scheduledTasksApi from '@/api/hr/scheduled-tasks'
import type { ScheduledTask, TaskResult } from '@/api/hr/scheduled-tasks'
import ErrorBoundary from '@/components/hr/ErrorBoundary.vue'
import TableSkeleton from '@/components/hr/TableSkeleton.vue'

type TagType = 'default' | 'info' | 'success' | 'warning' | 'error'

const message = useMessage()
const tasks = ref<ScheduledTask[]>([])
const loading = ref(false)
const showCreateModal = ref(false)
const showResultModal = ref(false)
const selectedTask = ref<ScheduledTask | null>(null)
const taskResult = ref<TaskResult | null>(null)
const resultLoading = ref(false)
const formRef = ref<FormInst | null>(null)
const activeTab = ref<'scheduled' | 'one_time'>('scheduled')

// ── Color maps ─────────────────────────────────────────────
const statusColorMap: Record<string, TagType> = {
  active: 'success',
  paused: 'warning',
  completed: 'info',
  failed: 'error',
}

const typeLabelMap: Record<string, string> = {
  scheduled: '定时任务',
  one_time: '一次性任务',
}

const typeIconMap: Record<string, string> = {
  daily_report: '📊',
  weekly_report: '📈',
  insight_scan: '🔍',
  report_generation: '📄',
  data_export: '💾',
  batch_scoring: '⚡',
  candidate_matching: '🎯',
  resume_parsing: '📋',
}

// ── Filter state ───────────────────────────────────────────
const filterStatus = ref('')
const statusOptions = [
  { label: '全部', value: '' },
  { label: '运行中', value: 'active' },
  { label: '已暂停', value: 'paused' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' },
]

const skillOptions = [
  { label: '日报生成', value: 'daily_report' },
  { label: '周报生成', value: 'weekly_report' },
  { label: '洞察扫描', value: 'insight_scan' },
  { label: '报表生成', value: 'report_generation' },
  { label: '数据导出', value: 'data_export' },
  { label: '批量评分', value: 'batch_scoring' },
  { label: '候选人匹配', value: 'candidate_matching' },
  { label: '简历解析', value: 'resume_parsing' },
]

const typeOptions = [
  { label: '定时任务', value: 'scheduled' },
  { label: '一次性任务', value: 'one_time' },
]

// ── Form state ─────────────────────────────────────────────
const formData = ref({
  name: '',
  type: 'one_time' as 'scheduled' | 'one_time',
  skill_name: '',
  schedule: '',
  run_at: null as number | null,
})

// ── Computed ───────────────────────────────────────────────
const filteredTasks = computed(() => {
  return tasks.value.filter((t) => {
    if (activeTab.value === 'scheduled' && t.type !== 'scheduled') return false
    if (activeTab.value === 'one_time' && t.type !== 'one_time') return false
    if (filterStatus.value && t.status !== filterStatus.value) return false
    return true
  })
})

// ── Table columns ──────────────────────────────────────────
const columns: DataTableColumns<ScheduledTask> = [
  {
    title: '任务名称',
    key: 'name',
    width: 180,
    ellipsis: { tooltip: true },
    render: (row) =>
      h('span', {}, [
        h('span', { style: 'margin-right: 6px' }, typeIconMap[row.skill_name] ?? '🤖'),
        row.name,
      ]),
  },
  {
    title: 'Skill',
    key: 'skill_name',
    width: 130,
    ellipsis: { tooltip: true },
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row) =>
      h(
        NTag,
        { size: 'small', type: statusColorMap[row.status] ?? 'default' },
        () => row.status,
      ),
  },
  {
    title: '进度',
    key: 'progress',
    width: 120,
    render: (row) => {
      if (row.status === 'completed') return h(NProgress, { type: 'line', percentage: 100, status: 'success', indicatorPlacement: 'inside' })
      if (row.status === 'failed') return h(NProgress, { type: 'line', percentage: 100, status: 'error', indicatorPlacement: 'inside' })
      if (row.status === 'active') return h(NProgress, { type: 'line', percentage: 60, status: 'info', indicatorPlacement: 'inside' })
      return h(NProgress, { type: 'line', percentage: 0, indicatorPlacement: 'inside' })
    },
  },
  { title: 'Schedule', key: 'schedule', width: 120, render: (row) => row.schedule ?? '-' },
  {
    title: '创建时间',
    key: 'created_at',
    width: 160,
    render: (row) => row.created_at ?? '-',
  },
  {
    title: '操作',
    key: 'actions',
    width: 240,
    render: (row) =>
      h(NSpace, { size: 'small' }, () => {
        const btns = [
          h(NButton, { size: 'tiny', onClick: () => handleViewResult(row) }, () => '结果'),
        ]
        if (row.status === 'active') {
          btns.push(
            h(
              NButton,
              { size: 'tiny', type: 'warning', onClick: () => handlePause(row.id) },
              () => '暂停',
            ),
          )
        }
        if (row.status === 'paused') {
          btns.push(
            h(
              NButton,
              { size: 'tiny', type: 'success', onClick: () => handleResume(row.id) },
              () => '恢复',
            ),
          )
        }
        if (row.status === 'active' || row.status === 'paused') {
          btns.push(
            h(
              NPopconfirm,
              { onPositiveClick: () => handleCancel(row.id) },
              {
                trigger: () =>
                  h(NButton, { size: 'tiny', type: 'error' }, () => '取消'),
                default: () => '确认取消该任务？',
              },
            ),
          )
        }
        return btns
      }),
  },
]

// ── Lifecycle ──────────────────────────────────────────────
onMounted(async () => {
  await fetchTasks()
})

// ── Data fetching ──────────────────────────────────────────
async function fetchTasks() {
  loading.value = true
  try {
    const res = await scheduledTasksApi.listScheduledTasks({
      status: filterStatus.value || undefined,
    } as Record<string, string | number>)
    tasks.value = res.items
  } catch {
    message.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

// ── Handlers ───────────────────────────────────────────────
async function handleViewResult(task: ScheduledTask) {
  selectedTask.value = task
  if (task.last_result) {
    taskResult.value = task.last_result
    showResultModal.value = true
    return
  }
  resultLoading.value = true
  showResultModal.value = true
  try {
    taskResult.value = await scheduledTasksApi.getTaskResult(task.id)
  } catch {
    message.error('获取任务结果失败')
    taskResult.value = null
  } finally {
    resultLoading.value = false
  }
}

async function handlePause(id: string) {
  try {
    await scheduledTasksApi.pauseScheduledTask(id)
    message.success('已暂停')
    await fetchTasks()
  } catch {
    message.error('暂停失败')
  }
}

async function handleResume(id: string) {
  try {
    await scheduledTasksApi.resumeScheduledTask(id)
    message.success('已恢复')
    await fetchTasks()
  } catch {
    message.error('恢复失败')
  }
}

async function handleCancel(id: string) {
  try {
    await scheduledTasksApi.cancelScheduledTask(id)
    message.success('已取消')
    await fetchTasks()
  } catch {
    message.error('取消失败')
  }
}

function handleCreate() {
  formData.value = {
    name: '',
    type: activeTab.value === 'scheduled' ? 'scheduled' : 'one_time',
    skill_name: '',
    schedule: '',
    run_at: null,
  }
  showCreateModal.value = true
}

async function handleSave() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  try {
    const payload: Record<string, unknown> = {
      name: formData.value.name,
      type: formData.value.type,
      skill_name: formData.value.skill_name,
    }
    if (formData.value.type === 'scheduled' && formData.value.schedule) {
      payload.schedule = formData.value.schedule
    }
    if (formData.value.type === 'one_time' && formData.value.run_at) {
      payload.run_at = new Date(formData.value.run_at).toISOString()
    }
    await scheduledTasksApi.createScheduledTask(payload as any)
    message.success('任务已创建')
    showCreateModal.value = false
    await fetchTasks()
  } catch {
    message.error('创建失败')
  }
}

function handleTabChange(tab: string) {
  activeTab.value = tab as 'scheduled' | 'one_time'
}

async function handleRefreshAll() {
  await fetchTasks()
  message.success('已刷新')
}
</script>

<template>
  <ErrorBoundary>
    <div class="ai-task-center-view">
      <header class="page-header">
        <h2 class="header-title">AI 任务中心</h2>
        <NSpace>
          <NButton @click="handleRefreshAll">刷新</NButton>
          <NButton type="primary" @click="handleCreate">创建任务</NButton>
        </NSpace>
      </header>

      <!-- Tabs -->
      <NTabs v-model:value="activeTab" type="line" @update:value="handleTabChange" style="margin-bottom: 16px">
        <NTabPane name="scheduled" tab="定时任务">
          <template #tab>
            <span>⏰ 定时任务</span>
          </template>
        </NTabPane>
        <NTabPane name="one_time" tab="一次性任务">
          <template #tab>
            <span>🚀 一次性任务</span>
          </template>
        </NTabPane>
      </NTabs>

      <!-- Filter -->
      <div class="filter-bar">
        <NSelect
          v-model:value="filterStatus"
          :options="statusOptions"
          style="width: 130px"
          @update:value="fetchTasks"
        />
      </div>

      <!-- Table -->
      <TableSkeleton v-if="loading" :rows="6" :columns="7" />
      <NDataTable
        v-else
        :columns="columns"
        :data="filteredTasks"
        :row-key="(row: ScheduledTask) => row.id"
        :pagination="{ pageSize: 20 }"
        :scroll-x="1100"
        striped
      />

      <!-- Create Modal -->
      <NModal
        v-model:show="showCreateModal"
        preset="card"
        title="创建 AI 任务"
        style="max-width: 520px"
      >
        <NForm ref="formRef" :model="formData" label-placement="left" label-width="90">
          <NFormItem
            label="任务名称"
            path="name"
            :rule="{ required: true, message: '请输入任务名称' }"
          >
            <NInput v-model:value="formData.name" placeholder="输入任务名称" />
          </NFormItem>
          <NFormItem
            label="任务类型"
            path="type"
            :rule="{ required: true, message: '请选择任务类型' }"
          >
            <NSelect
              v-model:value="formData.type"
              :options="typeOptions"
            />
          </NFormItem>
          <NFormItem
            label="Skill"
            path="skill_name"
            :rule="{ required: true, message: '请选择 Skill' }"
          >
            <NSelect
              v-model:value="formData.skill_name"
              :options="skillOptions"
              filterable
              tag
              placeholder="选择或输入 Skill"
            />
          </NFormItem>
          <NFormItem v-if="formData.type === 'scheduled'" label="Cron 表达式" path="schedule">
            <NInput v-model:value="formData.schedule" placeholder="如: 0 8 * * *" />
          </NFormItem>
          <NFormItem v-if="formData.type === 'one_time'" label="执行时间">
            <NDatePicker
              v-model:value="formData.run_at"
              type="datetime"
              clearable
              style="width: 100%"
            />
          </NFormItem>
        </NForm>
        <template #footer>
          <NSpace justify="end">
            <NButton @click="showCreateModal = false">取消</NButton>
            <NButton type="primary" @click="handleSave">创建</NButton>
          </NSpace>
        </template>
      </NModal>

      <!-- Result Modal -->
      <NModal
        v-model:show="showResultModal"
        preset="card"
        :title="`任务结果 — ${selectedTask?.name ?? ''}`"
        style="max-width: 620px"
      >
        <template v-if="resultLoading">
          <div class="loading-hint">加载中...</div>
        </template>
        <template v-else-if="taskResult">
          <NDescriptions bordered :column="1" label-placement="left" size="small">
            <NDescriptionsItem label="状态">
              <NTag
                size="small"
                :type="
                  taskResult.status === 'completed'
                    ? 'success'
                    : taskResult.status === 'failed'
                      ? 'error'
                      : 'warning'
                "
              >
                {{ taskResult.status }}
              </NTag>
            </NDescriptionsItem>
            <NDescriptionsItem label="开始时间">
              {{ taskResult.started_at }}
            </NDescriptionsItem>
            <NDescriptionsItem label="完成时间">
              {{ taskResult.completed_at ?? '-' }}
            </NDescriptionsItem>
            <NDescriptionsItem label="耗时">
              {{
                taskResult.duration_ms != null
                  ? `${(taskResult.duration_ms / 1000).toFixed(1)}s`
                  : '-'
              }}
            </NDescriptionsItem>
            <NDescriptionsItem v-if="taskResult.error" label="错误信息">
              <span class="error-text">{{ taskResult.error }}</span>
            </NDescriptionsItem>
            <NDescriptionsItem v-if="taskResult.output" label="输出结果">
              <pre class="result-output">{{
                typeof taskResult.output === 'string'
                  ? taskResult.output
                  : JSON.stringify(taskResult.output, null, 2)
              }}</pre>
            </NDescriptionsItem>
          </NDescriptions>
        </template>
        <template v-else>
          <NEmpty description="暂无执行结果" />
        </template>
      </NModal>
    </div>
  </ErrorBoundary>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.ai-task-center-view {
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
}

.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.loading-hint {
  text-align: center;
  padding: 20px;
  color: $text-muted;
}

.error-text {
  color: var(--error);
  font-family: $font-code;
  font-size: 13px;
}

.result-output {
  background: var(--code-bg);
  padding: 12px;
  border-radius: $radius-sm;
  font-family: $font-code;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  max-height: 300px;
  overflow-y: auto;
  color: $text-primary;
}
</style>
