/**
 * Public API Client for Token-based routes.
 *
 * Unlike the authenticated hrRequest, this client does NOT send
 * Authorization or X-Tenant-Id headers. Token-based endpoints
 * use JWT self-validation embedded in the URL token.
 */

const HR_API_BASE = '/api/v1'

export async function publicRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${HR_API_BASE}${path}`
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  const res = await fetch(url, { ...options, headers })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Public API Error ${res.status}: ${text || res.statusText}`)
  }

  if (res.status === 204) {
    return undefined as unknown as T
  }

  return res.json()
}

export async function publicGet<T>(path: string): Promise<T> {
  return publicRequest<T>(path)
}

export async function publicPost<T>(path: string, body?: unknown): Promise<T> {
  return publicRequest<T>(path, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  })
}
