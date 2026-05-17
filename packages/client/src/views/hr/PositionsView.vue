<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NCard, NButton, NDataTable, NSpace, NInput, NSelect, NTag, useMessage } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { usePositionStore } from '@/stores/hr/positions'
import type { Position } from '@/api/hr/positions'
import PositionCreateModal from '@/components/hr/PositionCreateModal.vue'
import ErrorBoundary from '@/components/hr/ErrorBoundary.vue'
import TableSkeleton from '@/components/hr/TableSkeleton.vue'

const positionStore = usePositionStore()
const message = useMessage()
const showCreateModal = ref(false)
const editingPosition = ref<Position | null>(null)
const keyword = ref('')

const statusOptions = [
  { label: '全部', value: '' },
  { label: '草稿', value: 'draft' },
  { label: '招聘中', value: 'open' },
  { label: '已暂停', value: 'paused' },
  { label: '已关闭', value: 'closed' },
  { label: '已归档', value: 'archived' },
]

const filterStatus = ref('')

const statusColorMap: Record<string, string> = {
  draft: 'default',
  open: 'success',
  paused: 'warning',
  closed: 'error',
  archived: 'info',
}

const columns: DataTableColumns<Position> = [
  { title: '岗位名称', key: 'title', ellipsis: { tooltip: true } },
  { title: '地点', key: 'location', width: 100 },
  { title: '类型', key: 'employment_type', width: 80 },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row) => h(NTag, { size: 'small', type: statusColorMap[row.status] as any }, () => row.status),
  },
  { title: '人数', key: 'headcount', width: 70 },
  { title: '优先级', key: 'priority', width: 80 },
  { title: '创建时间', key: 'created_at', width: 120 },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render: (row) => h(NSpace, { size: 'small' }, () => [
      h(NButton, { size: 'tiny', onClick: () => handleEdit(row) }, () => '编辑'),
      h(NButton, { size: 'tiny', type: 'error', onClick: () => handleDelete(row.id) }, () => '删除'),
    ]),
  },
]

onMounted(() => {
  positionStore.fetchPositions()
})

function handleSearch() {
  positionStore.fetchPositions({
    keyword: keyword.value || undefined,
    status: (filterStatus.value || undefined) as any,
  })
}

function handleCreate() {
  editingPosition.value = null
  showCreateModal.value = true
}

function handleEdit(row: Position) {
  editingPosition.value = row
  showCreateModal.value = true
}

async function handleDelete(id: string) {
  try {
    await positionStore.deletePosition(id)
    message.success('岗位已删除')
  } catch {
    message.error('删除失败')
  }
}

function handleModalSaved() {
  positionStore.fetchPositions()
  editingPosition.value = null
  showCreateModal.value = false
}

function handleModalClose() {
  showCreateModal.value = false
  editingPosition.value = null
}
</script>

<template>
  <ErrorBoundary>
    <div class="positions-view">
      <header class="page-header">
        <h2 class="header-title">岗位管理</h2>
        <NButton type="primary" @click="handleCreate">新建岗位</NButton>
      </header>

      <!-- Filters -->
      <div class="filter-bar">
        <NInput v-model:value="keyword" placeholder="搜索岗位名称..." clearable style="width: 240px;" @keyup.enter="handleSearch" />
        <NSelect v-model:value="filterStatus" :options="statusOptions" style="width: 120px;" @update:value="handleSearch" />
        <NButton @click="handleSearch">搜索</NButton>
      </div>

      <!-- Table -->
      <TableSkeleton v-if="positionStore.loading" :rows="6" :columns="7" />
      <NDataTable
        v-else
        :columns="columns"
        :data="positionStore.positions"
        :row-key="(row: Position) => row.id"
        :pagination="{ pageSize: 20 }"
        :scroll-x="900"
        striped
      />

      <PositionCreateModal
        :show="showCreateModal"
        :edit-data="editingPosition"
        @saved="handleModalSaved"
        @close="handleModalClose"
      />
    </div>
  </ErrorBoundary>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.positions-view {
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
