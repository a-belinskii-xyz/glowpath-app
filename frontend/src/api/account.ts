import { apiRequest, authorizedFetch } from './client'
import type { DiaryRestore } from '../types/restore'
import { filenameFromDisposition } from '../lib/download'

/** Download the full diary export (ZIP with JSON, CSV and attachments). */
export async function downloadAccountExport(): Promise<{ blob: Blob; filename: string }> {
  const response = await authorizedFetch('/v1/account/export')
  return {
    blob: await response.blob(),
    filename: filenameFromDisposition(
      response.headers.get('Content-Disposition'),
      'glowpath-export.zip',
    ),
  }
}

/** Permanently delete the signed-in account and all of its data. */
export function deleteAccount(): Promise<void> {
  return apiRequest<void>('/v1/account', { method: 'DELETE', auth: true, body: { confirm: true } })
}

/** Ask the bot to send the export into the user's Telegram chat; returns how many files were sent. */
export function sendAccountExportToTelegram(): Promise<{ parts: number }> {
  return apiRequest<{ parts: number }>('/v1/account/export/telegram', { method: 'POST', auth: true })
}

async function uploadRestoreFiles(path: string, files: File[]): Promise<DiaryRestore> {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }
  const response = await authorizedFetch(path, {
    method: 'POST',
    body: formData,
    headers: { Accept: 'application/json' },
  })
  return (await response.json()) as DiaryRestore
}

/** Upload export ZIP part(s) and get a preview; the diary does not change yet. */
export function startDiaryRestore(files: File[]): Promise<DiaryRestore> {
  return uploadRestoreFiles('/v1/account/restores', files)
}

/** Add more ZIP parts (photos and voice notes) to a preview. */
export function addDiaryRestoreParts(restoreId: string, files: File[]): Promise<DiaryRestore> {
  return uploadRestoreFiles(`/v1/account/restores/${restoreId}/parts`, files)
}

export function applyDiaryRestore(restoreId: string): Promise<DiaryRestore> {
  return apiRequest<DiaryRestore>(`/v1/account/restores/${restoreId}/apply`, {
    method: 'POST',
    auth: true,
  })
}

export function cancelDiaryRestore(restoreId: string): Promise<DiaryRestore> {
  return apiRequest<DiaryRestore>(`/v1/account/restores/${restoreId}/cancel`, {
    method: 'POST',
    auth: true,
  })
}
