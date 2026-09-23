import { useEffect, useState } from 'react'

import {
  getAttachmentObjectUrl,
  getCachedAttachmentObjectUrl,
} from '../lib/attachmentBlobUrl'

type AttachmentImageProps = {
  entryId: string
  attachmentId: string
  alt: string
  className?: string
}

export function AttachmentImage({ entryId, attachmentId, alt, className }: AttachmentImageProps) {
  const [src, setSrc] = useState<string | null>(
    () => getCachedAttachmentObjectUrl(entryId, attachmentId),
  )
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    const cached = getCachedAttachmentObjectUrl(entryId, attachmentId)
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
