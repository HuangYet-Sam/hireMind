<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NBreadcrumb, NBreadcrumbItem } from 'naive-ui'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const collapsed = ref(false)
const isMobile = ref(false)

function checkMobile() {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value) {
    collapsed.value = true
  }
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

function toggleCollapse() {
  collapsed.value = !collapsed.value
}

const menuItems = computed(() => [
  { key: 'hr.dashboard', label: t('sidebar.hrDashboard') },
  { key: 'hr.orgChart', label: t('sidebar.hrOrgChart') },
  { key: 'hr.positions', label: t('sidebar.hrPositions') },
  { key: 'hr.resumes', label: t('sidebar.hrResumes') },
  { key: 'hr.candidates', label: t('sidebar.hrCandidates') },
  { key: 'hr.matching', label: t('sidebar.hrMatching') },
  { key: 'hr.interviews', label: t('sidebar.hrInterviews') },
  { key: 'hr.offers', label: t('sidebar.hrOffers') },
  { key: 'hr.analytics', label: t('sidebar.hrAnalytics') },
  { key: 'hr.tasks', label: t('sidebar.hrTasks') },
])

const activeKey = computed(() => {
  const name = route.name as string
  // Map detail routes back to their parent for highlight
  if (name === 'hr.positionDetail') return 'hr.positions'
  if (name === 'hr.candidateDetail') return 'hr.candidates'
  if (name === 'hr.interviewDetail') return 'hr.interviews'
  if (name === 'hr.offerDetail') return 'hr.offers'
  return name
})

function handleMenuClick(key: string) {
  router.push({ name: key })
}

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

function goHome() {
  router.push('/')
}

const logoPath = '/logo.png'
</script>

<template>
  <div class="hr-layout">
    <!-- HR Sidebar -->
    <aside class="hr-sidebar" :class="{ collapsed }">
      <!-- Logo -->
      <div class="hr-sidebar-logo">
        <img :src="logoPath" alt="HireMind" class="hr-logo-img" />
        <span v-if="!collapsed" class="hr-logo-text">HireMind</span>
        <button v-if="!isMobile" class="hr-collapse-btn" @click="toggleCollapse" :title="collapsed ? '展开' : '收起'">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline v-if="collapsed" points="9 18 15 12 9 6" />
            <polyline v-else points="15 18 9 12 15 6" />
          </svg>
        </button>
      </div>

      <!-- Navigation -->
      <nav class="hr-sidebar-nav">
        <button
          v-for="item in menuItems"
          :key="item.key"
          class="hr-nav-item"
          :class="{ active: activeKey === item.key }"
          @click="handleMenuClick(item.key)"
          :title="collapsed ? item.label : undefined"
        >
          <svg v-if="item.key === 'hr.dashboard'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10" />
            <circle cx="12" cy="12" r="6" />
            <circle cx="12" cy="12" r="2" />
          </svg>
          <svg v-else-if="item.key === 'hr.orgChart'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="8" y="2" width="8" height="6" rx="1" />
            <rect x="2" y="16" width="6" height="6" rx="1" />
            <rect x="16" y="16" width="6" height="6" rx="1" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="5" y1="12" x2="19" y2="12" />
            <line x1="5" y1="12" x2="5" y2="16" />
            <line x1="19" y1="12" x2="19" y2="16" />
          </svg>
          <svg v-else-if="item.key === 'hr.positions'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          <svg v-else-if="item.key === 'hr.resumes'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
          <svg v-else-if="item.key === 'hr.candidates'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
          <svg v-else-if="item.key === 'hr.matching'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
          <svg v-else-if="item.key === 'hr.interviews'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          <svg v-else-if="item.key === 'hr.offers'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <path d="M9 15l2 2 4-4" />
          </svg>
          <svg v-else-if="item.key === 'hr.analytics'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="12" width="4" height="9" rx="1" />
            <rect x="10" y="7" width="4" height="14" rx="1" />
            <rect x="17" y="3" width="4" height="18" rx="1" />
          </svg>
          <svg v-else-if="item.key === 'hr.tasks'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 18h6" />
            <path d="M10 22h4" />
            <path d="M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z" />
          </svg>
          <span v-if="!collapsed" class="hr-nav-label">{{ item.label }}</span>
        </button>
      </nav>

      <!-- Footer: back to main -->
      <div class="hr-sidebar-footer">
        <button class="hr-nav-item hr-back-btn" @click="goHome" :title="collapsed ? '返回主界面' : undefined">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 12H5" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
          <span v-if="!collapsed" class="hr-nav-label">返回主界面</span>
        </button>
      </div>
    </aside>

    <!-- Main content area -->
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

/* ─── Sidebar ─── */

.hr-sidebar {
  width: $sidebar-width;
  height: 100%;
  background-color: $bg-sidebar;
  border-right: 1px solid $border-color;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width $transition-normal;
  overflow: hidden;

  &.collapsed {
    width: $sidebar-collapsed-width;
  }
}

.hr-sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 12px;
  border-bottom: 1px solid $border-color;
  position: relative;
  background-color: $bg-card;
  flex-shrink: 0;

  .dark & {
    background-color: #393939;
  }

  .hr-logo-img {
    width: 28px;
    height: 28px;
    flex-shrink: 0;
  }

  .hr-logo-text {
    font-size: 18px;
    font-weight: 600;
    letter-spacing: 0.5px;
    color: $text-primary;
    white-space: nowrap;
    overflow: hidden;
  }

  .hr-collapse-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border: none;
    background: none;
    color: $text-muted;
    border-radius: $radius-sm;
    cursor: pointer;
    margin-left: auto;
    flex-shrink: 0;
    transition: all $transition-fast;

    &:hover {
      color: $text-primary;
      background-color: rgba(var(--accent-primary-rgb), 0.08);
    }
  }
}

.hr-sidebar.collapsed .hr-sidebar-logo {
  justify-content: center;
  gap: 0;
  padding: 16px 8px;

  .hr-logo-text {
    display: none;
  }

  .hr-collapse-btn {
    display: none;
  }
}

.hr-sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px;
  overflow-y: auto;
  min-height: 0;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }
}

.hr-sidebar.collapsed .hr-sidebar-nav {
  padding: 8px 4px;
}

.hr-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: none;
  background: none;
  color: $text-secondary;
  font-size: 14px;
  border-radius: $radius-sm;
  cursor: pointer;
  transition: all $transition-fast;
  width: 100%;
  text-align: left;

  &:hover {
    background-color: rgba(var(--accent-primary-rgb), 0.06);
    color: $text-primary;
  }

  &.active {
    background-color: rgba(var(--accent-primary-rgb), 0.12);
    color: $accent-primary;
  }

  .hr-nav-label {
    white-space: nowrap;
    overflow: hidden;
  }
}

.hr-sidebar.collapsed .hr-nav-item {
  justify-content: center;
  padding: 10px 4px;
  gap: 0;

  .hr-nav-label {
    display: none;
  }
}

/* ─── Sidebar Footer ─── */

.hr-sidebar-footer {
  padding: 8px;
  border-top: 1px solid $border-color;
  flex-shrink: 0;
}

.hr-sidebar.collapsed .hr-sidebar-footer {
  padding: 8px 4px;
}

.hr-back-btn {
  color: $text-muted;

  &:hover {
    color: $text-primary;
  }
}

/* ─── Main Content ─── */

.hr-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.hr-breadcrumb-bar {
  padding: 12px 24px;
  border-bottom: 1px solid $border-light;
  background: $bg-card;
  flex-shrink: 0;
}

.hr-content {
  flex: 1;
  overflow-y: auto;
  background: $bg-primary;
}

/* ─── Mobile ─── */

@media (max-width: $breakpoint-mobile) {
  .hr-sidebar {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 1000;
    width: $sidebar-collapsed-width;
    transform: translateX(-100%);
    transition: transform $transition-normal, width $transition-normal;

    &:hover {
      transform: translateX(0);
      width: $sidebar-width;
    }
  }
}
</style>
