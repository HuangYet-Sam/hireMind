import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as matchingApi from '@/api/hr/matching'
import type { MatchResult, MatchRequest } from '@/api/hr/matching'

export const useMatchingStore = defineStore('hr-matching', () => {
  const matches = ref<MatchResult[]>([])
  const currentMatrix = ref<MatchResult[]>([])
  const loading = ref(false)

  async function fetchMatches(params?: Record<string, string | number>) {
    loading.value = true
    try {
      matches.value = await matchingApi.listMatches(params)
    } catch (err) {
      console.error('Failed to fetch matches:', err)
    } finally {
      loading.value = false
    }
  }

  async function matchPosition(data: MatchRequest): Promise<MatchResult[]> {
    loading.value = true
    try {
      const results = await matchingApi.matchPositionToCandidates(data)
      matches.value = results
      return results
    } catch (err) {
      console.error('Failed to match position:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  async function fetchMatchMatrix(positionId: string) {
    loading.value = true
    try {
      currentMatrix.value = await matchingApi.getMatchMatrix(positionId)
    } catch (err) {
      console.error('Failed to fetch match matrix:', err)
    } finally {
      loading.value = false
    }
  }

  async function batchMatch(positionIds: string[], candidateIds?: string[]) {
    return matchingApi.batchMatch({ position_ids: positionIds, candidate_ids: candidateIds })
  }

  return {
    matches, currentMatrix, loading,
    fetchMatches, matchPosition, fetchMatchMatrix, batchMatch,
  }
})
