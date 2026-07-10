import { useEffect, useState } from 'react'

import { fetchMoodEntryAttachmentBlob } from '../api/moodEntries'

const blobUrlCache = new Map<string, string>()
const blobUrlInflight = new Map<string, Promise<string>>()

function cacheKey(entryId: string, attachmentId: string): string {
  return `${entryId}:${attachmentId}`
}

async function getAttachmentObjectUrl(entryId: string, attachmentId: string): Promise<string> {
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

type AttachmentImageProps = {
  entryId: string
  attachmentId: string
  alt: string
  className?: string
}

export function AttachmentImage({ entryId, attachmentId, alt, className }: AttachmentImageProps) {
  const [src, setSrc] = useState<string | null>(
    () => blobUrlCache.get(cacheKey(entryId, attachmentId)) ?? null,
  )
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    const key = cacheKey(entryId, attachmentId)
    const cached = blobUrlCache.get(key)
    if (cached) {
      setSrc(cached)
      setFailed(false)
      return
    }

    setSrc(null)
    setFailed(false)

    void getAttachmentObjectUrl(entryId, attachmentId)
      .then((objectUrl) => {
        if (!cancelled) {
          setSrc(objectUrl)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setFailed(true)
        }
      })

    return () => {
      cancelled = true
    }
  }, [entryId, attachmentId])

  if (failed) {
    return <span className={`attachment-image-fallback ${className ?? ''}`.trim()}>?</span>
  }

  if (!src) {
    return <span className={`attachment-image-skeleton ${className ?? ''}`.trim()} aria-hidden />
  }

  return <img className={className} src={src} alt={alt} loading="lazy" />
}
