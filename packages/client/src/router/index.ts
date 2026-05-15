import { createRouter, createWebHashHistory } from 'vue-router'
import { hasApiKey } from '@/api/client'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },

    // ─── Hermes Admin Routes (unchanged) ──────────────────
    {
      path: '/hermes/chat',
      name: 'hermes.chat',
      component: () => import('@/views/hermes/ChatView.vue'),
    },
    {
      path: '/hermes/history',
      name: 'hermes.history',
      component: () => import('@/views/hermes/HistoryView.vue'),
    },
    {
      path: '/hermes/jobs',
      name: 'hermes.jobs',
      component: () => import('@/views/hermes/JobsView.vue'),
    },
    {
      path: '/hermes/models',
      name: 'hermes.models',
      component: () => import('@/views/hermes/ModelsView.vue'),
    },
    {
      path: '/hermes/profiles',
      name: 'hermes.profiles',
      component: () => import('@/views/hermes/ProfilesView.vue'),
    },
    {
      path: '/hermes/logs',
      name: 'hermes.logs',
      component: () => import('@/views/hermes/LogsView.vue'),
    },
    {
      path: '/hermes/usage',
      name: 'hermes.usage',
      component: () => import('@/views/hermes/UsageView.vue'),
    },
    {
      path: '/hermes/skills',
      name: 'hermes.skills',
      component: () => import('@/views/hermes/SkillsView.vue'),
    },
    {
      path: '/hermes/memory',
      name: 'hermes.memory',
      component: () => import('@/views/hermes/MemoryView.vue'),
    },
    {
      path: '/hermes/settings',
      name: 'hermes.settings',
      component: () => import('@/views/hermes/SettingsView.vue'),
    },
    {
      path: '/hermes/gateways',
      name: 'hermes.gateways',
      component: () => import('@/views/hermes/GatewaysView.vue'),
    },
    {
      path: '/hermes/channels',
      name: 'hermes.channels',
      component: () => import('@/views/hermes/ChannelsView.vue'),
    },
    {
      path: '/hermes/terminal',
      name: 'hermes.terminal',
      component: () => import('@/views/hermes/TerminalView.vue'),
    },
    {
      path: '/hermes/group-chat',
      name: 'hermes.groupChat',
      component: () => import('@/views/hermes/GroupChatView.vue'),
    },
    {
      path: '/hermes/files',
      name: 'hermes.files',
      component: () => import('@/views/hermes/FilesView.vue'),
    },

    // ─── HireMind Recruitment Routes ─────────────────────
    {
      path: '/hr',
      component: () => import('@/components/layout/HrLayout.vue'),
      meta: { hr: true },
      children: [
        {
          path: '',
          redirect: { name: 'hr.dashboard' },
        },
        {
          path: 'dashboard',
          name: 'hr.dashboard',
          component: () => import('@/views/hr/DashboardView.vue'),
        },
        {
          path: 'org-chart',
          name: 'hr.orgChart',
          component: () => import('@/views/hr/OrgChartView.vue'),
        },
        {
          path: 'positions',
          name: 'hr.positions',
          component: () => import('@/views/hr/PositionsView.vue'),
        },
        {
          path: 'positions/:id',
          name: 'hr.positionDetail',
          component: () => import('@/views/hr/PositionDetailView.vue'),
        },
        {
          path: 'resumes',
          name: 'hr.resumes',
          component: () => import('@/views/hr/ResumesView.vue'),
        },
        {
          path: 'candidates',
          name: 'hr.candidates',
          component: () => import('@/views/hr/CandidatesView.vue'),
        },
        {
          path: 'candidates/:id',
          name: 'hr.candidateDetail',
          component: () => import('@/views/hr/CandidateDetailView.vue'),
        },
        {
          path: 'matching',
          name: 'hr.matching',
          component: () => import('@/views/hr/MatchingView.vue'),
        },
        {
          path: 'interviews',
          name: 'hr.interviews',
          component: () => import('@/views/hr/InterviewsView.vue'),
        },
        {
          path: 'interviews/:id',
          name: 'hr.interviewDetail',
          component: () => import('@/views/hr/InterviewDetailView.vue'),
        },
        {
          path: 'offers',
          name: 'hr.offers',
          component: () => import('@/views/hr/OffersView.vue'),
        },
        {
          path: 'offers/:id',
          name: 'hr.offerDetail',
          component: () => import('@/views/hr/OfferDetailView.vue'),
        },
        {
          path: 'analytics',
          name: 'hr.analytics',
          component: () => import('@/views/hr/AnalyticsView.vue'),
        },
        {
          path: 'tasks',
          name: 'hr.tasks',
          component: () => import('@/views/hr/TasksView.vue'),
        },
      ],
    },
  ],
})

router.beforeEach((to, _from, next) => {
  // Public pages don't need auth
  if (to.meta.public) {
    // Already has key, skip login
    if (to.name === 'login' && hasApiKey()) {
      next({ path: '/hermes/chat' })
      return
    }
    next()
    return
  }

  // All other pages require token
  if (!hasApiKey()) {
    next({ name: 'login' })
    return
  }

  next()
})

export default router
