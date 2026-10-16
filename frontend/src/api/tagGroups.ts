import { apiRequest, getApiBaseUrl } from './client'
import { apiLocaleHeaders, getApiLocale } from '../lib/locale'
import { isGuestDiaryMode } from '../lib/guestMode'
import * as guestStore from '../guest/store'
import { ApiError, parseApiError } from '../lib/errors'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '../lib/storage'
import type { TokenResponse } from '../types/auth'
import type {
  QuickTagResponse,
  ReorderRequest,
  TagGroupListResponse,
  TagGroupPatch,
  TagGroupPublic,
  TagGroupWrite,
  TagIconListResponse,
  TagIconPublic,
  TagPatch,
  TagPublic,
  TagWrite,
} from '../types/tag'

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

export function listTagGroups(): Promise<TagGroupListResponse> {
  if (isGuestDiaryMode()) {
    return guestStore.listGuestTagGroups()
  }
  return apiRequest<TagGroupListResponse>('/v1/tag-groups', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function createTagGroup(body: TagGroupWrite): Promise<TagGroupPublic> {
  if (isGuestDiaryMode()) {
    return guestStore.createGuestTagGroup(body, getApiLocale())
  }
  return apiRequest<TagGroupPublic>('/v1/tag-groups', {
    method: 'POST',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function patchTagGroup(groupId: string, body: TagGroupPatch): Promise<TagGroupPublic> {
  if (isGuestDiaryMode()) {
    return guestStore.patchGuestTagGroup(groupId, body, getApiLocale())
  }
  return apiRequest<TagGroupPublic>(`/v1/tag-groups/${groupId}`, {
    method: 'PATCH',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function deleteTagGroup(groupId: string): Promise<void> {
  if (isGuestDiaryMode()) {
    return guestStore.deleteGuestTagGroup(groupId)
  }
  return apiRequest<void>(`/v1/tag-groups/${groupId}`, {
    method: 'DELETE',
    auth: true,
  })
}

export function reorderTagGroups(body: ReorderRequest): Promise<TagGroupListResponse> {
  if (isGuestDiaryMode()) {
    return guestStore.reorderGuestTagGroups(body.ordered_ids)
  }
  return apiRequest<TagGroupListResponse>('/v1/tag-groups/reorder', {
    method: 'PUT',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function createTag(groupId: string, body: TagWrite): Promise<TagPublic> {
  if (isGuestDiaryMode()) {
    return guestStore.createGuestTag(groupId, body, getApiLocale())
  }
  return apiRequest<TagPublic>(`/v1/tag-groups/${groupId}/tags`, {
    method: 'POST',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

/** Tag typed in an entry: the user's tag with this name, or a new one in «New tags». */
export function quickCreateTag(label: string): Promise<QuickTagResponse> {
  if (isGuestDiaryMode()) {
    return guestStore.quickCreateGuestTag(label, getApiLocale())
  }
  return apiRequest<QuickTagResponse>('/v1/tag-groups/quick-tag', {
    method: 'POST',
    auth: true,
    headers: apiLocaleHeaders(),
    body: { label },
  })
}

export function patchTag(groupId: string, tagId: string, body: TagPatch): Promise<TagPublic> {
  if (isGuestDiaryMode()) {
    return guestStore.patchGuestTag(groupId, tagId, body, getApiLocale())
  }
  return apiRequest<TagPublic>(`/v1/tag-groups/${groupId}/tags/${tagId}`, {
    method: 'PATCH',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function deleteTag(groupId: string, tagId: string): Promise<void> {
  if (isGuestDiaryMode()) {
    return guestStore.deleteGuestTag(groupId, tagId)
  }
  return apiRequest<void>(`/v1/tag-groups/${groupId}/tags/${tagId}`, {
    method: 'DELETE',
    auth: true,
  })
}

export function reorderTags(groupId: string, body: ReorderRequest): Promise<TagGroupPublic> {
  if (isGuestDiaryMode()) {
    return guestStore.reorderGuestTags(groupId, body.ordered_ids)
  }
  return apiRequest<TagGroupPublic>(`/v1/tag-groups/${groupId}/tags/reorder`, {
    method: 'PUT',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function getTagIcons(groupId: string, tagId: string): Promise<TagIconListResponse> {
  return apiRequest<TagIconListResponse>(`/v1/tag-groups/${groupId}/tags/${tagId}/icons`, {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function getTagIconUrl(iconId: string): string {
  return `${getApiBaseUrl()}/v1/tag-groups/icons/id/${iconId}`
}

export function getTagIconSourceUrl(iconId: string): string {
  return `${getApiBaseUrl()}/v1/tag-groups/icons/id/${iconId}/source`
}

export async function fetchTagIconBlob(
  iconId: string,
  retryOnUnauthorized = true,
): Promise<Blob> {
  const headers: Record<string, string> = { Accept: '*/*' }
  const accessToken = getAccessToken()
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  const response = await fetch(getTagIconUrl(iconId), {
    method: 'GET',
    headers,
  })

  if (response.status === 401 && retryOnUnauthorized) {
    const refreshed = await refreshTokensOnce()
    if (refreshed) {
      return fetchTagIconBlob(iconId, false)
    }
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(parseApiError(response.status, payload), response.status)
  }

  return response.blob()
}

export async function fetchTagIconSourceBlob(
  iconId: string,
  retryOnUnauthorized = true,
): Promise<Blob> {
  const headers: Record<string, string> = { Accept: '*/*' }
  const accessToken = getAccessToken()
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  const response = await fetch(getTagIconSourceUrl(iconId), {
    method: 'GET',
    headers,
  })

  if (response.status === 401 && retryOnUnauthorized) {
    const refreshed = await refreshTokensOnce()
    if (refreshed) {
      return fetchTagIconSourceBlob(iconId, false)
    }
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(parseApiError(response.status, payload), response.status)
  }

  return response.blob()
}

export async function uploadTagIcon(
  groupId: string,
  tagId: string,
  file: File,
  source?: File | null,
): Promise<TagIconPublic> {
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

  const response = await fetch(`${getApiBaseUrl()}/v1/tag-groups/${groupId}/tags/${tagId}/icons`, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (response.status === 401) {
    const refreshed = await refreshTokensOnce()
    if (refreshed) {
      return uploadTagIcon(groupId, tagId, file, source)
    }
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(parseApiError(response.status, payload), response.status)
  }

  return payload as TagIconPublic
}

export function deleteTagIcon(iconId: string): Promise<void> {
  return apiRequest<void>(`/v1/tag-groups/icons/id/${iconId}`, {
    method: 'DELETE',
    auth: true,
    headers: apiLocaleHeaders(),
  })
}
