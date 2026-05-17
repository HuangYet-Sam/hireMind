<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NCard, NTree, NDataTable, NSpin, NButton, NEmpty, NTag, NSpace, NPopconfirm, useMessage } from 'naive-ui'
import type { TreeOption, DataTableColumns } from 'naive-ui'
import * as departmentsApi from '@/api/hr/departments'
import type { Department } from '@/api/hr/departments'
import * as positionsApi from '@/api/hr/positions'
import type { Position } from '@/api/hr/positions'
import DepartmentCreateModal from '@/components/hr/DepartmentCreateModal.vue'

const message = useMessage()
const departments = ref<Department[]>([])
const selectedDept = ref<Department | null>(null)
const deptPositions = ref<Position[]>([])
const loading = ref(false)
const positionsLoading = ref(false)
const showModal = ref(false)
const editingDept = ref<Department | null>(null)

onMounted(() => {
  loadDepartments()
})

async function loadDepartments() {
  loading.value = true
  try {
    departments.value = await departmentsApi.getDepartmentTree()
  } catch (err) {
    console.error('Failed to load departments:', err)
  } finally {
    loading.value = false
  }
}

function buildTreeOptions(list: Department[]): TreeOption[] {
  return list.map(dept => ({
    key: dept.id,
    label: `${dept.name} (${dept.current_headcount})`,
    children: dept.children?.length ? buildTreeOptions(dept.children) : undefined,
  }))
}

function handleSelect(keys: string[]) {
  if (keys.length > 0) {
    const findDept = (list: Department[]): Department | undefined => {
      for (const d of list) {
        if (d.id === keys[0]) return d
        if (d.children?.length) {
          const found = findDept(d.children)
          if (found) return found
        }
      }
    }
    selectedDept.value = findDept(departments.value) ?? null
    if (selectedDept.value) loadDeptPositions(selectedDept.value.id)
  }
}

async function loadDeptPositions(deptId: string) {
  positionsLoading.value = true
  try {
    const res = await positionsApi.listPositions({ department_id: deptId, page_size: 100 })
    deptPositions.value = res.items
  } catch (err) {
    console.error('Failed to load positions:', err)
    deptPositions.value = []
  } finally {
    positionsLoading.value = false
  }
}

function handleCreate() {
  editingDept.value = null
  showModal.value = true
}

function handleEdit() {
  editingDept.value = selectedDept.value
  showModal.value = true
}

async function handleDelete() {
  if (!selectedDept.value) return
  try {
    await departmentsApi.deleteDepartment(selectedDept.value.id)
    message.success('部门已删除')
    selectedDept.value = null
    deptPositions.value = []
    await loadDepartments()
  } catch (err: any) {
    message.error(err?.message || '删除失败')
  }
}

function handleModalSuccess() {
  showModal.value = false
  editingDept.value = null
  loadDepartments()
}

const statusMap: Record<string, { label: string; type: 'success' | 'warning' | 'error' | 'info' | 'default' }> = {
  draft: { label: '草稿', type: 'default' },
  open: { label: '招聘中', type: 'success' },
  paused: { label: '暂停', type: 'warning' },
  closed: { label: '已关闭', type: 'info' },
  archived: { label: '已归档', type: 'info' },
}

const positionColumns: DataTableColumns<Position> = [
  { title: '岗位名称', key: 'title', ellipsis: { tooltip: true } },
  { title: '类型', key: 'employment_type', width: 90, render: (row) => h(NTag, { size: 'small', type: 'info' }, () => row.employment_type) },
  { title: '状态', key: 'status', width: 90, render: (row) => {
    const s = statusMap[row.status] ?? { label: row.status, type: 'default' as const }
    return h(NTag, { size: 'small', type: s.type }, () => s.label)
  }},
  { title: '优先级', key: 'priority', width: 80 },
  { title: '人数', key: 'headcount', width: 70 },
]
</script>

<template>
  <div class="org-chart-view">
    <header class="page-header">
      <h2 class="header-title">组织架构</h2>
      <p class="header-desc">部门树与岗位列表管理</p>
    </header>

    <div class="org-content">
      <div class="dept-tree-panel">
        <NCard title="部门" size="small">
          <template #header-extra>
            <NButton size="tiny" type="primary" @click="handleCreate">新建部门</NButton>
          </template>
          <NSpin :show="loading">
            <NTree
              v-if="departments.length"
              :data="buildTreeOptions(departments)"
              :default-expand-all="true"
              block-line
              @update:selected-keys="handleSelect"
            />
            <NEmpty v-else description="暂无部门数据" />
          </NSpin>
        </NCard>
      </div>

      <div class="dept-detail-panel">
        <template v-if="selectedDept">
          <NCard :title="selectedDept.name" size="small">
            <template #header-extra>
              <NSpace size="small">
                <NButton size="tiny" @click="handleEdit">编辑</NButton>
                <NPopconfirm @positive-click="handleDelete">
                  <template #trigger>
                    <NButton size="tiny" type="error">删除</NButton>
                  </template>
                  确定删除部门「{{ selectedDept.name }}」吗？
                </NPopconfirm>
              </NSpace>
            </template>
            <div class="dept-meta">
              <span>负责人：{{ selectedDept.manager_name || '未指定' }}</span>
              <span>当前人数：{{ selectedDept.current_headcount }}</span>
              <span>编制上限：{{ selectedDept.headcount_limit ?? '不限' }}</span>
              <span v-if="selectedDept.description" class="dept-desc">{{ selectedDept.description }}</span>
            </div>
          </NCard>

          <NCard title="关联岗位" size="small" style="margin-top: 12px;">
            <NSpin :show="positionsLoading">
              <NDataTable
                v-if="deptPositions.length"
                :columns="positionColumns"
                :data="deptPositions"
                :bordered="false"
                size="small"
                :pagination="{ pageSize: 10 }"
              />
              <NEmpty v-else description="该部门暂无岗位" />
            </NSpin>
          </NCard>
        </template>
        <NEmpty v-else description="请在左侧选择一个部门" />
      </div>
    </div>

    <DepartmentCreateModal
      v-model:show="showModal"
      :edit-data="editingDept"
      :departments="departments"
      @created="handleModalSuccess"
    />
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.org-chart-view {
  padding: 24px;
  height: calc(100 * var(--vh));
  display: flex;
  flex-direction: column;
}

.page-header {
  margin-bottom: 24px;

  .header-title {
    font-size: 22px;
    font-weight: 600;
    color: $text-primary;
    margin: 0 0 4px;
  }

  .header-desc {
    font-size: 14px;
    color: $text-muted;
    margin: 0;
  }
}

.org-content {
  flex: 1;
  display: flex;
  gap: 16px;
  min-height: 0;
}

.dept-tree-panel {
  width: 300px;
  flex-shrink: 0;
}

.dept-detail-panel {
  flex: 1;
  min-width: 0;
}

.dept-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 14px;
  color: $text-secondary;

  .dept-desc {
    width: 100%;
    margin-top: 4px;
    color: $text-muted;
    font-size: 13px;
  }
}
</style>
