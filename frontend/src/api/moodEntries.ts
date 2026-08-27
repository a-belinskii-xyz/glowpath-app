import { ApiError, parseApiError } from '../lib/errors'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '../lib/storage'
import { apiLocaleHeaders } from '../lib/locale'
import type { TokenResponse } from '../types/auth'
import type {
  AttachmentKind,
  AttachmentPublic,
  ListMoodEntriesParams,
  MoodEntryCalendarResponse,
  MoodEntryCreate,
  MoodEntryListResponse,
  MoodEntryPatch,
  MoodEntryPublic,
  MoodEntryStatsResponse,
  MoodEntryStreakResponse,
  MoodInsightsResponse,
  GalleryPhotoListResponse,
  SearchMoodEntriesParams,
} from '../types/mood'
import { apiRequest, getApiBaseUrl } from './client'
import { uploadAttachment } from './upload'

let refreshPromise: Promise<boolean> | null = null

async function refreshTokensOnce(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
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
    })().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

function moodHeaders(): Record<string, string> {
  return apiLocaleHeaders()
}

function buildListQuery(params: ListMoodEntriesParams = {}): string {
  const search = new URLSearchParams()
  if (params.limit !== undefined) {
    search.set('limit', String(params.limit))
  }
  if (params.offset !== undefined) {
    search.set('offset', String(params.offset))
  }
  if (params.recorded_from) {
    search.set('recorded_from', params.recorded_from)
  }
  if (params.recorded_to) {
    search.set('recorded_to', params.recorded_to)
  }
  if (params.is_favorite !== undefined) {
    search.set('is_favorite', String(params.is_favorite))
  }
  const query = search.toString()
  return query ? `?${query}` : ''
}

export function listMoodEntries(params: ListMoodEntriesParams = {}): Promise<MoodEntryListResponse> {
  return apiRequest<MoodEntryListResponse>(`/v1/mood-entries${buildListQuery(params)}`, {
    auth: true,
    headers: moodHeaders(),
  })
}

export function listGalleryPhotos(params: { limit?: number; offset?: number } = {}): Promise<GalleryPhotoListResponse> {
  return apiRequest<GalleryPhotoListResponse>(`/v1/mood-entries/photos${buildListQuery(params)}`, {
    auth: true,
    headers: moodHeaders(),
  })
}

export function searchMoodEntries(
  params: SearchMoodEntriesParams,
): Promise<MoodEntryListResponse> {
  const search = new URLSearchParams()
  search.set('q', params.q)
  if (params.limit !== undefined) {
    search.set('limit', String(params.limit))
  }
  return apiRequest<MoodEntryListResponse>(`/v1/mood-entries/search?${search.toString()}`, {
    auth: true,
    headers: moodHeaders(),
  })
}

export function getMoodEntryCalendar(params: {
  recorded_from: string
  recorded_to: string
}): Promise<MoodEntryCalendarResponse> {
  return apiRequest<MoodEntryCalendarResponse>(`/v1/mood-entries/calendar${buildListQuery(params)}`, {
    auth: true,
    headers: moodHeaders(),
  })
}

export function getMoodEntryStreak(): Promise<MoodEntryStreakResponse> {
  return apiRequest<MoodEntryStreakResponse>('/v1/mood-entries/streak', {
    auth: true,
    headers: moodHeaders(),
  })
}

export function getMoodEntryStats(params: {
  recorded_from: string
  recorded_to: string
}): Promise<MoodEntryStatsResponse> {
  return apiRequest<MoodEntryStatsResponse>(`/v1/mood-entries/stats${buildListQuery(params)}`, {
    auth: true,
    headers: moodHeaders(),
  })
}

export function getMoodInsights(params: {
  recorded_from?: string
  recorded_to?: string
  limit?: number
  focus_entry_id?: string
} = {}): Promise<MoodInsightsResponse> {
  const search = new URLSearchParams()
  if (params.recorded_from) {
    search.set('recorded_from', params.recorded_from)
  }
  if (params.recorded_to) {
    search.set('recorded_to', params.recorded_to)
  }
  if (params.limit !== undefined) {
    search.set('limit', String(params.limit))
  }
  if (params.focus_entry_id) {
    search.set('focus_entry_id', params.focus_entry_id)
  }
  const query = search.toString()
  return apiRequest<MoodInsightsResponse>(
    `/v1/mood-entries/insights${query ? `?${query}` : ''}`,
    {
      auth: true,
      headers: moodHeaders(),
    },
  )
}

export function getMoodEntry(entryId: string): Promise<MoodEntryPublic> {
  return apiRequest<MoodEntryPublic>(`/v1/mood-entries/${entryId}`, {
    auth: true,
    headers: moodHeaders(),
  })
}

export function createMoodEntry(body: MoodEntryCreate): Promise<MoodEntryPublic> {
  return apiRequest<MoodEntryPublic>('/v1/mood-entries', {
    method: 'POST',
    body,
    auth: true,
    headers: moodHeaders(),
  })
}

export function patchMoodEntry(entryId: string, body: MoodEntryPatch): Promise<MoodEntryPublic> {
  return apiRequest<MoodEntryPublic>(`/v1/mood-entries/${entryId}`, {
    method: 'PATCH',
    body,
    auth: true,
    headers: moodHeaders(),
  })
}

export function deleteMoodEntry(entryId: string): Promise<void> {
  return apiRequest<void>(`/v1/mood-entries/${entryId}`, {
    method: 'DELETE',
    auth: true,
    headers: moodHeaders(),
  })
}

export function reorderMoodEntryAttachments(
  entryId: string,
  orderedIds: string[],
): Promise<AttachmentPublic[]> {
  return apiRequest<AttachmentPublic[]>(`/v1/mood-entries/${entryId}/attachments/reorder`, {
    method: 'PUT',
    auth: true,
    headers: moodHeaders(),
    body: { ordered_ids: orderedIds },
  })
}

export function uploadMoodEntryAttachment(
  entryId: string,
  kind: AttachmentKind,
  file: File,
): Promise<AttachmentPublic> {
  return uploadAttachment(`/v1/mood-entries/${entryId}/attachments`, kind, file)
}

export function deleteMoodEntryAttachment(entryId: string, attachmentId: string): Promise<void> {
  return apiRequest<void>(`/v1/mood-entries/${entryId}/attachments/${attachmentId}`, {
    method: 'DELETE',
    auth: true,
    headers: moodHeaders(),
  })
}

export function getMoodEntryAttachmentUrl(entryId: string, attachmentId: string): string {
  return `${getApiBaseUrl()}/v1/mood-entries/${entryId}/attachments/${attachmentId}`
}

export async function fetchMoodEntryAttachmentBlob(
  entryId: string,
  attachmentId: string,
  retryOnUnauthorized = true,
): Promise<Blob> {
  const headers: Record<string, string> = { Accept: '*/*' }
  const accessToken = getAccessToken()
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  const response = await fetch(getMoodEntryAttachmentUrl(entryId, attachmentId), {
    method: 'GET',
    headers,
  })

  if (response.status === 401 && retryOnUnauthorized) {
    const refreshed = await refreshTokensOnce()
    if (refreshed) {
      return fetchMoodEntryAttachmentBlob(entryId, attachmentId, false)
    }
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(parseApiError(response.status, payload), response.status)
  }

  return response.blob()
}
