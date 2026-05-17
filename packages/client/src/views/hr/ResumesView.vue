<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NDataTable, NInput, NSelect, NTag, NSpace, NSpin, useMessage } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useResumeStore } from '@/stores/hr/resumes'
import type { Resume } from '@/api/hr/resumes'

type TagType = 'default' | 'info' | 'success' | 'warning' | 'error'

const router = useRouter()
const resumeStore = useResumeStore()
const message = useMessage()
const keyword = ref('')
const filterParseStatus = ref('')

const parseStatusOptions = [
  { label: '全部', value: '' },
  { label: '待解析', value: 'pending' },
  { label: '解析中', value: 'processing' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' },
]

const parseColorMap: Record<string, TagType> = {
  pending: 'default',
  processing: 'warning',
  completed: 'success',
  failed: 'error',
}

const columns: DataTableColumns<Resume> = [
  { title: '文件名', key: 'original_filename', ellipsis: { tooltip: true } },
  { title: '候选人ID', key: 'candidate_id', width: 120 },
  {
    title: '解析状态',
    key: 'parse_status',
    width: 100,
    render: (row) => h(NTag, { size: 'small', type: parseColorMap[row.parse_status] ?? 'default' }, () => row.parse_status),
  },
  { title: '页数', key: 'page_count', width: 80 },
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
    status: filterParseStatus.value || undefined,
  })
}

function handleView(id: string) {
  router.push({ name: 'hr.resumeDetail', params: { id } })
}

async function handleReparse(id: string) {
  try {
    await resumeStore.reparseResume(id)
    message.success('重新解析已触发')
  } catch {
    message.error('重新解析失败')
  }
}

async function handleDelete(id: string) {
  try {
    await resumeStore.deleteResume(id)
    message.success('简历已删除')
  } catch {
    message.error('删除失败')
  }
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
