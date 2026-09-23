import { fetchCatalogIconBlob } from '../api/marketplace'

const blobUrlCache = new Map<string, string>()
const blobUrlInflight = new Map<string, Promise<string>>()

export function getCachedCatalogIconObjectUrl(iconId: string): string | null {
  return blobUrlCache.get(iconId) ?? null
}

export async function getCatalogIconObjectUrl(iconId: string): Promise<string> {
  const cached = blobUrlCache.get(iconId)
  if (cached) {
    return cached
  }

  const inflight = blobUrlInflight.get(iconId)
  if (inflight) {
    return inflight
  }

  const request = fetchCatalogIconBlob(iconId)
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

export function revokeCatalogIconObjectUrl(iconId: string): void {
  const cached = blobUrlCache.get(iconId)
  if (cached) {
    URL.revokeObjectURL(cached)
    blobUrlCache.delete(iconId)
  }
}
