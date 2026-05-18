import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as interviewsApi from '@/api/hr/interviews'
import type {
  Interview,
  InterviewListParams,
  InterviewCalendarParams,
  CreateInterviewRequest,
  UpdateInterviewRequest,
  InterviewStats,
  InterviewerWorkloadItem,
  InterviewCalendarEvent,
  WorkloadStats,
  InterviewBriefingResponse,
  InterviewQuestionsResponse,
  RecommendedSlot,
} from '@/api/hr/interviews'

export type ViewMode = 'calendar' | 'board' | 'list'

export const useInterviewStore = defineStore('hr-interviews', () => {
  // ─── Core State ─────────────────────────────────────────────────
  const interviews = ref<Interview[]>([])
  const current = ref<Interview | null>(null)
  const loading = ref(false)
  const total = ref(0)
  const viewMode = ref<ViewMode>('list')
  const stats = ref<InterviewStats | null>(null)
  const statsLoading = ref(false)
  const calendarDate = ref(new Date())
  const filterStatus = ref<string>('')
  const sortBy = ref<string>('scheduled_at')
  const sortOrder = ref<'asc' | 'desc'>('desc')

  // ─── Calendar State ─────────────────────────────────────────────
  const calendarEvents = ref<InterviewCalendarEvent[]>([])
  const calendarLoading = ref(false)

  // ─── Workload State ─────────────────────────────────────────────
  const workloadStats = ref<WorkloadStats[]>([])
  const workloadLoading = ref(false)

  // ─── Briefing State ─────────────────────────────────────────────
  const currentBriefing = ref<InterviewBriefingResponse | null>(null)
  const briefingLoading = ref(false)

  // ─── Questions State ────────────────────────────────────────────
  const currentQuestions = ref<InterviewQuestionsResponse | null>(null)
  const questionsLoading = ref(false)

  // ─── Slots State ────────────────────────────────────────────────
  const recommendedSlots = ref<RecommendedSlot[]>([])
  const slotsLoading = ref(false)

  // ─── Computed ───────────────────────────────────────────────────
  const upcoming = computed(() =>
    interviews.value
      .filter(i => i.status === 'scheduled' || i.status === 'confirmed')
      .sort((a, b) => new Date(a.scheduled_at!).getTime() - new Date(b.scheduled_at!).getTime())
  )

  const byStatus = computed(() => {
    const map: Record<string, Interview[]> = {}
    for (const i of interviews.value) {
      const key = mapStatusToBoardColumn(i.status)
      if (!map[key]) map[key] = []
      map[key].push(i)
    }
    return map
  })

  const completedWithScore = computed(() =>
    interviews.value.filter(i => i.overall_score !== null)
  )

  const avgScore = computed(() => {
    const scored = completedWithScore.value
    if (!scored.length) return null
    return scored.reduce((s, i) => s + i.overall_score!, 0) / scored.length
  })

  const interviewerWorkload = computed<InterviewerWorkloadItem[]>(() => {
    const map: Record<string, { total: number; pendingFeedback: number; scores: number[] }> = {}
    for (const interview of interviews.value) {
      const ids = interview.interviewer_ids || []
      for (const iid of ids) {
        if (!map[iid]) map[iid] = { total: 0, pendingFeedback: 0, scores: [] }
        map[iid].total++
        if (interview.status === 'in_progress' || interview.status === 'completed') {
          if (interview.overall_score === null) map[iid].pendingFeedback++
        }
        if (interview.overall_score !== null) map[iid].scores.push(interview.overall_score)
      }
    }
    return Object.entries(map).map(([interviewer_id, d]) => ({
      interviewer_id,
      total_interviews: d.total,
      pending_feedback: d.pendingFeedback,
      avg_score: d.scores.length ? d.scores.reduce((a, b) => a + b, 0) / d.scores.length : null,
    }))
  })

  const calendarInterviews = computed(() => {
    return interviews.value.filter(i => i.scheduled_at !== null)
  })

  // ─── Helpers ────────────────────────────────────────────────────
  function mapStatusToBoardColumn(status: string): string {
    switch (status) {
      case 'pending': return 'pending'
      case 'scheduled': case 'confirmed': return 'scheduled'
      case 'in_progress': return 'in_progress'
      case 'completed':
        return interviews.value.find(i => i.status === status && i.overall_score === null)
          ? 'pending_feedback' : 'completed'
      default: return 'completed'
    }
  }

  function setViewMode(mode: ViewMode) {
    viewMode.value = mode
  }

  function setCalendarDate(date: Date) {
    calendarDate.value = date
  }

  // ─── Core Actions ───────────────────────────────────────────────
  async function fetchInterviews(params?: InterviewListParams) {
    loading.value = true
    try {
      const res = await interviewsApi.listInterviews(params)
      interviews.value = res.items
      total.value = res.total
    } catch (err) {
      console.error('Failed to fetch interviews:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchInterview(id: string) {
    loading.value = true
    try {
      current.value = await interviewsApi.getInterview(id)
    } catch (err) {
      console.error('Failed to fetch interview:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchCalendarData(params: InterviewCalendarParams) {
    loading.value = true
    try {
      const items = await interviewsApi.getInterviewCalendar(params)
      interviews.value = items
      total.value = items.length
    } catch (err) {
      console.error('Failed to fetch calendar data:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchStats(params?: { interviewer_id?: string; date_from?: string; date_to?: string }) {
    statsLoading.value = true
    try {
      stats.value = await interviewsApi.getInterviewStats(params)
    } catch (err) {
      console.error('Failed to fetch interview stats:', err)
    } finally {
      statsLoading.value = false
    }
  }

  async function createInterview(data: CreateInterviewRequest): Promise<Interview> {
    const interview = await interviewsApi.createInterview(data)
    interviews.value.unshift(interview)
    return interview
  }

  async function updateInterview(id: string, data: UpdateInterviewRequest): Promise<Interview> {
    const interview = await interviewsApi.updateInterview(id, data)
    const idx = interviews.value.findIndex(i => i.id === id)
    if (idx !== -1) interviews.value[idx] = interview
    if (current.value?.id === id) current.value = interview
    return interview
  }

  async function cancelInterview(id: string, reason?: string) {
    await interviewsApi.cancelInterview(id, reason)
    const idx = interviews.value.findIndex(i => i.id === id)
    if (idx !== -1) {
      interviews.value[idx] = { ...interviews.value[idx], status: 'cancelled' }
    }
  }

  async function rescheduleInterview(id: string, scheduledAt: string, durationMinutes?: number) {
    return updateInterview(id, {
      scheduled_at: scheduledAt,
      ...(durationMinutes !== undefined ? { duration_minutes: durationMinutes } : {}),
    })
  }

  async function changeStatus(id: string, status: string) {
    return updateInterview(id, { status })
  }

  // ─── Calendar Actions ───────────────────────────────────────────
  async function fetchCalendar(dateFrom: string, dateTo: string) {
    calendarLoading.value = true
    try {
      calendarEvents.value = await interviewsApi.fetchInterviewCalendar(dateFrom, dateTo)
    } catch (err) {
      console.error('Failed to fetch calendar events:', err)
    } finally {
      calendarLoading.value = false
    }
  }

  // ─── Workload Actions ───────────────────────────────────────────
  async function fetchWorkload() {
    workloadLoading.value = true
    try {
      workloadStats.value = await interviewsApi.fetchWorkloadStats()
    } catch (err) {
      console.error('Failed to fetch workload stats:', err)
    } finally {
      workloadLoading.value = false
    }
  }

  // ─── Briefing Actions ───────────────────────────────────────────
  async function generateBriefing(interviewId: string) {
    briefingLoading.value = true
    try {
      currentBriefing.value = await interviewsApi.generateBriefing(interviewId)
    } catch (err) {
      console.error('Failed to generate briefing:', err)
    } finally {
      briefingLoading.value = false
    }
  }

  function clearBriefing() {
    currentBriefing.value = null
  }

  // ─── Questions Actions ──────────────────────────────────────────
  async function generateQuestions(interviewId: string) {
    questionsLoading.value = true
    try {
      currentQuestions.value = await interviewsApi.generateQuestions(interviewId)
    } catch (err) {
      console.error('Failed to generate questions:', err)
    } finally {
      questionsLoading.value = false
    }
  }

  function clearQuestions() {
    currentQuestions.value = null
  }

  // ─── Slots Actions ──────────────────────────────────────────────
  async function fetchRecommendedSlots(interviewId: string) {
    slotsLoading.value = true
    try {
      recommendedSlots.value = await interviewsApi.recommendSlots(interviewId)
    } catch (err) {
      console.error('Failed to recommend slots:', err)
    } finally {
      slotsLoading.value = false
    }
  }

  // ─── Batch Actions ──────────────────────────────────────────────
  async function batchCreateInterviews(
    items: interviewsApi.BatchCreateInterviewItem[],
  ): Promise<Interview[]> {
    const created = await interviewsApi.batchCreateInterviews(items)
    interviews.value.unshift(...created)
    return created
  }

  // ─── Advance Round ──────────────────────────────────────────────
  async function advanceInterviewRound(interviewId: string): Promise<Interview> {
    const updated = await interviewsApi.advanceRound(interviewId)
    const idx = interviews.value.findIndex(i => i.id === interviewId)
    if (idx !== -1) interviews.value[idx] = updated
    if (current.value?.id === interviewId) current.value = updated
    return updated
  }

  // ─── Analyze Feedback ───────────────────────────────────────────
  async function analyzeFeedback(interviewId: string) {
    return interviewsApi.analyzeFeedback(interviewId)
  }

  return {
    // State
    interviews, current, loading, total, upcoming, viewMode,
    stats, statsLoading, calendarDate, filterStatus, sortBy, sortOrder,
    calendarEvents, calendarLoading,
    workloadStats, workloadLoading,
    currentBriefing, briefingLoading,
    currentQuestions, questionsLoading,
    recommendedSlots, slotsLoading,
    // Computed
    byStatus, calendarInterviews, completedWithScore, avgScore, interviewerWorkload,
    // Setters
    setViewMode, setCalendarDate,
    clearBriefing, clearQuestions,
    // Actions
    fetchInterviews, fetchInterview, fetchCalendarData, fetchStats,
    createInterview, updateInterview, cancelInterview,
    rescheduleInterview, changeStatus,
    fetchCalendar, fetchWorkload,
    generateBriefing, generateQuestions,
    fetchRecommendedSlots, batchCreateInterviews,
    advanceInterviewRound, analyzeFeedback,
  }
})
