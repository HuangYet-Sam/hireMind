<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NButton, NDataTable, NTag, NSpace, NProgress, NSpin } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import * as tasksApi from '@/api/hr/tasks'
import type { AiTask } from '@/api/hr/tasks'

const tasks = ref<AiTask[]>([])
const loading = ref(false)

const statusColorMap: Record<string, string> = {
  queued: 'default',
  running: 'warning',
  completed: 'success',
  failed: 'error',
  cancelled: 'default',
}

const typeLabelMap: Record<string, string> = {
  resume_parsing: '简历解析',
  candidate_matching: '候选人匹配',
  batch_scoring: '批量评分',
  report_generation: '报告生成',
  candidate_summary: '候选人摘要',
}

const columns: DataTableColumns<AiTask> = [
  { title: '类型', key: 'type', width: 120, render: (row) => typeLabelMap[row.type] || row.type },
  { title: '输入摘要', key: 'input_summary', ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => h(NTag, { size: 'small', type: statusColorMap[row.status] as any }, () => row.status),
  },
  {
    title: '进度',
    key: 'progress',
    width: 150,
    render: (row) => h(NProgress, {
      type: 'line',
      percentage: row.progress,
      status: row.status === 'failed' ? 'error' : row.status === 'completed' ? 'success' : 'default',
    }),
  },
  { title: '创建时间', key: 'created_at', width: 120 },
  { title: '完成时间', key: 'completed_at', width: 120 },
  {
    title: '操作',
    key: 'actions',
    width: 140,
    render: (row) => h(NSpace, { size: 'small' }, () => {
      const btns = [h(NButton, { size: 'tiny', onClick: () => handleView(row.id) }, () => '详情')]
      if (row.status === 'failed') {
        btns.push(h(NButton, { size: 'tiny', type: 'warning', onClick: () => handleRetry(row.id) }, () => '重试'))
      }
      if (row.status === 'running' || row.status === 'queued') {
        btns.push(h(NButton, { size: 'tiny', type: 'error', onClick: () => handleCancel(row.id) }, () => '取消'))
      }
      return btns
    }),
  },
]

onMounted(async () => {
  await fetchTasks()
})

async function fetchTasks() {
  loading.value = true
  try {
    const res = await tasksApi.listAiTasks()
    tasks.value = res.items
  } catch (err) {
    console.error('Failed to fetch AI tasks:', err)
  } finally {
    loading.value = false
  }
}

function handleView(id: string) {
  console.log('View task:', id)
}

async function handleRetry(id: string) {
  await tasksApi.retryAiTask(id)
  await fetchTasks()
}

async function handleCancel(id: string) {
  await tasksApi.cancelAiTask(id)
  await fetchTasks()
}
</script>

<template>
  <div class="tasks-view">
    <header class="page-header">
      <h2 class="header-title">AI任务中心</h2>
      <NButton @click="fetchTasks">刷新</NButton>
    </header>

    <NSpin :show="loading">
      <NDataTable
        :columns="columns"
        :data="tasks"
        :row-key="(row: AiTask) => row.id"
        :pagination="{ pageSize: 20 }"
        striped
      />
    </NSpin>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.tasks-view {
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;

  .header-title {
    font-size: 22px;
    font-weight: 600;
    color: $text-primary;
    margin: 0;
  }
}
</style>
