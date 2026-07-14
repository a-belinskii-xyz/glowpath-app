import { useState } from 'react'

import { AttachmentImage } from './AttachmentImage'
import { PhotoLightbox } from './PhotoLightbox'
import type { AttachmentPublic } from '../types/mood'

type EntryAttachmentThumbsProps = {
  entryId: string
  attachments: AttachmentPublic[]
}

export function EntryAttachmentThumbs({ entryId, attachments }: EntryAttachmentThumbsProps) {
  const photos = attachments
    .filter((attachment) => attachment.kind === 'photo')
    .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
  const audioCount = attachments.filter((attachment) => attachment.kind === 'audio').length
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)

  if (photos.length === 0 && audioCount === 0) {
    return null
  }

  return (
    <>
      <span className="entry-attachments">
        {photos.length > 0 ? (
          <span className="entry-photo-thumbs">
            {photos.map((photo, index) => (
              <span
                key={photo.id}
                role="button"
                tabIndex={0}
                className="entry-photo-thumb-button"
                aria-label={`View ${photo.original_name}`}
                onClick={(event) => {
                  event.preventDefault()
                  event.stopPropagation()
                  setLightboxIndex(index)
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    event.stopPropagation()
                    setLightboxIndex(index)
                  }
                }}
              >
                <AttachmentImage
                  className="entry-photo-thumb"
                  entryId={entryId}
                  attachmentId={photo.id}
                  alt={photo.original_name}
                />
              </span>
            ))}
          </span>
        ) : null}
        {audioCount > 0 ? <span className="entry-audio-count muted">{audioCount} audio</span> : null}
      </span>

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
