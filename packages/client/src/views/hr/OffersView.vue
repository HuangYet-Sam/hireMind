<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NButton, NDataTable, NTag, NSpace, NSelect, useMessage } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useOfferStore } from '@/stores/hr/offers'
import type { Offer } from '@/api/hr/offers'
import OfferCreateModal from '@/components/hr/OfferCreateModal.vue'
import ErrorBoundary from '@/components/hr/ErrorBoundary.vue'
import TableSkeleton from '@/components/hr/TableSkeleton.vue'

const offerStore = useOfferStore()
const message = useMessage()
const filterStatus = ref<string>('')
const showCreateModal = ref(false)
const editingOffer = ref<Offer | null>(null)

const statusOptions = [
  { label: '全部', value: '' },
  { label: '草稿', value: 'draft' },
  { label: '待审批', value: 'pending_approval' },
  { label: '已审批', value: 'approved' },
  { label: '已发送', value: 'sent' },
  { label: '已接受', value: 'accepted' },
  { label: '已拒绝', value: 'rejected' },
  { label: '已撤回', value: 'withdrawn' },
]

const statusColorMap: Record<string, string> = {
  draft: 'default',
  pending_approval: 'warning',
  approved: 'info',
  sent: 'info',
  accepted: 'success',
  rejected: 'error',
  withdrawn: 'default',
  expired: 'error',
}

const columns: DataTableColumns<Offer> = [
  { title: '候选人', key: 'candidate_id', width: 120 },
  { title: '岗位', key: 'position_id', width: 140, ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => h(NTag, { size: 'small', type: statusColorMap[row.status] as any }, () => row.status),
  },
  { title: '基础薪资', key: 'base_salary', width: 100, render: (row) => row.base_salary ? `¥${row.base_salary.toLocaleString()}` : '-' },
  { title: '入职日期', key: 'proposed_start_date', width: 110 },
  { title: '创建时间', key: 'created_at', width: 120 },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    render: (row) => h(NSpace, { size: 'small' }, () => {
      const btns = [h(NButton, { size: 'tiny', onClick: () => handleView(row.id) }, () => '详情')]
      if (row.status === 'pending_approval') {
        btns.push(h(NButton, { size: 'tiny', type: 'success', onClick: () => handleApprove(row.id) }, () => '审批'))
      }
      if (row.status === 'approved') {
        btns.push(h(NButton, { size: 'tiny', type: 'primary', onClick: () => handleSend(row.id) }, () => '发送'))
      }
      return btns
    }),
  },
]

onMounted(() => {
  offerStore.fetchOffers()
})

function handleFilter() {
  offerStore.fetchOffers({
    status: (filterStatus.value || undefined) as any,
  })
}

function handleView(id: string) {
  console.log('View offer:', id)
}

async function handleApprove(id: string) {
  try {
    await offerStore.approveOffer(id)
    message.success('Offer已审批')
  } catch {
    message.error('审批失败')
  }
}

async function handleSend(id: string) {
  try {
    await offerStore.sendOffer(id)
    message.success('Offer已发送')
  } catch {
    message.error('发送失败')
  }
}

function openCreateModal() {
  editingOffer.value = null
  showCreateModal.value = true
}

function handleModalSaved() {
  showCreateModal.value = false
  editingOffer.value = null
  offerStore.fetchOffers()
  message.success('操作成功')
}
</script>

<template>
  <ErrorBoundary>
    <div class="offers-view">
      <header class="page-header">
        <h2 class="header-title">Offer管理</h2>
        <NButton type="primary" @click="openCreateModal">创建Offer</NButton>
      </header>

      <div class="filter-bar">
        <NSelect v-model:value="filterStatus" :options="statusOptions" style="width: 120px;" @update:value="handleFilter" />
      </div>

      <TableSkeleton v-if="offerStore.loading" :rows="6" :columns="7" />
      <NDataTable
        v-else
        :columns="columns"
        :data="offerStore.offers"
        :row-key="(row: Offer) => row.id"
        :pagination="{ pageSize: 20 }"
        :scroll-x="900"
        striped
      />

      <OfferCreateModal
        :show="showCreateModal"
        :edit-data="editingOffer"
        @close="showCreateModal = false"
        @saved="handleModalSaved"
      />
    </div>
  </ErrorBoundary>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.offers-view {
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
}
</style>
