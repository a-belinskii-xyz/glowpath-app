import { useState } from 'react'

import { AttachmentImage } from './AttachmentImage'
import { AudioIcon } from './icons'
import { PhotoLightbox } from './PhotoLightbox'
import { useLocale } from '../context/LocaleContext'
import type { AttachmentPublic } from '../types/mood'

const COLLAGE_VISIBLE_MAX = 5

type EntryAttachmentThumbsProps = {
  entryId: string
  attachments: AttachmentPublic[]
  showAudioCount?: boolean
  /** Compact thumbs for lists; collage for entry detail. */
  variant?: 'thumbs' | 'collage'
}

export function EntryAttachmentThumbs({
  entryId,
  attachments,
  showAudioCount = true,
  variant = 'thumbs',
}: EntryAttachmentThumbsProps) {
  const { t } = useLocale()
  const photos = attachments
    .filter((attachment) => attachment.kind === 'photo')
    .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
  const audioCount = showAudioCount
    ? attachments.filter((attachment) => attachment.kind === 'audio').length
    : 0
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)

  if (photos.length === 0 && audioCount === 0) {
    return null
  }

  const openPhoto = (index: number) => {
    setLightboxIndex(index)
  }

  const collageCount = Math.min(photos.length, COLLAGE_VISIBLE_MAX)
  const collagePhotos = photos.slice(0, collageCount)
  const hiddenCount = photos.length - collageCount

  return (
    <>
      <div className="entry-attachments">
        {photos.length > 0 ? (
          variant === 'collage' ? (
            <div
              className="entry-photo-collage"
              data-count={collageCount}
            >
              {collagePhotos.map((photo, index) => {
                const isLastVisible = index === collageCount - 1
                const overflowLabel =
                  isLastVisible && hiddenCount > 0 ? `+${hiddenCount}` : null

                return (
                  <button
                    key={photo.id}
                    type="button"
                    className="entry-photo-collage-item"
                    aria-label={
                      overflowLabel
                        ? t('media.viewPhoto', {
                            name: `${photo.original_name} (+${hiddenCount})`,
                          })
                        : t('media.viewPhoto', { name: photo.original_name })
                    }
                    onClick={(event) => {
                      event.preventDefault()
                      event.stopPropagation()
                      openPhoto(index)
                    }}
                  >
                    <AttachmentImage
                      className="entry-photo-collage-image"
                      entryId={entryId}
                      attachmentId={photo.id}
                      alt={photo.original_name}
                    />
                    {overflowLabel ? (
                      <span className="entry-photo-collage-more" aria-hidden>
                        {overflowLabel}
                      </span>
                    ) : null}
                  </button>
                )
              })}
            </div>
          ) : (
            <div className="entry-photo-thumbs">
              {photos.map((photo, index) => (
                <button
                  key={photo.id}
                  type="button"
                  className="entry-photo-thumb-button"
                  aria-label={t('media.viewPhoto', { name: photo.original_name })}
                  onClick={(event) => {
                    event.preventDefault()
                    event.stopPropagation()
                    openPhoto(index)
                  }}
                >
                  <AttachmentImage
                    className="entry-photo-thumb"
                    entryId={entryId}
                    attachmentId={photo.id}
                    alt={photo.original_name}
                  />
                </button>
              ))}
            </div>
          )
        ) : null}
        {audioCount > 0 ? (
          <span
            className="entry-audio-badge muted"
            aria-label={t('media.audioCount', { count: audioCount })}
            title={t('media.audioCount', { count: audioCount })}
          >
            <AudioIcon className="entry-audio-badge-icon" />
          </span>
        ) : null}
      </div>

      {lightboxIndex !== null ? (
        <PhotoLightbox
          entryId={entryId}
          photos={photos}
          index={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
          onIndexChange={setLightboxIndex}
        />
      ) : null}
    </>
  )
}
