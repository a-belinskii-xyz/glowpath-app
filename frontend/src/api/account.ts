import { apiRequest, authorizedFetch } from './client'
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
