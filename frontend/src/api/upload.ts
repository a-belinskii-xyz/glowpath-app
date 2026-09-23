import { ApiError, parseApiError } from '../lib/errors'
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '../lib/storage'
import type { AttachmentKind, AttachmentPublic } from '../types/mood'
import type { TokenResponse } from '../types/auth'
import { getApiBaseUrl } from './client'

let refreshPromise: Promise<boolean> | null = null

async function refreshTokens(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    return false
  }

  const response = await fetch(`${getApiBaseUrl()}/v1/auth/refresh`, {
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

async function uploadWithAuth(
  path: string,
  formData: FormData,
  retryOnUnauthorized = true,
): Promise<AttachmentPublic> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
  }

  const accessToken = getAccessToken()
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (response.status === 401 && retryOnUnauthorized) {
    const refreshed = await refreshTokensOnce()
    if (refreshed) {
      return uploadWithAuth(path, formData, false)
    }
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(parseApiError(response.status, payload), response.status)
  }

  return payload as AttachmentPublic
}

export function uploadAttachment(
  path: string,
  kind: AttachmentKind,
  file: File,
): Promise<AttachmentPublic> {
  const formData = new FormData()
  formData.set('kind', kind)
  formData.set('file', file)
  return uploadWithAuth(path, formData)
}
