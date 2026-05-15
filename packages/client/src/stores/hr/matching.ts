import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as matchingApi from '@/api/hr/matching'
import type { MatchResult, MatchRequestParams } from '@/api/hr/matching'

export const useMatchingStore = defineStore('hr-matching', () => {
  const matches = ref<MatchResult[]>([])
  const loading = ref(false)

  async function matchCandidatesForPosition(positionId: string, params?: MatchRequestParams): Promise<MatchResult[]> {
    loading.value = true
    try {
      const result = await matchingApi.matchCandidatesForPosition(positionId, params)
      matches.value = result.matches
      return result.matches
    } catch (err) {
      console.error('Failed to match candidates for position:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  async function matchPositionsForCandidate(candidateId: string, params?: MatchRequestParams): Promise<MatchResult[]> {
    loading.value = true
    try {
      const result = await matchingApi.matchPositionsForCandidate(candidateId, params)
      matches.value = result.matches
      return result.matches
    } catch (err) {
      console.error('Failed to match positions for candidate:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  async function fetchMatchResult(positionId: string) {
    loading.value = true
    try {
      const result = await matchingApi.getMatchResult(positionId)
      if (result) matches.value = result.matches
    } catch (err) {
      console.error('Failed to fetch match result:', err)
    } finally {
      loading.value = false
    }
  }

  return {
    matches, loading,
    matchCandidatesForPosition, matchPositionsForCandidate, fetchMatchResult,
  }
})
