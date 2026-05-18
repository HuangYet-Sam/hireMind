<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import {
  NButton,
  NDataTable,
  NTag,
  NSpace,
  NSwitch,
  NModal,
  NCard,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NSelect,
  NDescriptions,
  NDescriptionsItem,
  NDrawer,
  NDrawerContent,
  NPopconfirm,
  NEmpty,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns, FormInst } from 'naive-ui'
import * as cronApi from '@/api/hr/cron'
import type { CronJob, CronRun } from '@/api/hr/cron'
import ErrorBoundary from '@/components/hr/ErrorBoundary.vue'
import TableSkeleton from '@/components/hr/TableSkeleton.vue'

type TagType = 'default' | 'info' | 'success' | 'warning' | 'error'

const message = useMessage()
const jobs = ref<CronJob[]>([])
const runs = ref<CronRun[]>([])
const loading = ref(false)
const runsLoading = ref(false)
const showCreateModal = ref(false)
const showHistoryDrawer = ref(false)
const showDetailModal = ref(false)
const selectedJob = ref<CronJob | null>(null)
const detailRun = ref<CronRun | null>(null)
const formRef = ref<FormInst | null>(null)
const editingJob = ref<CronJob | null>(null)

// ── Status color map ───────────────────────────────────────
const statusColorMap: Record<string, TagType> = {
  success: 'success',
  failed: 'error',
  running: 'info',
  pending: 'default',
  timeout: 'warning',
}

const statusLabelMap: Record<string, string> = {
  success: '成功',
  failed: '失败',
  running: '运行中',
  pending: '等待中',
  timeout: '超时',
}

// ── Schedule presets ───────────────────────────────────────
const scheduleOptions = [
  { label: '每分钟', value: '* * * * *' },
  { label: '每小时', value: '0 * * * *' },
  { label: '每天 00:00', value: '0 0 * * *' },
  { label: '每天 08:00', value: '0 8 * * *' },
  { label: '每天 18:00', value: '0 18 * * *' },
  { label: '每周一 09:00', value: '0 9 * * 1' },
  { label: '每月1号 00:00', value: '0 0 1 * *' },
]

const jobTypeOptions = [
  { label: '日报生成', value: 'daily_report' },
  { label: '周报生成', value: 'weekly_report' },
  { label: '洞察扫描', value: 'insight_scan' },
  { label: '数据同步', value: 'data_sync' },
  { label: '自定义', value: 'custom' },
]

// ── Form state ─────────────────────────────────────────────
const formData = ref({
  name: '',
  description: '',
  schedule: '0 8 * * *',
  skill_name: '',
  job_type: 'custom',
  enabled: true,
  max_retries: 3,
  timeout_seconds: 300,
})

// ── Table columns ──────────────────────────────────────────
const jobColumns: DataTableColumns<CronJob> = [
  {
    title: '任务名称',
    key: 'name',
    width: 160,
    ellipsis: { tooltip: true },
  },
  {
    title: 'Skill',
    key: 'skill_name',
    width: 140,
    ellipsis: { tooltip: true },
  },
  {
    title: 'Cron 表达式',
    key: 'schedule',
    width: 130,
  },
  {
    title: '状态',
    key: 'enabled',
    width: 80,
    render: (row) =>
      h(NSwitch, {
        size: 'small',
        value: row.enabled,
        onUpdateValue: (val: boolean) => handleToggle(row.id, val),
      }),
  },
  {
    title: '上次状态',
    key: 'last_run_status',
    width: 100,
    render: (row) =>
      row.last_run_status
        ? h(
            NTag,
            { size: 'small', type: statusColorMap[row.last_run_status] ?? 'default' },
            () => statusLabelMap[row.last_run_status!] ?? row.last_run_status!,
          )
        : h('span', { style: 'color: var(--text-muted)' }, '-'),
  },
  {
    title: '上次执行',
    key: 'last_run_at',
    width: 160,
    render: (row) => row.last_run_at ?? '-',
  },
  {
    title: '下次执行',
    key: 'next_run_at',
    width: 160,
    render: (row) => row.next_run_at ?? '-',
  },
  {
    title: '操作',
    key: 'actions',
    width: 240,
    render: (row) =>
      h(NSpace, { size: 'small' }, () => [
        h(
          NButton,
          { size: 'tiny', type: 'primary', onClick: () => handleTrigger(row.id) },
          () => '执行',
        ),
        h(
          NButton,
          { size: 'tiny', onClick: () => handleViewHistory(row) },
          () => '历史',
        ),
        h(NButton, { size: 'tiny', onClick: () => handleEdit(row) }, () => '编辑'),
        h(
          NPopconfirm,
          { onPositiveClick: () => handleDelete(row.id) },
          {
            trigger: () =>
              h(NButton, { size: 'tiny', type: 'error' }, () => '删除'),
            default: () => '确认删除该 Cron 任务？',
          },
        ),
      ]),
  },
]

// ── Run columns (history drawer) ───────────────────────────
const runColumns: DataTableColumns<CronRun> = [
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row) =>
      h(
        NTag,
        { size: 'small', type: statusColorMap[row.status] ?? 'default' },
        () => statusLabelMap[row.status] ?? row.status,
      ),
  },
  { title: '开始时间', key: 'started_at', width: 160 },
  {
    title: '完成时间',
    key: 'completed_at',
    width: 160,
    render: (row) => row.completed_at ?? '-',
  },
  {
    title: '耗时',
    key: 'duration_ms',
    width: 100,
    render: (row) =>
      row.duration_ms != null ? `${(row.duration_ms / 1000).toFixed(1)}s` : '-',
  },
  {
    title: '结果摘要',
    key: 'result_summary',
    ellipsis: { tooltip: true },
    render: (row) => row.result_summary ?? '-',
  },
  {
    title: '操作',
    key: 'actions',
    width: 60,
    render: (row) =>
      h(
        NButton,
        { size: 'tiny', onClick: () => handleViewRunDetail(row) },
        () => '详情',
      ),
  },
]

// ── Lifecycle ──────────────────────────────────────────────
onMounted(async () => {
  await fetchJobs()
})

// ── Data fetching ──────────────────────────────────────────
async function fetchJobs() {
  loading.value = true
  try {
    const res = await cronApi.listCronJobs()
    jobs.value = res.items
  } catch {
    message.error('获取 Cron 任务列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchRuns(jobId: string) {
  runsLoading.value = true
  try {
    const res = await cronApi.listCronRuns({ job_id: jobId })
    runs.value = res.items
  } catch {
    message.error('获取执行历史失败')
  } finally {
    runsLoading.value = false
  }
}

// ── Handlers ───────────────────────────────────────────────
async function handleToggle(id: string, enabled: boolean) {
  try {
    await cronApi.toggleCronJob(id, enabled)
    message.success(enabled ? '已启用' : '已暂停')
    await fetchJobs()
  } catch {
    message.error('操作失败')
  }
}

async function handleTrigger(id: string) {
  try {
    await cronApi.triggerCronJob(id)
    message.success('已触发执行')
    await fetchJobs()
  } catch {
    message.error('触发失败')
  }
}

function handleViewHistory(job: CronJob) {
  selectedJob.value = job
  showHistoryDrawer.value = true
  fetchRuns(job.id)
}

function handleViewRunDetail(run: CronRun) {
  detailRun.value = run
  showDetailModal.value = true
}

function handleCreate() {
  editingJob.value = null
  formData.value = {
    name: '',
    description: '',
    schedule: '0 8 * * *',
    skill_name: '',
    job_type: 'custom',
    enabled: true,
    max_retries: 3,
    timeout_seconds: 300,
  }
  showCreateModal.value = true
}

function handleEdit(job: CronJob) {
  editingJob.value = job
  formData.value = {
    name: job.name,
    description: job.description,
    schedule: job.schedule,
    skill_name: job.skill_name,
    job_type: 'custom',
    enabled: job.enabled,
    max_retries: 3,
    timeout_seconds: 300,
  }
  showCreateModal.value = true
}

async function handleDelete(id: string) {
  try {
    await cronApi.deleteCronJob(id)
    message.success('已删除')
    await fetchJobs()
  } catch {
    message.error('删除失败')
  }
}

async function handleSave() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  try {
    if (editingJob.value) {
      await cronApi.updateCronJob(editingJob.value.id, formData.value)
      message.success('更新成功')
    } else {
      await cronApi.createCronJob(formData.value)
      message.success('创建成功')
    }
    showCreateModal.value = false
    await fetchJobs()
  } catch {
    message.error(editingJob.value ? '更新失败' : '创建失败')
  }
}

function handleModalClose() {
  showCreateModal.value = false
  editingJob.value = null
}

function handleDrawerClose() {
  showHistoryDrawer.value = false
  selectedJob.value = null
  runs.value = []
}
</script>

<template>
  <ErrorBoundary>
    <div class="cron-manager-view">
      <header class="page-header">
        <h2 class="header-title">Cron 任务管理</h2>
        <NSpace>
          <NButton @click="fetchJobs">刷新</NButton>
          <NButton type="primary" @click="handleCreate">新建 Cron 任务</NButton>
        </NSpace>
      </header>

      <TableSkeleton v-if="loading" :rows="6" :columns="7" />
      <NDataTable
        v-else
        :columns="jobColumns"
        :data="jobs"
        :row-key="(row: CronJob) => row.id"
        :pagination="{ pageSize: 20 }"
        :scroll-x="1200"
        striped
      />

      <!-- Create / Edit Modal -->
      <NModal
        v-model:show="showCreateModal"
        preset="card"
        :title="editingJob ? '编辑 Cron 任务' : '新建 Cron 任务'"
        style="max-width: 560px"
      >
        <NForm ref="formRef" :model="formData" label-placement="left" label-width="100">
          <NFormItem
            label="任务名称"
            path="name"
            :rule="{ required: true, message: '请输入任务名称' }"
          >
            <NInput v-model:value="formData.name" placeholder="输入任务名称" />
          </NFormItem>
          <NFormItem label="任务类型" path="job_type">
            <NSelect
              v-model:value="formData.job_type"
              :options="jobTypeOptions"
              placeholder="选择任务类型"
            />
          </NFormItem>
          <NFormItem label="描述" path="description">
            <NInput
              v-model:value="formData.description"
              type="textarea"
              :rows="2"
              placeholder="可选描述"
            />
          </NFormItem>
          <NFormItem
            label="Cron 表达式"
            path="schedule"
            :rule="{ required: true, message: '请选择或输入 Cron 表达式' }"
          >
            <NSelect
              v-model:value="formData.schedule"
              :options="scheduleOptions"
              filterable
              tag
            />
          </NFormItem>
          <NFormItem
            label="Skill 名称"
            path="skill_name"
            :rule="{ required: true, message: '请输入 Skill 名称' }"
          >
            <NInput v-model:value="formData.skill_name" placeholder="要调用的 Skill" />
          </NFormItem>
          <NFormItem label="重试次数" path="max_retries">
            <NInputNumber
              v-model:value="formData.max_retries"
              :min="0"
              :max="10"
              style="width: 100%"
            />
          </NFormItem>
          <NFormItem label="超时(秒)" path="timeout_seconds">
            <NInputNumber
              v-model:value="formData.timeout_seconds"
              :min="10"
              :max="3600"
              style="width: 100%"
            />
          </NFormItem>
          <NFormItem label="启用">
            <NSwitch v-model:value="formData.enabled" />
          </NFormItem>
        </NForm>
        <template #footer>
          <NSpace justify="end">
            <NButton @click="handleModalClose">取消</NButton>
            <NButton type="primary" @click="handleSave">
              {{ editingJob ? '更新' : '创建' }}
            </NButton>
          </NSpace>
        </template>
      </NModal>

      <!-- Execution History Drawer -->
      <NDrawer
        :show="showHistoryDrawer"
        :width="720"
        placement="right"
        :mask-closable="true"
        @update:show="(val: boolean) => { if (!val) handleDrawerClose() }"
      >
        <NDrawerContent :title="`执行历史 — ${selectedJob?.name ?? ''}`">
          <template v-if="runsLoading">
            <TableSkeleton :rows="5" :columns="5" />
          </template>
          <template v-else-if="runs.length > 0">
            <NDataTable
              :columns="runColumns"
              :data="runs"
              :row-key="(row: CronRun) => row.id"
              :pagination="{ pageSize: 10 }"
              :scroll-x="850"
              striped
              size="small"
            />
          </template>
          <template v-else>
            <NEmpty description="暂无执行记录" />
          </template>
        </NDrawerContent>
      </NDrawer>

      <!-- Run Detail Modal -->
      <NModal
        v-model:show="showDetailModal"
        preset="card"
        title="执行详情"
        style="max-width: 620px"
      >
        <template v-if="detailRun">
          <NDescriptions bordered :column="1" label-placement="left" size="small">
            <NDescriptionsItem label="执行 ID">{{ detailRun.id }}</NDescriptionsItem>
            <NDescriptionsItem label="状态">
              <NTag
                size="small"
                :type="statusColorMap[detailRun.status] ?? 'default'"
              >
                {{ statusLabelMap[detailRun.status] ?? detailRun.status }}
              </NTag>
            </NDescriptionsItem>
            <NDescriptionsItem label="开始时间">
              {{ detailRun.started_at }}
            </NDescriptionsItem>
            <NDescriptionsItem label="完成时间">
              {{ detailRun.completed_at ?? '-' }}
            </NDescriptionsItem>
            <NDescriptionsItem label="耗时">
              {{
                detailRun.duration_ms != null
                  ? `${(detailRun.duration_ms / 1000).toFixed(1)}s`
                  : '-'
              }}
            </NDescriptionsItem>
            <NDescriptionsItem v-if="detailRun.result_summary" label="结果摘要">
              {{ detailRun.result_summary }}
            </NDescriptionsItem>
            <NDescriptionsItem v-if="detailRun.error" label="错误信息">
              <span class="error-text">{{ detailRun.error }}</span>
            </NDescriptionsItem>
          </NDescriptions>
        </template>
      </NModal>
    </div>
  </ErrorBoundary>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.cron-manager-view {
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

.error-text {
  color: var(--error);
  font-family: $font-code;
  font-size: 13px;
}
</style>
