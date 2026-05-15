<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NCard, NButton, NDataTable, NTag, NSpace, NSelect, NSteps, NStep, NSpin } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useOfferStore } from '@/stores/hr/offers'
import type { Offer } from '@/api/hr/offers'
import OfferCreateModal from '@/components/hr/OfferCreateModal.vue'

const offerStore = useOfferStore()
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
  { title: '候选人', key: 'candidate_name', width: 120 },
  { title: '岗位', key: 'position_title', width: 140, ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => h(NTag, { size: 'small', type: statusColorMap[row.status] as any }, () => row.status),
  },
  { title: '薪资', key: 'salary', width: 100, render: (row) => `${row.salary_currency} ${row.salary.toLocaleString()}` },
  { title: '入职日期', key: 'start_date', width: 110 },
  { title: '合同类型', key: 'contract_type', width: 90 },
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
  await offerStore.approveOffer(id)
}

async function handleSend(id: string) {
  await offerStore.sendOffer(id)
}

function openCreateModal() {
  editingOffer.value = null
  showCreateModal.value = true
}

function openEditModal(offer: Offer) {
  editingOffer.value = offer
  showCreateModal.value = true
}

function handleModalSaved() {
  showCreateModal.value = false
  editingOffer.value = null
  offerStore.fetchOffers()
}
</script>

<template>
  <div class="offers-view">
    <header class="page-header">
      <h2 class="header-title">Offer管理</h2>
      <NButton type="primary" @click="openCreateModal">创建Offer</NButton>
    </header>

    <div class="filter-bar">
      <NSelect v-model:value="filterStatus" :options="statusOptions" style="width: 120px;" @update:value="handleFilter" />
    </div>

    <NSpin :show="offerStore.loading">
      <NDataTable
        :columns="columns"
        :data="offerStore.offers"
        :row-key="(row: Offer) => row.id"
        :pagination="{ pageSize: 20 }"
        striped
      />
    </NSpin>

    <OfferCreateModal
      :show="showCreateModal"
      :edit-data="editingOffer"
      @close="showCreateModal = false"
      @saved="handleModalSaved"
    />
  </div>
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
