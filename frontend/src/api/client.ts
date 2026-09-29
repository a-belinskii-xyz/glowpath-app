import { ApiError, parseApiError } from '../lib/errors'
import { apiLocaleHeaders } from '../lib/locale'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '../lib/storage'
import type { TokenResponse } from '../types/auth'

// Dev: hit API on :8000. Prod / nginx image: same-origin (empty) so /v1 is proxied.
const configured = import.meta.env.VITE_API_BASE_URL
const API_BASE_URL =
  configured === ''
    ? ''
    : configured || (import.meta.env.DEV ? 'http://localhost:8000' : '')

type RequestOptions = {
  method?: string
  body?: unknown
  auth?: boolean
  retryOnUnauthorized?: boolean
  headers?: Record<string, string>
}

let refreshPromise: Promise<boolean> | null = null

async function refreshTokens(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    return false
  }

  const response = await fetch(`${API_BASE_URL}/v1/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })

  if (!response.ok) {
    clearTokens()
    return false
  }

  const tokens = (await response.json()) as TokenResponse
  setTokens(tokens.access_token, tokens.refresh_token)
  return true
}

async function refreshTokensOnce(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = refreshTokens().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

export function getApiBaseUrl(): string {
  return API_BASE_URL
}

/**
 * Authenticated fetch for non-JSON bodies (FormData uploads, file downloads).
 * Retries once after a token refresh; throws ApiError on non-2xx responses.
 */
export async function authorizedFetch(
  path: string,
  init: { method?: string; body?: BodyInit; headers?: Record<string, string> } = {},
  retryOnUnauthorized = true,
): Promise<Response> {
  const headers: Record<string, string> = { ...apiLocaleHeaders(), ...init.headers }
  const accessToken = getAccessToken()
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: init.method ?? 'GET',
    headers,
    body: init.body,
  })
  if (response.status === 401 && retryOnUnauthorized) {
    const refreshed = await refreshTokensOnce()
    if (refreshed) {
      return authorizedFetch(path, init, false)
    }
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(parseApiError(response.status, payload), response.status)
  }
  return response
}

export async function apiRequest<T>(
  path: string,
  { method = 'GET', body, auth = false, retryOnUnauthorized = true, headers: extraHeaders }: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...apiLocaleHeaders(),
    ...extraHeaders,
  }

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  if (auth) {
    const accessToken = getAccessToken()
    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    credentials: 'include',
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (response.status === 401 && auth && retryOnUnauthorized) {
    const refreshed = await refreshTokensOnce()
    if (refreshed) {
      return apiRequest<T>(path, { method, body, auth, retryOnUnauthorized: false, headers: extraHeaders })
    }
  }

  if (response.status === 204) {
    return undefined as T
  }

  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    throw new ApiError(parseApiError(response.status, payload), response.status)
  }

  return payload as T
}
