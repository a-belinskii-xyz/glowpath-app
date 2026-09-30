import { authorizedFetch } from './client'
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
