// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

import { useAnalyticsStore } from '../../packages/client/src/stores/hr/analytics'

function mockResponse(data: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
    headers: new Headers({ 'content-type': 'application/json' }),
  })
}

describe('Analytics Store', () => {
  let store: ReturnType<typeof useAnalyticsStore>

  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('hermes_api_key', 'test-key')
    vi.clearAllMocks()
    setActivePinia(createPinia())
    store = useAnalyticsStore()
  })

  it('fetchKpi populates kpi ref', async () => {
    const kpiData = {
      open_positions: 12,
      candidates_in_pipeline: 45,
      interviews_this_week: 8,
      offers_pending: 3,
      avg_time_to_hire: 21,
    }
    mockFetch.mockReturnValue(mockResponse(kpiData))
    await store.fetchKpi()
    expect(store.kpi).toEqual(kpiData)
  })

  it('fetchFunnel populates funnel ref', async () => {
    const funnelData = [
      { stage: 'applied', count: 100 },
      { stage: 'screened', count: 60 },
      { stage: 'interviewed', count: 30 },
      { stage: 'offered', count: 10 },
      { stage: 'hired', count: 8 },
    ]
    mockFetch.mockReturnValue(mockResponse(funnelData))
    await store.fetchFunnel()
    expect(store.funnel).toHaveLength(5)
    expect(store.funnel[0].stage).toBe('applied')
  })

  it('fetchTimeToHire populates timeToHire ref', async () => {
    const trendData = [
      { period: '2026-01', avg_days: 25, count: 5 },
      { period: '2026-02', avg_days: 20, count: 8 },
    ]
    mockFetch.mockReturnValue(mockResponse(trendData))
    await store.fetchTimeToHire()
    expect(store.timeToHire).toHaveLength(2)
    expect(store.timeToHire[1].avg_days).toBe(20)
  })

  it('fetchSourceEffectiveness populates sourceEffectiveness ref', async () => {
    const sourceData = [
      { source: 'referral', total: 30, hired: 8, conversion_rate: 0.27 },
      { source: 'linkedin', total: 50, hired: 5, conversion_rate: 0.1 },
    ]
    mockFetch.mockReturnValue(mockResponse(sourceData))
    await store.fetchSourceEffectiveness()
    expect(store.sourceEffectiveness).toHaveLength(2)
  })

  it('fetchDepartmentSummary populates departmentSummary ref', async () => {
    const deptData = [
      { department: 'Engineering', positions: 5, candidates: 20 },
      { department: 'Product', positions: 3, candidates: 12 },
    ]
    mockFetch.mockReturnValue(mockResponse(deptData))
    await store.fetchDepartmentSummary()
    expect(store.departmentSummary).toHaveLength(2)
  })

  it('fetchAll loads all data in parallel', async () => {
    mockFetch
      .mockReturnValueOnce(mockResponse({ open_positions: 5, candidates_in_pipeline: 10, interviews_this_week: 2, offers_pending: 1, avg_time_to_hire: 18 }))
      .mockReturnValueOnce(mockResponse([{ stage: 'applied', count: 50 }]))
      .mockReturnValueOnce(mockResponse([{ period: '2026-03', avg_days: 18, count: 3 }]))
      .mockReturnValueOnce(mockResponse([{ source: 'referral', total: 10, hired: 2, conversion_rate: 0.2 }]))
      .mockReturnValueOnce(mockResponse([{ department: 'Eng', positions: 3, candidates: 8 }]))

    await store.fetchAll()
    expect(store.kpi).not.toBeNull()
    expect(store.funnel).toHaveLength(1)
    expect(store.timeToHire).toHaveLength(1)
    expect(store.sourceEffectiveness).toHaveLength(1)
    expect(store.departmentSummary).toHaveLength(1)
    expect(mockFetch).toHaveBeenCalledTimes(5)
  })
})
