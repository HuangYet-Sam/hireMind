<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NCard, NButton, NDataTable, NTag, NSpace, NSelect, NSpin } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useInterviewStore } from '@/stores/hr/interviews'
import type { Interview } from '@/api/hr/interviews'
import InterviewCreateModal from '@/components/hr/InterviewCreateModal.vue'

const interviewStore = useInterviewStore()
const filterStatus = ref<string>('')
const showCreateModal = ref(false)

const statusOptions = [
  { label: '全部', value: '' },
  { label: '已安排', value: 'scheduled' },
  { label: '已确认', value: 'confirmed' },
  { label: '进行中', value: 'in_progress' },
  { label: '已完成', value: 'completed' },
  { label: '已取消', value: 'cancelled' },
]

const statusColorMap: Record<string, string> = {
  scheduled: 'warning',
  confirmed: 'info',
  in_progress: 'success',
  completed: 'default',
  cancelled: 'error',
  no_show: 'error',
}

const columns: DataTableColumns<Interview> = [
  { title: '候选人ID', key: 'candidate_id', width: 120 },
  { title: '岗位ID', key: 'position_id', width: 140, ellipsis: { tooltip: true } },
  { title: '轮次', key: 'round_number', width: 60 },
  { title: '类型', key: 'interview_type', width: 100 },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row) => h(NTag, { size: 'small', type: statusColorMap[row.status] as any }, () => row.status),
  },
  { title: '时间', key: 'scheduled_at', width: 160 },
  { title: '时长(分)', key: 'duration_minutes', width: 80 },
  { title: '评分', key: 'overall_score', width: 70, render: (row) => row.overall_score !== null ? `${row.overall_score}/10` : '-' },
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

onMounted(() => {
  interviewStore.fetchInterviews()
})

function handleFilter() {
  interviewStore.fetchInterviews({
    status: (filterStatus.value || undefined) as any,
  })
}

function handleView(id: string) {
  console.log('View interview:', id)
}

async function handleCancel(id: string) {
  await interviewStore.cancelInterview(id)
}

function handleCreateSaved() {
  interviewStore.fetchInterviews()
  showCreateModal.value = false
}
</script>

<template>
  <div class="interviews-view">
    <header class="page-header">
      <h2 class="header-title">面试管理</h2>
      <NButton type="primary" @click="showCreateModal = true">安排面试</NButton>
    </header>

    <div class="filter-bar">
      <NSelect v-model:value="filterStatus" :options="statusOptions" style="width: 120px;" @update:value="handleFilter" />
    </div>

    <NSpin :show="interviewStore.loading">
      <NDataTable
        :columns="columns"
        :data="interviewStore.interviews"
        :row-key="(row: Interview) => row.id"
        :pagination="{ pageSize: 20 }"
        striped
      />
    </NSpin>

    <!-- TODO: Calendar view tab -->

    <InterviewCreateModal
      :show="showCreateModal"
      @close="showCreateModal = false"
      @saved="handleCreateSaved"
    />
  </div>
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
}
</style>
