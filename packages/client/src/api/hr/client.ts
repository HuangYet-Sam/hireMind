/**
 * HireMind Recruitment API Client
 *
 * Direct connection to FastAPI backend on port 8000.
 * Separate from the Hermes BFF (Koa :8648) used by the admin panel.
 */

const HR_API_BASE = 'http://127.0.0.1:8000/api/v1'

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('hermes_api_key') || ''
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const tenantId = localStorage.getItem('hr_tenant_id')
  if (tenantId) {
    headers['X-Tenant-Id'] = tenantId
  }
  return headers
}

export interface ApiResponse<T> {
  data: T
  message?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export async function hrRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${HR_API_BASE}${path}`
  const headers = {
    ...getAuthHeaders(),
    ...options.headers as Record<string, string>,
  }

  const res = await fetch(url, { ...options, headers })

  if (res.status === 401) {
    console.error('[HR API] Unauthorized')
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HR API Error ${res.status}: ${text || res.statusText}`)
  }

  if (res.status === 204) {
    return undefined as unknown as T
  }

  return res.json()
}

/** GET request with optional query params */
export async function hrGet<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  let url = path
  if (params) {
    const filtered = Object.entries(params).filter(([, v]) => v !== undefined)
    if (filtered.length > 0) {
      const qs = new URLSearchParams(
        filtered.map(([k, v]) => [k, String(v)])
      ).toString()
      url += `?${qs}`
    }
  }
  return hrRequest<T>(url)
}

/** POST request */
export async function hrPost<T>(path: string, body?: unknown): Promise<T> {
  return hrRequest<T>(path, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  })
}

/** PUT request */
export async function hrPut<T>(path: string, body?: unknown): Promise<T> {
  return hrRequest<T>(path, {
    method: 'PUT',
    body: body ? JSON.stringify(body) : undefined,
  })
}

/** PATCH request */
export async function hrPatch<T>(path: string, body?: unknown): Promise<T> {
  return hrRequest<T>(path, {
    method: 'PATCH',
    body: body ? JSON.stringify(body) : undefined,
  })
}

/** DELETE request */
export async function hrDelete<T = { ok: boolean }>(path: string): Promise<T> {
  return hrRequest<T>(path, { method: 'DELETE' })
}
