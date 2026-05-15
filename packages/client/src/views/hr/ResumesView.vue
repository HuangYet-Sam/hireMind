<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NCard, NButton, NDataTable, NInput, NSelect, NTag, NSpace, NSpin } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useResumeStore } from '@/stores/hr/resumes'
import type { Resume } from '@/api/hr/resumes'

const resumeStore = useResumeStore()
const keyword = ref('')
const filterParseStatus = ref('')

const parseStatusOptions = [
  { label: '全部', value: '' },
  { label: '待解析', value: 'pending' },
  { label: '解析中', value: 'processing' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' },
]

const parseColorMap: Record<string, string> = {
  pending: 'default',
  processing: 'warning',
  completed: 'success',
  failed: 'error',
}

const columns: DataTableColumns<Resume> = [
  { title: '文件名', key: 'filename', ellipsis: { tooltip: true } },
  { title: '候选人ID', key: 'candidate_id', width: 120 },
  {
    title: '解析状态',
    key: 'parse_status',
    width: 100,
    render: (row) => h(NTag, { size: 'small', type: parseColorMap[row.parse_status] as any }, () => row.parse_status),
  },
  { title: 'AI标签', key: 'tags', width: 200, render: (row) => h(NSpace, { size: 4 }, () => row.tags.slice(0, 3).map(t => h(NTag, { size: 'small' }, () => t))) },
  { title: '来源', key: 'source', width: 90 },
  { title: '上传时间', key: 'created_at', width: 120 },
  {
    title: '操作',
    key: 'actions',
    width: 140,
    render: (row) => h(NSpace, { size: 'small' }, () => [
      h(NButton, { size: 'tiny', onClick: () => handleView(row.id) }, () => '查看'),
      h(NButton, { size: 'tiny', onClick: () => handleReparse(row.id) }, () => '重解析'),
      h(NButton, { size: 'tiny', type: 'error', onClick: () => handleDelete(row.id) }, () => '删除'),
    ]),
  },
]

onMounted(() => {
  resumeStore.fetchResumes()
})

function handleSearch() {
  resumeStore.fetchResumes({
    keyword: keyword.value || undefined,
    parse_status: (filterParseStatus.value || undefined) as any,
  })
}

function handleView(id: string) {
  // TODO: open resume viewer modal
  console.log('View resume:', id)
}

async function handleReparse(id: string) {
  await resumeStore.reparseResume(id)
}

async function handleDelete(id: string) {
  await resumeStore.deleteResume(id)
}
</script>

<template>
  <div class="resumes-view">
    <header class="page-header">
      <h2 class="header-title">简历库</h2>
      <NButton type="primary">上传简历</NButton>
    </header>

    <div class="filter-bar">
      <NInput v-model:value="keyword" placeholder="搜索简历..." clearable style="width: 240px;" @keyup.enter="handleSearch" />
      <NSelect v-model:value="filterParseStatus" :options="parseStatusOptions" style="width: 120px;" @update:value="handleSearch" />
      <NButton @click="handleSearch">搜索</NButton>
    </div>

    <NSpin :show="resumeStore.loading">
      <NDataTable
        :columns="columns"
        :data="resumeStore.resumes"
        :row-key="(row: Resume) => row.id"
        :pagination="{ pageSize: 20 }"
        striped
      />
    </NSpin>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.resumes-view {
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
