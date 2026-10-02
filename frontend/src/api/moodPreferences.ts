import { apiRequest, getApiBaseUrl } from './client'
import { apiLocaleHeaders, getApiLocale } from '../lib/locale'
import { isGuestDiaryMode } from '../lib/guestMode'
import * as guestStore from '../guest/store'
import { ApiError, parseApiError } from '../lib/errors'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '../lib/storage'
import type { TokenResponse } from '../types/auth'
import type { MoodPreferencesPublic, MoodPreferencesUpdate } from '../types/moodPreferences'

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

export type MoodIconPublic = {
  id: string
  score: number
  mime_type: string
  size_bytes: number
  original_name: string
  has_source: boolean
  preferences: MoodPreferencesPublic
}

export type MoodIconMeta = {
  id: string
  score: number
  mime_type: string
  size_bytes: number
  original_name: string
  has_source: boolean
}

export type MoodIconListResponse = {
  items: MoodIconMeta[]
  max_per_score: number
}

export type BuiltinMoodIconPublic = {
  slug: string
  label: string
  asset_path: string
  suggested_score: number | null
  default_score: number | null
}

export type MoodIconCatalogResponse = {
  items: BuiltinMoodIconPublic[]
}

export function getMoodPreferences(): Promise<MoodPreferencesPublic> {
  if (isGuestDiaryMode()) {
    return guestStore.getGuestMoodPreferences(getApiLocale())
  }
  return apiRequest<MoodPreferencesPublic>('/v1/mood-preferences', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function patchMoodPreferences(
  body: MoodPreferencesUpdate,
): Promise<MoodPreferencesPublic> {
  if (isGuestDiaryMode()) {
    return guestStore.patchGuestMoodPreferences(body, getApiLocale())
  }
  return apiRequest<MoodPreferencesPublic>('/v1/mood-preferences', {
    method: 'PATCH',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function getMoodIconCatalog(): Promise<MoodIconCatalogResponse> {
  return apiRequest<MoodIconCatalogResponse>('/v1/mood-preferences/icon-catalog', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function getMoodIcons(score?: number): Promise<MoodIconListResponse> {
  const query = score === undefined ? '' : `?score=${score}`
  return apiRequest<MoodIconListResponse>(`/v1/mood-preferences/icons${query}`, {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function getMoodIconUrl(iconId: string): string {
  return `${getApiBaseUrl()}/v1/mood-preferences/icons/id/${iconId}`
}

export function getMoodIconSourceUrl(iconId: string): string {
  return `${getApiBaseUrl()}/v1/mood-preferences/icons/id/${iconId}/source`
}

export async function fetchMoodIconBlob(
  iconId: string,
  retryOnUnauthorized = true,
): Promise<Blob> {
  const headers: Record<string, string> = { Accept: '*/*' }
  const accessToken = getAccessToken()
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  const response = await fetch(getMoodIconUrl(iconId), {
    method: 'GET',
    headers,
  })

  if (response.status === 401 && retryOnUnauthorized) {
    const refreshed = await refreshTokensOnce()
    if (refreshed) {
      return fetchMoodIconBlob(iconId, false)
    }
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(parseApiError(response.status, payload), response.status)
  }

  return response.blob()
}

export async function fetchMoodIconSourceBlob(
  iconId: string,
  retryOnUnauthorized = true,
): Promise<Blob> {
  const headers: Record<string, string> = { Accept: '*/*' }
  const accessToken = getAccessToken()
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  const response = await fetch(getMoodIconSourceUrl(iconId), {
    method: 'GET',
    headers,
  })

  if (response.status === 401 && retryOnUnauthorized) {
    const refreshed = await refreshTokensOnce()
    if (refreshed) {
      return fetchMoodIconSourceBlob(iconId, false)
    }
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(parseApiError(response.status, payload), response.status)
  }

  return response.blob()
}

export async function uploadMoodIcon(
  score: number,
  file: File,
  source?: File | null,
): Promise<MoodIconPublic> {
  const formData = new FormData()
  formData.append('file', file)
  if (source) {
    formData.append('source', source)
  }

  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...apiLocaleHeaders(),
  }
  const accessToken = getAccessToken()
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  const response = await fetch(`${getApiBaseUrl()}/v1/mood-preferences/icons/${score}`, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (response.status === 401) {
    const refreshed = await refreshTokensOnce()
    if (refreshed) {
      return uploadMoodIcon(score, file, source)
    }
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(parseApiError(response.status, payload), response.status)
  }

  return payload as MoodIconPublic
}

export function deleteMoodIcon(iconId: string): Promise<void> {
  return apiRequest<void>(`/v1/mood-preferences/icons/id/${iconId}`, {
    method: 'DELETE',
    auth: true,
    headers: apiLocaleHeaders(),
  })
}
