// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

import { hrGet, hrPost, hrPut, hrPatch, hrDelete } from '../../packages/client/src/api/hr/client'

describe('HR API Client', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    localStorage.setItem('hermes_api_key', 'test-key')
  })

  function mockResponse(data: unknown, ok = true, status = 200) {
    return Promise.resolve({
      ok,
      status,
      json: () => Promise.resolve(data),
      text: () => Promise.resolve(JSON.stringify(data)),
      headers: new Headers({ 'content-type': 'application/json' }),
    })
  }

  it('hrGet sends GET request with auth headers', async () => {
    mockFetch.mockReturnValue(mockResponse({ items: [], total: 0 }))
    const result = await hrGet('/positions')
    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/positions')
    expect(opts.headers.Authorization).toBe('Bearer test-key')
    expect(opts.headers['Content-Type']).toBe('application/json')
    expect(result).toEqual({ items: [], total: 0 })
  })

  it('hrPost sends POST request with JSON body', async () => {
    const body = { title: 'Senior Engineer' }
    mockFetch.mockReturnValue(mockResponse({ id: '1', ...body }))
    await hrPost('/positions', body)
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/positions'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(body),
      }),
    )
  })

  it('hrPatch sends PATCH request', async () => {
    mockFetch.mockReturnValue(mockResponse({ id: '1', status: 'closed' }))
    await hrPatch('/positions/1', { status: 'closed' })
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/positions/1'),
      expect.objectContaining({ method: 'PATCH' }),
    )
  })

  it('hrDelete sends DELETE request', async () => {
    mockFetch.mockReturnValue(mockResponse({ ok: true }))
    await hrDelete('/positions/1')
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/positions/1'),
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('hrGet includes query params', async () => {
    mockFetch.mockReturnValue(mockResponse({ items: [] }))
    await hrGet('/positions', { status: 'open', page: '1' })
    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain('status=open')
    expect(url).toContain('page=1')
  })

  it('hrGet throws on non-ok response', async () => {
    mockFetch.mockReturnValue(mockResponse({ detail: 'Not found' }, false, 404))
    await expect(hrGet('/positions/999')).rejects.toThrow()
  })
})
