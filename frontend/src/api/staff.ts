import { apiRequest, authorizedFetch } from './client'
import { filenameFromDisposition } from '../lib/download'
import { apiLocaleHeaders } from '../lib/locale'
import type {
  CriteriaSpec,
  StaffAchievementCreate,
  StaffAchievementPatch,
  StaffAchievementPublic,
} from '../types/achievement'
import type { PackDetailPublic, WalletLedgerListResponse } from '../types/marketplace'
import type {
  PresetExportParams,
  PresetImportResponse,
  StaffMetricsResponse,
  StaffPackCreate,
  StaffUserListResponse,
} from '../types/staff'

export function getStaffMetrics(): Promise<StaffMetricsResponse> {
  return apiRequest<StaffMetricsResponse>('/v1/staff/metrics', { auth: true })
}

export function searchStaffUsers(q: string, limit = 20): Promise<StaffUserListResponse> {
  const query = new URLSearchParams({ limit: String(limit) })
  if (q.trim()) {
    query.set('q', q.trim())
  }
  return apiRequest<StaffUserListResponse>(`/v1/staff/users?${query}`, { auth: true })
}

export function getStaffUserLedger(userId: string, limit = 10): Promise<WalletLedgerListResponse> {
  return apiRequest<WalletLedgerListResponse>(
    `/v1/staff/users/${userId}/ledger?limit=${limit}`,
    { auth: true },
  )
}

export function createStaffPack(body: StaffPackCreate): Promise<PackDetailPublic> {
  return apiRequest<PackDetailPublic>('/v1/staff/packs', {
    method: 'POST',
    auth: true,
    body,
    headers: apiLocaleHeaders(),
  })
}

export function setStaffPackSort(packId: string, sortOrder: number): Promise<PackDetailPublic> {
  return apiRequest<PackDetailPublic>(`/v1/staff/packs/${packId}/sort`, {
    method: 'PATCH',
    auth: true,
    body: { sort_order: sortOrder },
    headers: apiLocaleHeaders(),
  })
}

export function archiveStaffPack(packId: string): Promise<PackDetailPublic> {
  return apiRequest<PackDetailPublic>(`/v1/staff/packs/${packId}/archive`, {
    method: 'POST',
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

/** Download the preset zip and return it with the server-suggested filename. */
export async function downloadPresetExport(
  params: PresetExportParams,
): Promise<{ blob: Blob; filename: string }> {
  const query = new URLSearchParams({
    include_achievements: String(params.includeAchievements),
  })
  for (const id of params.packIds) {
    query.append('pack_id', id)
  }
  const response = await authorizedFetch(`/v1/staff/presets/export?${query}`)
  return {
    blob: await response.blob(),
    filename: filenameFromDisposition(
      response.headers.get('Content-Disposition'),
      'glowpath-preset.zip',
    ),
  }
}

export async function importPreset(file: File): Promise<PresetImportResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await authorizedFetch('/v1/staff/presets/import', {
    method: 'POST',
    body: formData,
    headers: { Accept: 'application/json' },
  })
  return (await response.json()) as PresetImportResponse
}

export function listStaffAchievements(): Promise<{ items: StaffAchievementPublic[] }> {
  return apiRequest<{ items: StaffAchievementPublic[] }>('/v1/staff/achievements', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function listCriteriaSpecs(): Promise<{ items: CriteriaSpec[] }> {
  return apiRequest<{ items: CriteriaSpec[] }>('/v1/staff/achievements/criteria-types', {
    auth: true,
  })
}

export function createStaffAchievement(
  body: StaffAchievementCreate,
): Promise<StaffAchievementPublic> {
  return apiRequest<StaffAchievementPublic>('/v1/staff/achievements', {
    method: 'POST',
    auth: true,
    body,
    headers: apiLocaleHeaders(),
  })
}

export function patchStaffAchievement(
  achievementId: string,
  body: StaffAchievementPatch,
): Promise<StaffAchievementPublic> {
  return apiRequest<StaffAchievementPublic>(`/v1/staff/achievements/${achievementId}`, {
    method: 'PATCH',
    auth: true,
    body,
    headers: apiLocaleHeaders(),
  })
}

export async function uploadStaffAchievementIcon(
  achievementId: string,
  file: File,
): Promise<StaffAchievementPublic> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await authorizedFetch(`/v1/staff/achievements/${achievementId}/icon`, {
    method: 'PUT',
    body: formData,
    headers: { Accept: 'application/json' },
  })
  return (await response.json()) as StaffAchievementPublic
}
