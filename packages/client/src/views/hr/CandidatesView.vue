<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NCard, NButton, NDataTable, NInput, NSelect, NTag, NSpace, NAvatar, NSpin } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useCandidateStore } from '@/stores/hr/candidates'
import type { Candidate } from '@/api/hr/candidates'

const candidateStore = useCandidateStore()
const keyword = ref('')
const filterStatus = ref('')

const statusOptions = [
  { label: '全部', value: '' },
  { label: '新候选人', value: 'new' },
  { label: '筛选中', value: 'screening' },
  { label: '面试中', value: 'interviewing' },
  { label: '已Offer', value: 'offered' },
  { label: '已入职', value: 'hired' },
  { label: '已拒绝', value: 'rejected' },
]

const statusColorMap: Record<string, string> = {
  new: 'default',
  screening: 'warning',
  interviewing: 'info',
  offered: 'success',
  hired: 'success',
  rejected: 'error',
  withdrawn: 'default',
}

const columns: DataTableColumns<Candidate> = [
  {
    title: '姓名',
    key: 'name',
    width: 160,
    render: (row) => h(NSpace, { align: 'center', size: 'small' }, () => [
      h(NAvatar, { size: 'small', round: true }, () => row.name.charAt(0)),
      h('span', row.name),
    ]),
  },
  { title: '当前公司', key: 'current_company', width: 140, ellipsis: { tooltip: true } },
  { title: '职位', key: 'current_title', width: 120, ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row) => h(NTag, { size: 'small', type: statusColorMap[row.status] as any }, () => row.status),
  },
  { title: '来源', key: 'source', width: 90 },
  {
    title: '匹配分',
    key: 'match_score',
    width: 80,
    render: (row) => row.match_score !== null ? `${Math.round(row.match_score * 100)}%` : '-',
  },
  { title: '经验(年)', key: 'years_of_experience', width: 80 },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    render: (row) => h(NButton, { size: 'tiny', onClick: () => handleView(row.id) }, () => '360°视图'),
  },
]

onMounted(() => {
  candidateStore.fetchCandidates()
})

function handleSearch() {
  candidateStore.fetchCandidates({
    keyword: keyword.value || undefined,
    status: (filterStatus.value || undefined) as any,
  })
}

function handleView(id: string) {
  // TODO: navigate to 360° candidate view
  console.log('View candidate:', id)
}
</script>

<template>
  <div class="candidates-view">
    <header class="page-header">
      <h2 class="header-title">候选人</h2>
      <NButton type="primary">添加候选人</NButton>
    </header>

    <div class="filter-bar">
      <NInput v-model:value="keyword" placeholder="搜索候选人..." clearable style="width: 240px;" @keyup.enter="handleSearch" />
      <NSelect v-model:value="filterStatus" :options="statusOptions" style="width: 120px;" @update:value="handleSearch" />
      <NButton @click="handleSearch">搜索</NButton>
    </div>

    <NSpin :show="candidateStore.loading">
      <NDataTable
        :columns="columns"
        :data="candidateStore.candidates"
        :row-key="(row: Candidate) => row.id"
        :pagination="{ pageSize: 20 }"
        striped
      />
    </NSpin>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.candidates-view {
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
