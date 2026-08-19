import { useEffect, useState } from 'react'

import { SoftAudioPlayer } from './SoftAudioPlayer'
import { useLocale } from '../context/LocaleContext'
import {
  getAttachmentObjectUrl,
  getCachedAttachmentObjectUrl,
} from '../lib/attachmentBlobUrl'
import type { AttachmentPublic } from '../types/mood'

type AttachmentAudioProps = {
  entryId: string
  attachment: AttachmentPublic
  /** Mood (or goal) hex used to tint the soft player chrome. */
  accentColor?: string
  className?: string
}

export function AttachmentAudio({
  entryId,
  attachment,
  accentColor,
  className,
}: AttachmentAudioProps) {
  const { t } = useLocale()
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
        {t('media.audioLoadFailed', { name: attachment.original_name })}
      </p>
    )
  }

  return (
    <SoftAudioPlayer
      src={src}
      accentColor={accentColor}
      title={attachment.original_name}
      className={className}
    >
      {attachment.transcription ? (
        <p className="entry-audio-transcription">{attachment.transcription}</p>
      ) : null}
    </SoftAudioPlayer>
  )
}
