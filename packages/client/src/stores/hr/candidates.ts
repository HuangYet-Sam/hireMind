import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as candidatesApi from '@/api/hr/candidates'
import type { Candidate, CandidateListParams, CreateCandidateRequest, UpdateCandidateRequest } from '@/api/hr/candidates'

export const useCandidateStore = defineStore('hr-candidates', () => {
  const candidates = ref<Candidate[]>([])
  const current = ref<Candidate | null>(null)
  const loading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)

  const candidatesByStatus = computed(() => {
    const map: Record<string, Candidate[]> = {}
    for (const c of candidates.value) {
      ;(map[c.status] ??= []).push(c)
    }
    return map
  })

  async function fetchCandidates(params?: CandidateListParams) {
    loading.value = true
    try {
      const res = await candidatesApi.listCandidates({ page: page.value, page_size: pageSize.value, ...params })
      candidates.value = res.items
      total.value = res.total
      page.value = res.page
    } catch (err) {
      console.error('Failed to fetch candidates:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchCandidate(id: string) {
    loading.value = true
    try {
      current.value = await candidatesApi.getCandidate(id)
    } catch (err) {
      console.error('Failed to fetch candidate:', err)
    } finally {
      loading.value = false
    }
  }

  async function createCandidate(data: CreateCandidateRequest): Promise<Candidate> {
    const candidate = await candidatesApi.createCandidate(data)
    candidates.value.unshift(candidate)
    return candidate
  }

  async function updateCandidate(id: string, data: UpdateCandidateRequest): Promise<Candidate> {
    const candidate = await candidatesApi.updateCandidate(id, data)
    const idx = candidates.value.findIndex(c => c.id === id)
    if (idx !== -1) candidates.value[idx] = candidate
    if (current.value?.id === id) current.value = candidate
    return candidate
  }

  async function deleteCandidate(id: string) {
    await candidatesApi.deleteCandidate(id)
    candidates.value = candidates.value.filter(c => c.id !== id)
  }

  return {
    candidates, current, loading, total, page, pageSize,
    candidatesByStatus,
    fetchCandidates, fetchCandidate, createCandidate, updateCandidate, deleteCandidate,
  }
})
