import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as matchingApi from '@/api/hr/matching'
import type { MatchResultItem, CandidateMatchResultItem, MatchDetailResponse, MatchRequestParams } from '@/api/hr/matching'

export const useMatchingStore = defineStore('hr-matching', () => {
  const matches = ref<(MatchResultItem | CandidateMatchResultItem)[]>([])
  const matchDetails = ref<MatchDetailResponse[]>([])
  const loading = ref(false)

  async function matchCandidatesForPosition(positionId: string, params?: MatchRequestParams): Promise<MatchResultItem[]> {
    loading.value = true
    try {
      const result = await matchingApi.matchCandidatesForPosition(positionId, params)
      matches.value = result.matches
      return result.matches
    } catch (err) {
      console.error('Failed to match candidates for position:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function matchPositionsForCandidate(candidateId: string, params?: MatchRequestParams): Promise<CandidateMatchResultItem[]> {
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
      if (result) {
        matchDetails.value = result.items
        matches.value = result.items
      }
    } catch (err) {
      console.error('Failed to fetch match result:', err)
    } finally {
      loading.value = false
    }
  }

  return {
    matches, matchDetails, loading,
    matchCandidatesForPosition, matchPositionsForCandidate, fetchMatchResult,
  }
})
