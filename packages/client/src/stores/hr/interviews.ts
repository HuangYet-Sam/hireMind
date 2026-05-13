import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as interviewsApi from '@/api/hr/interviews'
import type { Interview, InterviewListParams, CreateInterviewRequest, UpdateInterviewRequest } from '@/api/hr/interviews'

export const useInterviewStore = defineStore('hr-interviews', () => {
  const interviews = ref<Interview[]>([])
  const current = ref<Interview | null>(null)
  const loading = ref(false)
  const total = ref(0)

  const upcoming = computed(() =>
    interviews.value
      .filter(i => i.status === 'scheduled' || i.status === 'confirmed')
      .sort((a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime())
  )

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

  async function cancelInterview(id: string) {
    const interview = await interviewsApi.cancelInterview(id)
    const idx = interviews.value.findIndex(i => i.id === id)
    if (idx !== -1) interviews.value[idx] = interview
  }

  return {
    interviews, current, loading, total, upcoming,
    fetchInterviews, fetchInterview, createInterview, updateInterview, cancelInterview,
  }
})
