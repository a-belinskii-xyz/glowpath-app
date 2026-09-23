import { fetchMoodEntryAttachmentBlob } from '../api/moodEntries'

const blobUrlCache = new Map<string, string>()
const blobUrlInflight = new Map<string, Promise<string>>()

function cacheKey(entryId: string, attachmentId: string): string {
  return `${entryId}:${attachmentId}`
}

export function getCachedAttachmentObjectUrl(
  entryId: string,
  attachmentId: string,
): string | null {
  return blobUrlCache.get(cacheKey(entryId, attachmentId)) ?? null
}

export async function getAttachmentObjectUrl(
  entryId: string,
  attachmentId: string,
): Promise<string> {
  const key = cacheKey(entryId, attachmentId)
  const cached = blobUrlCache.get(key)
  if (cached) {
    return cached
  }

  const inflight = blobUrlInflight.get(key)
  if (inflight) {
    return inflight
  }

  const request = fetchMoodEntryAttachmentBlob(entryId, attachmentId)
    .then((blob) => {
      const objectUrl = URL.createObjectURL(blob)
      blobUrlCache.set(key, objectUrl)
      blobUrlInflight.delete(key)
      return objectUrl
    })
    .catch((error) => {
      blobUrlInflight.delete(key)
      throw error
    })

  blobUrlInflight.set(key, request)
  return request
}
