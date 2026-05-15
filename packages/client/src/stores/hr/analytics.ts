import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as analyticsApi from '@/api/hr/analytics'
import type { DashboardData, PipelineStage, TimeToHirePeriod, SourceEffectiveness, DepartmentSummary } from '@/api/hr/analytics'

export const useAnalyticsStore = defineStore('hr-analytics', () => {
  const kpi = ref<DashboardData | null>(null)
  const funnel = ref<PipelineStage[]>([])
  const timeToHire = ref<TimeToHirePeriod[]>([])
  const sourceEffectiveness = ref<SourceEffectiveness[]>([])
  const departmentSummary = ref<DepartmentSummary[]>([])
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

  async function fetchTimeToHire(params?: Record<string, string>) {
    try {
      timeToHire.value = await analyticsApi.getTimeToHire(params)
    } catch (err) {
      console.error('Failed to fetch time-to-hire:', err)
    }
  }

  async function fetchSourceEffectiveness() {
    try {
      sourceEffectiveness.value = await analyticsApi.getSourceBreakdown()
    } catch (err) {
      console.error('Failed to fetch source effectiveness:', err)
    }
  }

  async function fetchDepartmentSummary() {
    try {
      departmentSummary.value = await analyticsApi.getDepartmentSummary()
    } catch (err) {
      console.error('Failed to fetch department summary:', err)
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
        fetchTimeToHire(params),
        fetchSourceEffectiveness(),
        fetchDepartmentSummary(),
      ])
    } finally {
      loading.value = false
    }
  }

  return {
    kpi, funnel, timeToHire, sourceEffectiveness, departmentSummary, loading,
    fetchKpi, fetchFunnel, fetchTimeToHire, fetchSourceEffectiveness, fetchDepartmentSummary,
    fetchDashboard, fetchAll,
  }
})
