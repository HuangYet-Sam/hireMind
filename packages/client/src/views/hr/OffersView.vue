<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton, NDataTable, NTag, NSpace, NSelect, NInput, NDatePicker,
  NCard, NGrid, NGridItem, NStatistic, NProgress, NCheckbox, NPopconfirm, useMessage,
} from 'naive-ui'
import type { DataTableColumns, SelectOption } from 'naive-ui'
import { useOfferStore } from '@/stores/hr/offers'
import type { Offer } from '@/api/hr/offers'
import OfferCreateModal from '@/components/hr/OfferCreateModal.vue'
import ErrorBoundary from '@/components/hr/ErrorBoundary.vue'
import TableSkeleton from '@/components/hr/TableSkeleton.vue'

type TagType = 'default' | 'info' | 'success' | 'warning' | 'error'

const router = useRouter()
const offerStore = useOfferStore()
const message = useMessage()

// ─── 筛选状态 ────────────────────────────────────────────────
const filterStatuses = ref<string[]>([])
const filterPosition = ref<string | null>(null)
const filterDepartment = ref<string | null>(null)
const filterDateRange = ref<[number, number] | null>(null)
const filterUrgency = ref<string | null>(null)
const showCreateModal = ref(false)
const editingOffer = ref<Offer | null>(null)
const selectedRowKeys = ref<string[]>([])

// ─── 状态选项 ────────────────────────────────────────────────
const statusOptions: SelectOption[] = [
  { label: '草稿', value: 'draft' },
  { label: '待审批', value: 'pending_approval' },
  { label: '已审批', value: 'approved' },
  { label: '已发送', value: 'sent' },
  { label: '已接受', value: 'accepted' },
  { label: '已拒绝', value: 'rejected' },
  { label: '已撤回', value: 'withdrawn' },
]

const urgencyOptions: SelectOption[] = [
  { label: '低', value: 'low' },
  { label: '普通', value: 'normal' },
  { label: '高', value: 'high' },
  { label: '紧急', value: 'critical' },
]

const statusColorMap: Record<string, TagType> = {
  draft: 'default',
  pending_approval: 'warning',
  approved: 'info',
  sent: 'info',
  accepted: 'success',
  rejected: 'error',
  withdrawn: 'default',
  expired: 'error',
}

const statusLabelMap: Record<string, string> = {
  draft: '草稿',
  pending_approval: '待审批',
  approved: '已审批',
  sent: '已发送',
  accepted: '已接受',
  rejected: '已拒绝',
  withdrawn: '已撤回',
  expired: '已过期',
}

const urgencyColorMap: Record<string, string> = {
  low: '#999',
  normal: '#4a90d9',
  high: '#f0a020',
  critical: '#d03050',
}

// ─── 统计卡片 ────────────────────────────────────────────────
const stats = computed(() => offerStore.statsCards)

// ─── 薪资脱敏 ────────────────────────────────────────────────
function maskSalary(val: number | null): string {
  if (val == null) return '-'
  if (val >= 10000) return `¥${(val / 10000).toFixed(1)}W`
  return `¥${val.toLocaleString()}`
}

// ─── 表格列 ──────────────────────────────────────────────────
const columns: DataTableColumns<Offer> = [
  {
    type: 'selection',
  },
  {
    title: '候选人',
    key: 'candidate_name',
    width: 100,
    render: (row) => row.candidate_name || row.candidate_id,
  },
  {
    title: '岗位',
    key: 'position_title',
    width: 130,
    ellipsis: { tooltip: true },
    render: (row) => row.position_title || row.position_id || '-',
  },
  {
    title: '部门',
    key: 'department',
    width: 90,
    render: (row) => row.department || '-',
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row) => h(NTag, {
      size: 'small',
      type: statusColorMap[row.status] ?? 'default',
    }, () => statusLabelMap[row.status] ?? row.status),
  },
  {
    title: '紧急程度',
    key: 'urgency',
    width: 80,
    render: (row) => {
      const u = row.urgency
      if (!u) return '-'
      return h(NTag, {
        size: 'small',
        bordered: false,
        color: { color: urgencyColorMap[u] + '20', textColor: urgencyColorMap[u] },
      }, () => ({ low: '低', normal: '普通', high: '高', critical: '紧急' }[u] ?? u))
    },
  },
  {
    title: '月薪(脱敏)',
    key: 'base_salary',
    width: 100,
    render: (row) => maskSalary(row.base_salary),
  },
  {
    title: '审批进度',
    key: 'approval_progress',
    width: 110,
    render: (row) => {
      const progress = row.approval_progress
      if (progress == null) return '-'
      let status: 'success' | 'warning' | 'error' = 'success'
      if (row.status === 'rejected') status = 'error'
      else if (progress < 100) status = 'warning'
      return h(NProgress, {
        type: 'line',
        percentage: progress,
        status,
        indicatorPlacement: 'inside',
        height: 16,
      })
    },
  },
  {
    title: '入职日期',
    key: 'proposed_start_date',
    width: 100,
    render: (row) => row.proposed_start_date || '-',
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 110,
    render: (row) => row.created_at ? new Date(row.created_at).toLocaleDateString('zh-CN') : '-',
  },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    fixed: 'right',
    render: (row) => h(NSpace, { size: 'small' }, () => {
      const btns = [
        h(NButton, { size: 'tiny', onClick: () => handleView(row.id) }, () => '详情'),
      ]
      if (row.status === 'pending_approval') {
        btns.push(h(NButton, {
          size: 'tiny', type: 'success',
          onClick: () => handleApprove(row.id),
        }, () => '审批'))
      }
      if (row.status === 'approved') {
        btns.push(h(NButton, {
          size: 'tiny', type: 'primary',
          onClick: () => handleSend(row.id),
        }, () => '发送'))
      }
      if (['draft', 'pending_approval', 'approved', 'sent'].includes(row.status)) {
        btns.push(h(NPopconfirm, {
          onPositiveClick: () => handleWithdraw(row.id),
        }, {
          trigger: () => h(NButton, { size: 'tiny', type: 'warning' }, () => '撤回'),
          default: () => '确认撤回该Offer？',
        }))
      }
      return btns
    }),
  },
]

// ─── 生命周期 ────────────────────────────────────────────────
onMounted(() => {
  offerStore.fetchOffers()
})

// ─── 筛选 ────────────────────────────────────────────────────
function handleFilter() {
  offerStore.fetchOffers({
    status: filterStatuses.value.length === 1 ? filterStatuses.value[0] : undefined,
    position_id: filterPosition.value || undefined,
    department: filterDepartment.value || undefined,
    date_from: filterDateRange.value?.[0] ? new Date(filterDateRange.value[0]).toISOString() : undefined,
    date_to: filterDateRange.value?.[1] ? new Date(filterDateRange.value[1]).toISOString() : undefined,
  })
}

function handleResetFilter() {
  filterStatuses.value = []
  filterPosition.value = null
  filterDepartment.value = null
  filterDateRange.value = null
  filterUrgency.value = null
  offerStore.fetchOffers()
}

// ─── 行选择 ──────────────────────────────────────────────────
function handleCheck(rowKeys: string[]) {
  selectedRowKeys.value = rowKeys
}

const hasSelection = computed(() => selectedRowKeys.value.length > 0)

// ─── 操作 ────────────────────────────────────────────────────
function handleView(id: string) {
  router.push({ name: 'hr.offerDetail', params: { id } })
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

async function handleWithdraw(id: string) {
  try {
    await offerStore.withdrawOffer(id)
    message.success('Offer已撤回')
  } catch {
    message.error('撤回失败')
  }
}

// ─── 批量操作 ────────────────────────────────────────────────
async function handleBatchApprove() {
  if (!selectedRowKeys.value.length) return
  let success = 0
  for (const id of selectedRowKeys.value) {
    try {
      await offerStore.approveOffer(id)
      success++
    } catch { /* skip */ }
  }
  message.success(`批量审批完成：${success}/${selectedRowKeys.value.length} 成功`)
  selectedRowKeys.value = []
  offerStore.fetchOffers()
}

async function handleBatchWithdraw() {
  if (!selectedRowKeys.value.length) return
  let success = 0
  for (const id of selectedRowKeys.value) {
    try {
      await offerStore.withdrawOffer(id)
      success++
    } catch { /* skip */ }
  }
  message.success(`批量撤回完成：${success}/${selectedRowKeys.value.length} 成功`)
  selectedRowKeys.value = []
  offerStore.fetchOffers()
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

      <!-- 统计卡片 -->
      <NGrid :cols="5" :x-gap="12" :y-gap="12" class="stats-grid">
        <NGridItem>
          <NCard size="small" class="stat-card">
            <NStatistic label="总计" :value="stats.total" />
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard size="small" class="stat-card stat-pending">
            <NStatistic label="待审批" :value="stats.pendingApproval" />
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard size="small" class="stat-card stat-sent">
            <NStatistic label="已发送" :value="stats.sent" />
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard size="small" class="stat-card stat-accepted">
            <NStatistic label="已接受" :value="stats.accepted" />
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard size="small" class="stat-card stat-rejected">
            <NStatistic label="已拒绝" :value="stats.rejected" />
          </NCard>
        </NGridItem>
      </NGrid>

      <!-- 增强筛选栏 -->
      <div class="filter-bar">
        <NSelect
          v-model:value="filterStatuses"
          :options="statusOptions"
          multiple
          placeholder="状态筛选"
          style="width: 220px"
          @update:value="handleFilter"
        />
        <NSelect
          v-model:value="filterDepartment"
          :options="[]"
          placeholder="部门"
          clearable
          style="width: 120px"
          @update:value="handleFilter"
        />
        <NSelect
          v-model:value="filterUrgency"
          :options="urgencyOptions"
          placeholder="紧急程度"
          clearable
          style="width: 120px"
          @update:value="handleFilter"
        />
        <NDatePicker
          v-model:value="filterDateRange"
          type="daterange"
          clearable
          style="width: 240px"
          @update:value="handleFilter"
        />
        <NButton size="small" @click="handleResetFilter">重置</NButton>
      </div>

      <!-- 批量操作栏 -->
      <div v-if="hasSelection" class="batch-bar">
        <span class="batch-info">已选择 {{ selectedRowKeys.length }} 项</span>
        <NSpace>
          <NButton size="small" type="success" @click="handleBatchApprove">批量审批</NButton>
          <NPopconfirm @positive-click="handleBatchWithdraw">
            <template #trigger>
              <NButton size="small" type="warning">批量撤回</NButton>
            </template>
            确认批量撤回选中的 {{ selectedRowKeys.length }} 个Offer？
          </NPopconfirm>
        </NSpace>
      </div>

      <TableSkeleton v-if="offerStore.loading" :rows="6" :columns="7" />
      <NDataTable
        v-else
        :columns="columns"
        :data="offerStore.offers"
        :row-key="(row: Offer) => row.id"
        :pagination="{ pageSize: 20 }"
        :scroll-x="1300"
        :checked-row-keys="selectedRowKeys"
        @update:checked-row-keys="handleCheck"
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

.stats-grid {
  margin-bottom: 20px;

  @media (max-width: $breakpoint-mobile) {
    :deep(.n-grid) {
      grid-template-columns: repeat(2, 1fr) !important;
    }
  }
}

.stat-card {
  text-align: center;
  transition: box-shadow $transition-fast;

  &:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }

  &.stat-pending {
    border-top: 3px solid var(--warning);
  }

  &.stat-sent {
    border-top: 3px solid var(--accent-info);
  }

  &.stat-accepted {
    border-top: 3px solid var(--success);
  }

  &.stat-rejected {
    border-top: 3px solid var(--error);
  }
}

.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.batch-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: rgba(var(--accent-info-rgb), 0.06);
  border-radius: $radius-sm;
  margin-bottom: 12px;

  .batch-info {
    font-size: 13px;
    color: $text-secondary;
  }
}
</style>
