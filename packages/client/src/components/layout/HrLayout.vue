<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NMenu, NBreadcrumb, NBreadcrumbItem } from 'naive-ui'
import type { MenuOption } from 'naive-ui'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const activeKey = computed(() => route.name as string)

const menuOptions: MenuOption[] = [
  { label: '工作台', key: 'hr.dashboard' },
  { label: '组织架构', key: 'hr.orgChart' },
  { label: '岗位管理', key: 'hr.positions' },
  { label: '简历库', key: 'hr.resumes' },
  { label: '候选人', key: 'hr.candidates' },
  { label: '智能匹配', key: 'hr.matching' },
  { label: '面试管理', key: 'hr.interviews' },
  { label: 'Offer管理', key: 'hr.offers' },
  { label: '数据分析', key: 'hr.analytics' },
  { label: '任务中心', key: 'hr.tasks' },
]

const breadcrumbItems = computed(() => {
  const items = [{ label: 'HireMind', key: 'hr.dashboard' }]
  const current = menuOptions.find((o) => o.key === route.name)
  if (current && route.name !== 'hr.dashboard') {
    items.push({ label: current.label as string, key: current.key as string })
  }
  return items
})

function handleMenuClick(key: string) {
  router.push({ name: key })
}
</script>

<template>
  <div class="hr-layout">
    <aside class="hr-sidebar">
      <div class="hr-sidebar-header">
        <h3 class="hr-brand">HireMind</h3>
        <span class="hr-brand-sub">AI 招聘平台</span>
      </div>
      <NMenu
        :value="activeKey"
        :options="menuOptions"
        @update:value="handleMenuClick"
      />
    </aside>
    <div class="hr-main">
      <header class="hr-breadcrumb-bar">
        <NBreadcrumb>
          <NBreadcrumbItem
            v-for="item in breadcrumbItems"
            :key="item.key"
            @click="handleMenuClick(item.key)"
          >
            {{ item.label }}
          </NBreadcrumbItem>
        </NBreadcrumb>
      </header>
      <div class="hr-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.hr-layout {
  display: flex;
  height: 100%;
  width: 100%;
  overflow: hidden;
}

.hr-sidebar {
  width: 200px;
  min-width: 200px;
  background: $bg-sidebar;
  border-right: 1px solid $border-color;
  display: flex;
  flex-direction: column;
  overflow-y: auto;

  .hr-sidebar-header {
    padding: 20px 16px 12px;
    border-bottom: 1px solid $border-light;

    .hr-brand {
      font-size: 16px;
      font-weight: 700;
      color: $text-primary;
      margin: 0;
      line-height: 1.3;
    }

    .hr-brand-sub {
      font-size: 11px;
      color: $text-muted;
    }
  }
}

.hr-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.hr-breadcrumb-bar {
  padding: 12px 24px;
  border-bottom: 1px solid $border-light;
  background: $bg-card;
}

.hr-content {
  flex: 1;
  overflow-y: auto;
  background: $bg-primary;
}
</style>
