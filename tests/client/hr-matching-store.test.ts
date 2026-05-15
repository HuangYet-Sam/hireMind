// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

import { useMatchingStore } from '../../packages/client/src/stores/hr/matching'

function mockResponse(data: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
    headers: new Headers({ 'content-type': 'application/json' }),
  })
}

describe('Matching Store', () => {
  let store: ReturnType<typeof useMatchingStore>

  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('hermes_api_key', 'test-key')
    vi.clearAllMocks()
    setActivePinia(createPinia())
    store = useMatchingStore()
  })

  it('matchCandidatesForPosition populates matches', async () => {
    const matchData = {
      matches: [
        {
          id: 'm1',
          candidate_id: 'c1',
          candidate_name: 'Alice',
          position_id: 'p1',
          overall_score: 0.85,
          skill_score: 0.9,
          experience_score: 0.8,
          education_score: 0.75,
          suggestions: ['Strong React skills', 'Good culture fit'],
          created_at: '2026-01-15',
        },
        {
          id: 'm2',
          candidate_id: 'c2',
          candidate_name: 'Bob',
          position_id: 'p1',
          overall_score: 0.62,
          skill_score: 0.7,
          experience_score: 0.5,
          education_score: 0.65,
          suggestions: ['Needs more backend experience'],
          created_at: '2026-01-15',
        },
      ],
    }
    mockFetch.mockReturnValue(mockResponse(matchData))
    await store.matchCandidatesForPosition('p1')
    expect(store.matches).toHaveLength(2)
    expect(store.matches[0].candidate_name).toBe('Alice')
    expect(store.matches[0].overall_score).toBe(0.85)
    expect(store.loading).toBe(false)
  })

  it('matchCandidatesForPosition sets loading state', async () => {
    let loadingDuringCall = false
    mockFetch.mockImplementation(async () => {
      loadingDuringCall = store.loading
      return mockResponse([])
    })
    await store.matchCandidatesForPosition('p1')
    expect(loadingDuringCall).toBe(true)
    expect(store.loading).toBe(false)
  })

  it('matchCandidatesForPosition handles empty results', async () => {
    mockFetch.mockReturnValue(mockResponse({ matches: [] }))
    await store.matchCandidatesForPosition('p1')
    expect(store.matches).toHaveLength(0)
  })
})
