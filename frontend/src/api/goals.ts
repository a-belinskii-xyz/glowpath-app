import { apiRequest, getApiBaseUrl } from './client'
import { apiLocaleHeaders } from '../lib/locale'
import { ApiError, parseApiError } from '../lib/errors'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '../lib/storage'
import type { TokenResponse } from '../types/auth'
import type {
  GoalCalendarResponse,
  GoalIconListResponse,
  GoalIconPublic,
  GoalListResponse,
  GoalPatch,
  GoalPublic,
  GoalReorderRequest,
  GoalStatsResponse,
  GoalWrite,
} from '../types/goal'

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

export function listGoals(): Promise<GoalListResponse> {
  return apiRequest<GoalListResponse>('/v1/goals', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function createGoal(body: GoalWrite): Promise<GoalPublic> {
  return apiRequest<GoalPublic>('/v1/goals', {
    method: 'POST',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function patchGoal(goalId: string, body: GoalPatch): Promise<GoalPublic> {
  return apiRequest<GoalPublic>(`/v1/goals/${goalId}`, {
    method: 'PATCH',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function deleteGoal(goalId: string): Promise<void> {
  return apiRequest<void>(`/v1/goals/${goalId}`, {
    method: 'DELETE',
    auth: true,
  })
}

export function reorderGoals(body: GoalReorderRequest): Promise<GoalListResponse> {
  return apiRequest<GoalListResponse>('/v1/goals/reorder', {
    method: 'PUT',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function getGoalCalendar(params: {
  recorded_from: string
  recorded_to: string
}): Promise<GoalCalendarResponse> {
  const query = new URLSearchParams({
    recorded_from: params.recorded_from,
    recorded_to: params.recorded_to,
  })
  return apiRequest<GoalCalendarResponse>(`/v1/goals/calendar?${query}`, {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function getGoalStats(params: {
  recorded_from: string
  recorded_to: string
}): Promise<GoalStatsResponse> {
  const query = new URLSearchParams({
    recorded_from: params.recorded_from,
    recorded_to: params.recorded_to,
  })
  return apiRequest<GoalStatsResponse>(`/v1/goals/stats?${query}`, {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function getGoalIcons(goalId: string): Promise<GoalIconListResponse> {
  return apiRequest<GoalIconListResponse>(`/v1/goals/${goalId}/icons`, {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function getGoalIconUrl(iconId: string): string {
  return `${getApiBaseUrl()}/v1/goals/icons/id/${iconId}`
}

export function getGoalIconSourceUrl(iconId: string): string {
  return `${getApiBaseUrl()}/v1/goals/icons/id/${iconId}/source`
}

export async function fetchGoalIconBlob(
  iconId: string,
  retryOnUnauthorized = true,
): Promise<Blob> {
  const headers: Record<string, string> = { Accept: '*/*' }
  const accessToken = getAccessToken()
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  const response = await fetch(getGoalIconUrl(iconId), {
    method: 'GET',
    headers,
  })

  if (response.status === 401 && retryOnUnauthorized) {
    const refreshed = await refreshTokensOnce()
    if (refreshed) {
      return fetchGoalIconBlob(iconId, false)
    }
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(parseApiError(response.status, payload), response.status)
  }

  return response.blob()
}

export async function fetchGoalIconSourceBlob(
  iconId: string,
  retryOnUnauthorized = true,
): Promise<Blob> {
  const headers: Record<string, string> = { Accept: '*/*' }
  const accessToken = getAccessToken()
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  const response = await fetch(getGoalIconSourceUrl(iconId), {
    method: 'GET',
    headers,
  })

  if (response.status === 401 && retryOnUnauthorized) {
    const refreshed = await refreshTokensOnce()
    if (refreshed) {
      return fetchGoalIconSourceBlob(iconId, false)
    }
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(parseApiError(response.status, payload), response.status)
  }

  return response.blob()
}

export async function uploadGoalIcon(
  goalId: string,
  file: File,
  source?: File | null,
): Promise<GoalIconPublic> {
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

  const response = await fetch(`${getApiBaseUrl()}/v1/goals/${goalId}/icons`, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (response.status === 401) {
    const refreshed = await refreshTokensOnce()
    if (refreshed) {
      return uploadGoalIcon(goalId, file, source)
    }
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(parseApiError(response.status, payload), response.status)
  }

  return payload as GoalIconPublic
}

export function deleteGoalIcon(iconId: string): Promise<void> {
  return apiRequest<void>(`/v1/goals/icons/id/${iconId}`, {
    method: 'DELETE',
    auth: true,
    headers: apiLocaleHeaders(),
  })
}
