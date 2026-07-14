import { useEffect, useState } from 'react'

import {
  getAttachmentObjectUrl,
  getCachedAttachmentObjectUrl,
} from '../lib/attachmentBlobUrl'
import type { AttachmentPublic } from '../types/mood'

type AttachmentAudioProps = {
  entryId: string
  attachment: AttachmentPublic
  className?: string
}

export function AttachmentAudio({ entryId, attachment, className }: AttachmentAudioProps) {
  const [src, setSrc] = useState<string | null>(
    () => getCachedAttachmentObjectUrl(entryId, attachment.id),
  )
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    const cached = getCachedAttachmentObjectUrl(entryId, attachment.id)
    if (cached) {
      setSrc(cached)
      setFailed(false)
      return
    }

    setSrc(null)
    setFailed(false)

    void getAttachmentObjectUrl(entryId, attachment.id)
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
  }, [entryId, attachment.id])

  if (failed) {
    return (
      <p className={`entry-audio-error muted ${className ?? ''}`.trim()}>
        Could not load audio: {attachment.original_name}
      </p>
    )
  }

  return (
    <div className={`entry-audio-player ${className ?? ''}`.trim()}>
      <p className="entry-audio-name muted">{attachment.original_name}</p>
      {src ? (
        <audio controls preload="metadata" src={src}>
          Your browser does not support audio playback.
        </audio>
      ) : (
        <div className="entry-audio-skeleton" aria-hidden />
      )}
    </div>
  )
}
