import { apiRequest, getApiBaseUrl } from './client'
import { apiLocaleHeaders } from '../lib/locale'
import { ApiError, parseApiError } from '../lib/errors'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '../lib/storage'
import type { TokenResponse } from '../types/auth'
import type {
  CatalogIconPublic,
  CatalogIconWithPackPublic,
  IconCrop,
  IconListResponse,
  ListIconsParams,
  ListPacksParams,
  PackDetailPublic,
  PackListResponse,
  PackUnlockListResponse,
  PackUnlockPublic,
  RejectPackBody,
  SearchTagCreate,
  SearchTagListResponse,
  SearchTagPatch,
  SearchTagPublic,
  StudioIconPatch,
  StudioPackCreate,
  StudioPackPatch,
  UploadStudioIconFields,
} from '../types/marketplace'

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

function toQuery(params: Record<string, string | number | boolean | undefined>): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined) {
      continue
    }
    query.set(key, String(value))
  }
  const encoded = query.toString()
  return encoded ? `?${encoded}` : ''
}

export function getMarketplaceSearchTags(): Promise<SearchTagListResponse> {
  return apiRequest<SearchTagListResponse>('/v1/marketplace/search-tags', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function listMarketplacePacks(params: ListPacksParams = {}): Promise<PackListResponse> {
  return apiRequest<PackListResponse>(`/v1/marketplace/packs${toQuery(params)}`, {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function getMarketplacePack(packId: string): Promise<PackDetailPublic> {
  return apiRequest<PackDetailPublic>(`/v1/marketplace/packs/${packId}`, {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function unlockMarketplacePack(packId: string): Promise<PackUnlockPublic> {
  return apiRequest<PackUnlockPublic>(`/v1/marketplace/packs/${packId}/unlock`, {
    method: 'POST',
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function listMyPackUnlocks(): Promise<PackUnlockListResponse> {
  return apiRequest<PackUnlockListResponse>('/v1/marketplace/me/unlocks', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function listMarketplaceIcons(params: ListIconsParams = {}): Promise<IconListResponse> {
  const query = new URLSearchParams()
  if (params.q) {
    query.set('q', params.q)
  }
  if (params.pack_id) {
    query.set('pack_id', params.pack_id)
  }
  if (params.suggested_mood !== undefined) {
    query.set('suggested_mood', String(params.suggested_mood))
  }
  if (params.limit !== undefined) {
    query.set('limit', String(params.limit))
  }
  if (params.offset !== undefined) {
    query.set('offset', String(params.offset))
  }
  const tags = params.tag === undefined ? [] : Array.isArray(params.tag) ? params.tag : [params.tag]
  for (const tag of tags) {
    query.append('tag', tag)
  }
  const suffix = query.size > 0 ? `?${query}` : ''
  return apiRequest<IconListResponse>(`/v1/marketplace/icons${suffix}`, {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function getMarketplaceIcon(iconId: string): Promise<CatalogIconWithPackPublic> {
  return apiRequest<CatalogIconWithPackPublic>(`/v1/marketplace/icons/${iconId}`, {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function getCatalogIconImageUrl(iconId: string): string {
  return `${getApiBaseUrl()}/v1/marketplace/icons/${iconId}/image`
}

const ICON_CROP_HEADER = 'X-Icon-Crop'

function parseIconCropHeader(raw: string | null): IconCrop | null {
  if (!raw) return null
  const values = raw.split(',').map(Number)
  if (values.length !== 4 || values.some((value) => !Number.isFinite(value))) return null
  const [x, y, w, h] = values
  return w > 0 && h > 0 ? { x, y, w, h } : null
}

/** Original (uncropped) icon file plus the crop frame the server asks clients to show. */
export async function fetchCatalogIconBlob(
  iconId: string,
  retryOnUnauthorized = true,
): Promise<{ blob: Blob; crop: IconCrop | null }> {
  const headers: Record<string, string> = { Accept: '*/*' }
  const accessToken = getAccessToken()
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  const response = await fetch(getCatalogIconImageUrl(iconId), {
    method: 'GET',
    headers,
  })

  if (response.status === 401 && retryOnUnauthorized) {
    const refreshed = await refreshTokensOnce()
    if (refreshed) {
      return fetchCatalogIconBlob(iconId, false)
    }
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(parseApiError(response.status, payload), response.status)
  }

  return {
    blob: await response.blob(),
    crop: parseIconCropHeader(response.headers.get(ICON_CROP_HEADER)),
  }
}

export function createStudioPack(body: StudioPackCreate): Promise<PackDetailPublic> {
  return apiRequest<PackDetailPublic>('/v1/marketplace/studio/packs', {
    method: 'POST',
    auth: true,
    body,
    headers: apiLocaleHeaders(),
  })
}

export function patchStudioPack(packId: string, body: StudioPackPatch): Promise<PackDetailPublic> {
  return apiRequest<PackDetailPublic>(`/v1/marketplace/studio/packs/${packId}`, {
    method: 'PATCH',
    auth: true,
    body,
    headers: apiLocaleHeaders(),
  })
}

export function deleteStudioPack(packId: string): Promise<void> {
  return apiRequest<void>(`/v1/marketplace/studio/packs/${packId}`, {
    method: 'DELETE',
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

async function sendStudioMultipart(
  path: string,
  method: 'POST' | 'PUT',
  formData: FormData,
  retryOnUnauthorized = true,
): Promise<CatalogIconPublic> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...apiLocaleHeaders(),
  }
  const accessToken = getAccessToken()
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method,
    headers,
    body: formData,
  })

  if (response.status === 401 && retryOnUnauthorized) {
    const refreshed = await refreshTokensOnce()
    if (refreshed) {
      return sendStudioMultipart(path, method, formData, false)
    }
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(parseApiError(response.status, payload), response.status)
  }

  return payload as CatalogIconPublic
}

export function uploadStudioIcon(
  packId: string,
  file: File,
  fields: UploadStudioIconFields,
): Promise<CatalogIconPublic> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('labels', JSON.stringify(fields.labels))
  formData.append('suggested_colors', JSON.stringify(fields.suggested_colors))
  if (fields.suggested_mood_scores) {
    formData.append('suggested_mood_scores', JSON.stringify(fields.suggested_mood_scores))
  }
  if (fields.suggested_usage) {
    formData.append('suggested_usage', JSON.stringify(fields.suggested_usage))
  }
  if (fields.search_tag_slugs) {
    formData.append('search_tag_slugs', JSON.stringify(fields.search_tag_slugs))
  }
  if (fields.slug) {
    formData.append('slug', fields.slug)
  }
  return sendStudioMultipart(`/v1/marketplace/studio/packs/${packId}/icons`, 'POST', formData)
}

/** Swap the icon file; the server drops the crop frame because it no longer fits. */
export function replaceStudioIconImage(iconId: string, file: File): Promise<CatalogIconPublic> {
  const formData = new FormData()
  formData.append('file', file)
  return sendStudioMultipart(`/v1/marketplace/studio/icons/${iconId}/image`, 'PUT', formData)
}

export function reorderStudioIcons(packId: string, iconIds: string[]): Promise<PackDetailPublic> {
  return apiRequest<PackDetailPublic>(`/v1/marketplace/studio/packs/${packId}/icon-order`, {
    method: 'PUT',
    auth: true,
    body: { icon_ids: iconIds },
    headers: apiLocaleHeaders(),
  })
}

export function patchStudioIcon(iconId: string, body: StudioIconPatch): Promise<CatalogIconPublic> {
  return apiRequest<CatalogIconPublic>(`/v1/marketplace/studio/icons/${iconId}`, {
    method: 'PATCH',
    auth: true,
    body,
    headers: apiLocaleHeaders(),
  })
}

export function deleteStudioIcon(iconId: string): Promise<void> {
  return apiRequest<void>(`/v1/marketplace/studio/icons/${iconId}`, {
    method: 'DELETE',
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function submitStudioPack(packId: string): Promise<PackDetailPublic> {
  return apiRequest<PackDetailPublic>(`/v1/marketplace/studio/packs/${packId}/submit`, {
    method: 'POST',
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function listStaffPacks(params?: {
  status?: string
  limit?: number
  offset?: number
}): Promise<PackListResponse> {
  return apiRequest<PackListResponse>(
    `/v1/marketplace/staff/packs${toQuery({
      status: params?.status,
      limit: params?.limit,
      offset: params?.offset,
    })}`,
    {
      auth: true,
      headers: apiLocaleHeaders(),
    },
  )
}

export function publishStaffPack(packId: string): Promise<PackDetailPublic> {
  return apiRequest<PackDetailPublic>(`/v1/marketplace/staff/packs/${packId}/publish`, {
    method: 'POST',
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function rejectStaffPack(
  packId: string,
  body?: RejectPackBody,
): Promise<PackDetailPublic> {
  return apiRequest<PackDetailPublic>(`/v1/marketplace/staff/packs/${packId}/reject`, {
    method: 'POST',
    auth: true,
    body: body ?? {},
    headers: apiLocaleHeaders(),
  })
}

export function createStaffSearchTag(body: SearchTagCreate): Promise<SearchTagPublic> {
  return apiRequest<SearchTagPublic>('/v1/marketplace/staff/search-tags', {
    method: 'POST',
    auth: true,
    body,
    headers: apiLocaleHeaders(),
  })
}

export function patchStaffSearchTag(
  tagId: string,
  body: SearchTagPatch,
): Promise<SearchTagPublic> {
  return apiRequest<SearchTagPublic>(`/v1/marketplace/staff/search-tags/${tagId}`, {
    method: 'PATCH',
    auth: true,
    body,
    headers: apiLocaleHeaders(),
  })
}

export function deleteStaffSearchTag(tagId: string): Promise<void> {
  return apiRequest<void>(`/v1/marketplace/staff/search-tags/${tagId}`, {
    method: 'DELETE',
    auth: true,
    headers: apiLocaleHeaders(),
  })
}
