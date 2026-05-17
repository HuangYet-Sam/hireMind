<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NBreadcrumb, NBreadcrumbItem } from 'naive-ui'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const breadcrumbItems = computed(() => {
  const items = [{ label: t('sidebar.hrDashboard'), key: 'hr.dashboard' }]
  const nameMap: Record<string, string> = {
    'hr.orgChart': t('sidebar.hrOrgChart'),
    'hr.positions': t('sidebar.hrPositions'),
    'hr.positionDetail': t('sidebar.hrPositions'),
    'hr.resumes': t('sidebar.hrResumes'),
    'hr.candidates': t('sidebar.hrCandidates'),
    'hr.candidateDetail': t('sidebar.hrCandidates'),
    'hr.matching': t('sidebar.hrMatching'),
    'hr.interviews': t('sidebar.hrInterviews'),
    'hr.interviewDetail': t('sidebar.hrInterviews'),
    'hr.offers': t('sidebar.hrOffers'),
    'hr.offerDetail': t('sidebar.hrOffers'),
    'hr.analytics': t('sidebar.hrAnalytics'),
    'hr.tasks': t('sidebar.hrTasks'),
  }
  const label = nameMap[route.name as string]
  if (label && route.name !== 'hr.dashboard') {
    items.push({ label, key: route.name as string })
  }
  return items
})

function handleBreadcrumbClick(key: string) {
  if (key === route.name) return
  router.push({ name: key })
}
</script>

<template>
  <div class="hr-layout">
    <div class="hr-main">
      <header class="hr-breadcrumb-bar">
        <NBreadcrumb>
          <NBreadcrumbItem
            v-for="item in breadcrumbItems"
            :key="item.key"
            @click="handleBreadcrumbClick(item.key)"
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
