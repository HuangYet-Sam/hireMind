<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NTree, NDataTable, NSpin, NButton, NEmpty } from 'naive-ui'
import type { TreeOption } from 'naive-ui'
import * as departmentsApi from '@/api/hr/departments'
import type { Department } from '@/api/hr/departments'

const departments = ref<Department[]>([])
const selectedDept = ref<Department | null>(null)
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    departments.value = await departmentsApi.getDepartmentTree()
  } catch (err) {
    console.error('Failed to load departments:', err)
  } finally {
    loading.value = false
  }
})

function buildTreeOptions(list: Department[]): TreeOption[] {
  return list.map(dept => ({
    key: dept.id,
    label: `${dept.name} (${dept.open_positions})`,
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
  }
}
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
            <NButton size="tiny" type="primary">新建部门</NButton>
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
        <NCard v-if="selectedDept" :title="selectedDept.name" size="small">
          <p>负责人：{{ selectedDept.head_name || '未指定' }}</p>
          <p>人数：{{ selectedDept.head_count }}</p>
          <p>在招岗位：{{ selectedDept.open_positions }}</p>
          <!-- TODO: 岗位列表 -->
        </NCard>
        <NEmpty v-else description="请在左侧选择一个部门" />
      </div>
    </div>
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
</style>
