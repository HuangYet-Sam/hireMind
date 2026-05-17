<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NButton, NDataTable, NTag, NSpace, NProgress, NSpin, NModal, NCard, NDescriptions, NDescriptionsItem, useMessage } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import * as tasksApi from '@/api/hr/tasks'
import type { AiTask } from '@/api/hr/tasks'

type TagType = 'default' | 'info' | 'success' | 'warning' | 'error'

const tasks = ref<AiTask[]>([])
const loading = ref(false)
const detailTask = ref<AiTask | null>(null)
const showDetail = ref(false)
const message = useMessage()

const statusColorMap: Record<string, TagType> = {
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
    render: (row) => h(NTag, { size: 'small', type: statusColorMap[row.status] ?? 'default' }, () => row.status),
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
  } catch {
    message.error('获取 AI 任务列表失败')
  } finally {
    loading.value = false
  }
}

async function handleView(id: string) {
  try {
    detailTask.value = await tasksApi.getAiTask(id)
    showDetail.value = true
  } catch {
    message.error('获取任务详情失败')
  }
}

async function handleRetry(id: string) {
  try {
    await tasksApi.retryAiTask(id)
    message.success('任务已重新开始')
    await fetchTasks()
  } catch {
    message.error('重试失败')
  }
}

async function handleCancel(id: string) {
  try {
    await tasksApi.cancelAiTask(id)
    message.success('任务已取消')
    await fetchTasks()
  } catch {
    message.error('取消失败')
  }
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

    <NModal v-model:show="showDetail" preset="card" title="任务详情" style="max-width: 600px;">
      <template v-if="detailTask">
        <NDescriptions bordered :column="1" label-placement="left" size="small">
          <NDescriptionsItem label="任务ID">{{ detailTask.id }}</NDescriptionsItem>
          <NDescriptionsItem label="类型">{{ typeLabelMap[detailTask.type] || detailTask.type }}</NDescriptionsItem>
          <NDescriptionsItem label="状态">
            <NTag size="small" :type="statusColorMap[detailTask.status] ?? 'default'">{{ detailTask.status }}</NTag>
          </NDescriptionsItem>
          <NDescriptionsItem label="进度">
            <NProgress
              type="line"
              :percentage="detailTask.progress"
              :status="detailTask.status === 'failed' ? 'error' : detailTask.status === 'completed' ? 'success' : 'default'"
            />
          </NDescriptionsItem>
          <NDescriptionsItem label="输入摘要">{{ detailTask.input_summary || '-' }}</NDescriptionsItem>
          <NDescriptionsItem v-if="detailTask.error" label="错误信息">
            <span style="color: #d03050;">{{ detailTask.error }}</span>
          </NDescriptionsItem>
          <NDescriptionsItem label="创建时间">{{ detailTask.created_at }}</NDescriptionsItem>
          <NDescriptionsItem label="开始时间">{{ detailTask.started_at || '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="完成时间">{{ detailTask.completed_at || '-' }}</NDescriptionsItem>
        </NDescriptions>
      </template>
    </NModal>
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
