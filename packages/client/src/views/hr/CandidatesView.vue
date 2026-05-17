<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NDataTable, NInput, NSelect, NTag, NSpace, NAvatar, useMessage } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useCandidateStore } from '@/stores/hr/candidates'
import type { Candidate } from '@/api/hr/candidates'
import CandidateCreateModal from '@/components/hr/CandidateCreateModal.vue'
import ErrorBoundary from '@/components/hr/ErrorBoundary.vue'
import TableSkeleton from '@/components/hr/TableSkeleton.vue'

const router = useRouter()
const candidateStore = useCandidateStore()
const message = useMessage()
const keyword = ref('')
const filterStage = ref('')
const showCreateModal = ref(false)
const editingCandidate = ref<Candidate | null>(null)

const stageOptions = [
  { label: '全部', value: '' },
  { label: '已投递', value: 'applied' },
  { label: '已筛选', value: 'screened' },
  { label: '面试中', value: 'interviewed' },
  { label: '已Offer', value: 'offered' },
  { label: '已入职', value: 'hired' },
  { label: '已拒绝', value: 'rejected' },
]

const stageColorMap: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
  applied: 'default',
  screened: 'info',
  interviewed: 'warning',
  offered: 'success',
  hired: 'success',
  rejected: 'error',
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
    title: '阶段',
    key: 'stage',
    width: 90,
    render: (row) => h(NTag, { size: 'small', type: stageColorMap[row.stage] ?? 'default' }, () => row.stage),
  },
  { title: '来源', key: 'source', width: 90 },
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
    stage: (filterStage.value || undefined) as Candidate['stage'] | undefined,
  })
}

function handleView(id: string) {
  router.push({ name: 'hr.candidateDetail', params: { id } })
}

function openCreateModal() {
  editingCandidate.value = null
  showCreateModal.value = true
}

function handleModalSaved() {
  candidateStore.fetchCandidates()
  showCreateModal.value = false
  editingCandidate.value = null
  message.success('操作成功')
}
</script>

<template>
  <ErrorBoundary>
    <div class="candidates-view">
      <header class="page-header">
        <h2 class="header-title">候选人</h2>
        <NButton type="primary" @click="openCreateModal">添加候选人</NButton>
      </header>

      <div class="filter-bar">
        <NInput v-model:value="keyword" placeholder="搜索候选人..." clearable style="width: 240px;" @keyup.enter="handleSearch" />
        <NSelect v-model:value="filterStage" :options="stageOptions" style="width: 120px;" @update:value="handleSearch" />
        <NButton @click="handleSearch">搜索</NButton>
      </div>

      <TableSkeleton v-if="candidateStore.loading" :rows="6" :columns="7" />
      <NDataTable
        v-else
        :columns="columns"
        :data="candidateStore.candidates"
        :row-key="(row: Candidate) => row.id"
        :pagination="{ pageSize: 20 }"
        :scroll-x="800"
        striped
      />

      <CandidateCreateModal
        :show="showCreateModal"
        :edit-data="editingCandidate"
        @close="showCreateModal = false"
        @saved="handleModalSaved"
      />
    </div>
  </ErrorBoundary>
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

  @media (max-width: $breakpoint-mobile) {
    gap: 8px;

    :deep(.n-input) {
      width: 100% !important;
    }
  }
}
</style>
