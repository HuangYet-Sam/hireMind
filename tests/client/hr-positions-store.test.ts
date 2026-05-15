// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

vi.mock('@/router', () => ({
  default: { currentRoute: { value: { name: 'hr.positions' } }, replace: vi.fn() },
}))

import { usePositionStore } from '../../packages/client/src/stores/hr/positions'

function mockResponse(data: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
    headers: new Headers({ 'content-type': 'application/json' }),
  })
}

describe('Position Store', () => {
  let store: ReturnType<typeof usePositionStore>

  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('hermes_api_key', 'test-key')
    vi.clearAllMocks()
    setActivePinia(createPinia())
    store = usePositionStore()
  })

  it('fetchPositions populates positions array', async () => {
    const mockData = {
      items: [
        { id: 'p1', title: 'Frontend Engineer', status: 'open', department_id: 'd1', location: 'Beijing', employment_type: 'full_time', headcount: 3, priority: 'high', is_remote: false, description: '', requirements: [], benefits: [], required_skills: [], preferred_skills: [], education_requirement: null, experience_years_min: null, salary_min: null, salary_max: null, created_by: 'u1', created_at: '2026-01-01', updated_at: '2026-01-01' },
      ],
      total: 1,
    }
    mockFetch.mockReturnValue(mockResponse(mockData))
    await store.fetchPositions({ status: 'open' })
    expect(store.positions).toHaveLength(1)
    expect(store.positions[0].title).toBe('Frontend Engineer')
    expect(store.total).toBe(1)
  })

  it('fetchPositions with empty result', async () => {
    mockFetch.mockReturnValue(mockResponse({ items: [], total: 0 }))
    await store.fetchPositions()
    expect(store.positions).toHaveLength(0)
    expect(store.total).toBe(0)
  })

  it('createPosition adds new position', async () => {
    const newPos = { title: 'Backend Engineer', department_id: 'd1' }
    const created = { id: 'p2', ...newPos, status: 'draft', location: '', employment_type: 'full_time', headcount: 1, priority: 'medium', is_remote: false, description: '', requirements: [], benefits: [], required_skills: [], preferred_skills: [], education_requirement: null, experience_years_min: null, salary_min: null, salary_max: null, created_by: 'u1', created_at: '2026-01-02', updated_at: '2026-01-02' }
    mockFetch.mockReturnValue(mockResponse(created))
    const result = await store.createPosition(newPos as any)
    expect(result.title).toBe('Backend Engineer')
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/positions'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('updatePosition calls PATCH endpoint', async () => {
    mockFetch.mockReturnValue(mockResponse({ id: 'p1', status: 'closed' }))
    await store.updatePosition('p1', { status: 'closed' })
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/positions/p1'),
      expect.objectContaining({ method: 'PATCH' }),
    )
  })

  it('deletePosition calls DELETE endpoint', async () => {
    mockFetch.mockReturnValue(mockResponse({ ok: true }))
    await store.deletePosition('p1')
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/positions/p1'),
      expect.objectContaining({ method: 'DELETE' }),
    )
  })
})
