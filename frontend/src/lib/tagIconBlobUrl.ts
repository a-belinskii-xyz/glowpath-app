import { fetchTagIconBlob } from '../api/tagGroups'

const blobUrlCache = new Map<string, string>()
const blobUrlInflight = new Map<string, Promise<string>>()

export function getCachedTagIconObjectUrl(iconId: string): string | null {
  return blobUrlCache.get(iconId) ?? null
}

export async function getTagIconObjectUrl(iconId: string): Promise<string> {
  const cached = blobUrlCache.get(iconId)
  if (cached) {
    return cached
  }

  const inflight = blobUrlInflight.get(iconId)
  if (inflight) {
    return inflight
  }

  const request = fetchTagIconBlob(iconId)
    .then((blob) => {
      const objectUrl = URL.createObjectURL(blob)
      blobUrlCache.set(iconId, objectUrl)
      blobUrlInflight.delete(iconId)
      return objectUrl
    })
    .catch((error) => {
      blobUrlInflight.delete(iconId)
      throw error
    })

  blobUrlInflight.set(iconId, request)
  return request
}

export function revokeTagIconObjectUrl(iconId: string): void {
  const cached = blobUrlCache.get(iconId)
  if (cached) {
    URL.revokeObjectURL(cached)
    blobUrlCache.delete(iconId)
  }
  blobUrlInflight.delete(iconId)
}
