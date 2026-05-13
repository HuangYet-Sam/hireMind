import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as analyticsApi from '@/api/hr/analytics'
import type { KpiSummary, RecruitmentFunnel, HiringTrend, PositionMetrics } from '@/api/hr/analytics'

export const useAnalyticsStore = defineStore('hr-analytics', () => {
  const kpi = ref<KpiSummary | null>(null)
  const funnel = ref<RecruitmentFunnel[]>([])
  const trends = ref<HiringTrend[]>([])
  const positionMetrics = ref<PositionMetrics[]>([])
  const loading = ref(false)

  async function fetchKpi(params?: Record<string, string>) {
    try {
      kpi.value = await analyticsApi.getKpiSummary(params)
    } catch (err) {
      console.error('Failed to fetch KPI:', err)
    }
  }

  async function fetchFunnel(params?: Record<string, string>) {
    try {
      funnel.value = await analyticsApi.getRecruitmentFunnel(params)
    } catch (err) {
      console.error('Failed to fetch funnel:', err)
    }
  }

  async function fetchTrends(params?: Record<string, string>) {
    try {
      trends.value = await analyticsApi.getHiringTrends(params)
    } catch (err) {
      console.error('Failed to fetch trends:', err)
    }
  }

  async function fetchPositionMetrics(params?: Record<string, string>) {
    try {
      positionMetrics.value = await analyticsApi.getPositionMetrics(params)
    } catch (err) {
      console.error('Failed to fetch position metrics:', err)
    }
  }

  async function fetchDashboard() {
    loading.value = true
    try {
      kpi.value = await analyticsApi.getDashboardOverview()
    } catch (err) {
      console.error('Failed to fetch dashboard:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchAll(params?: Record<string, string>) {
    loading.value = true
    try {
      await Promise.all([
        fetchKpi(params),
        fetchFunnel(params),
        fetchTrends(params),
      ])
    } finally {
      loading.value = false
    }
  }

  return {
    kpi, funnel, trends, positionMetrics, loading,
    fetchKpi, fetchFunnel, fetchTrends, fetchPositionMetrics, fetchDashboard, fetchAll,
  }
})
