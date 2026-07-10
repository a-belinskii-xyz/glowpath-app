import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'

import { AttachmentImage } from './AttachmentImage'
import type { AttachmentPublic } from '../types/mood'

type PhotoLightboxProps = {
  entryId: string
  photos: AttachmentPublic[]
  index: number
  onClose: () => void
  onIndexChange: (index: number) => void
}

export function PhotoLightbox({
  entryId,
  photos,
  index,
  onClose,
  onIndexChange,
}: PhotoLightboxProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const photo = photos[index]
  const hasMultiple = photos.length > 1

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
        return
      }
      if (!hasMultiple) {
        return
      }
      if (event.key === 'ArrowLeft') {
        event.preventDefault()
        onIndexChange((index - 1 + photos.length) % photos.length)
      }
      if (event.key === 'ArrowRight') {
        event.preventDefault()
        onIndexChange((index + 1) % photos.length)
      }
    }

    document.addEventListener('keydown', handleKey)
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', handleKey)
    }
  }, [hasMultiple, index, onClose, onIndexChange, photos.length])

  if (!photo) {
    return null
  }

  const goPrev = () => onIndexChange((index - 1 + photos.length) % photos.length)
  const goNext = () => onIndexChange((index + 1) % photos.length)

  return createPortal(
    <div className="photo-lightbox-backdrop" role="presentation" onClick={onClose}>
      <div
        className="photo-lightbox"
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={photo.original_name}
        onClick={(event) => event.stopPropagation()}
      >
        <button type="button" className="photo-lightbox-close" onClick={onClose} aria-label="Close">
          ×
        </button>

        {hasMultiple ? (
          <button
            type="button"
            className="photo-lightbox-nav photo-lightbox-prev"
            onClick={goPrev}
            aria-label="Previous photo"
          >
            ‹
          </button>
        ) : null}

        <div className="photo-lightbox-stage">
          <AttachmentImage
            className="photo-lightbox-image"
            entryId={entryId}
            attachmentId={photo.id}
            alt={photo.original_name}
          />
        </div>

        {hasMultiple ? (
          <button
            type="button"
            className="photo-lightbox-nav photo-lightbox-next"
            onClick={goNext}
            aria-label="Next photo"
          >
            ›
          </button>
        ) : null}

        {hasMultiple ? (
          <p className="photo-lightbox-counter">
            {index + 1} / {photos.length}
          </p>
        ) : null}
      </div>
    </div>,
    document.body,
  )
}
