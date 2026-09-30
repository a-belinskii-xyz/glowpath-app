/** System share sheet for files (Web Share API level 2), with a download fallback. */

export type ShareFileResult = 'shared' | 'cancelled'

export function canShareFile(file: File): boolean {
  if (typeof navigator === 'undefined' || typeof navigator.share !== 'function') {
    return false
  }
  try {
    return typeof navigator.canShare === 'function' && navigator.canShare({ files: [file] })
  } catch {
    return false
  }
}

/** Must run inside a user gesture (a click handler), or Safari rejects it. */
export async function shareFile(file: File, title?: string): Promise<ShareFileResult> {
  try {
    await navigator.share(title ? { files: [file], title } : { files: [file] })
    return 'shared'
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      return 'cancelled'
    }
    throw error
  }
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 10_000)
}
