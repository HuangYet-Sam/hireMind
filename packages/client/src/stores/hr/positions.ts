import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as positionsApi from '@/api/hr/positions'
import type { Position, PositionListParams, CreatePositionRequest, UpdatePositionRequest } from '@/api/hr/positions'

export const usePositionStore = defineStore('hr-positions', () => {
  const positions = ref<Position[]>([])
  const current = ref<Position | null>(null)
  const loading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)

  const openPositions = computed(() => positions.value.filter(p => p.status === 'open'))
  const draftPositions = computed(() => positions.value.filter(p => p.status === 'draft'))

  async function fetchPositions(params?: PositionListParams) {
    loading.value = true
    try {
      const res = await positionsApi.listPositions({ page: page.value, page_size: pageSize.value, ...params })
      positions.value = res.items
      total.value = res.total
      page.value = res.page
    } catch (err) {
      console.error('Failed to fetch positions:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchPosition(id: string) {
    loading.value = true
    try {
      current.value = await positionsApi.getPosition(id)
    } catch (err) {
      console.error('Failed to fetch position:', err)
    } finally {
      loading.value = false
    }
  }

  async function createPosition(data: CreatePositionRequest): Promise<Position> {
    const position = await positionsApi.createPosition(data)
    positions.value.unshift(position)
    return position
  }

  async function updatePosition(id: string, data: UpdatePositionRequest): Promise<Position> {
    const position = await positionsApi.updatePosition(id, data)
    const idx = positions.value.findIndex(p => p.id === id)
    if (idx !== -1) positions.value[idx] = position
    if (current.value?.id === id) current.value = position
    return position
  }

  async function deletePosition(id: string) {
    await positionsApi.deletePosition(id)
    positions.value = positions.value.filter(p => p.id !== id)
  }

  return {
    positions, current, loading, total, page, pageSize,
    openPositions, draftPositions,
    fetchPositions, fetchPosition, createPosition, updatePosition, deletePosition,
  }
})
