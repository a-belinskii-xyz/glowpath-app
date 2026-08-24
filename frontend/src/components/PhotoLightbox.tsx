import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'

import { AttachmentImage } from './AttachmentImage'
import { useLocale } from '../context/LocaleContext'
import { intlLocale } from '../i18n/t'
import { formatDayHeading, formatWeekday } from '../lib/datetime'

export type LightboxPhoto = {
  id: string
  entryId: string
  originalName: string
  createdAt?: string
}

type PhotoLightboxProps = {
  photos: LightboxPhoto[]
  index: number
  onClose: () => void
  onIndexChange: (index: number) => void
  showOpenEntry?: boolean
  timeZone?: string
}

export function PhotoLightbox({
  photos,
  index,
  onClose,
  onIndexChange,
  showOpenEntry = false,
  timeZone = 'UTC',
}: PhotoLightboxProps) {
  const { locale, t } = useLocale()
  const dialogRef = useRef<HTMLDivElement>(null)
  const photo = photos[index]
  const hasMultiple = photos.length > 1
  const dateLocale = intlLocale(locale)

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
  const addedAt = photo.createdAt

  return createPortal(
    <div className="photo-lightbox-backdrop" role="presentation" onClick={onClose}>
      <div
        className="photo-lightbox"
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={photo.originalName}
        onClick={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          className="photo-lightbox-close"
          onClick={onClose}
          aria-label={t('common.close')}
        >
          ×
        </button>

        {hasMultiple ? (
          <button
            type="button"
            className="photo-lightbox-nav photo-lightbox-prev"
            onClick={goPrev}
            aria-label={t('media.previousPhoto')}
          >
            ‹
          </button>
        ) : null}

        <div className="photo-lightbox-stage">
          <AttachmentImage
            className="photo-lightbox-image"
            entryId={photo.entryId}
            attachmentId={photo.id}
            alt={photo.originalName}
          />
        </div>

        {hasMultiple ? (
          <button
            type="button"
            className="photo-lightbox-nav photo-lightbox-next"
            onClick={goNext}
            aria-label={t('media.nextPhoto')}
          >
            ›
          </button>
        ) : null}

        <div className="photo-lightbox-footer">
          {addedAt ? (
            <div className="photo-lightbox-meta">
              <p className="photo-lightbox-date">{formatDayHeading(addedAt, timeZone, dateLocale)}</p>
              <p className="photo-lightbox-weekday">{formatWeekday(addedAt, timeZone, dateLocale)}</p>
            </div>
          ) : null}
          {showOpenEntry ? (
            <Link
              className="button photo-lightbox-open-entry"
              to={`/entries/${photo.entryId}`}
              state={{ from: '/gallery' }}
            >
              {t('gallery.openEntry')}
            </Link>
          ) : null}
          {hasMultiple ? (
            <p className="photo-lightbox-counter">
              {index + 1} / {photos.length}
            </p>
          ) : null}
        </div>
      </div>
    </div>,
    document.body,
  )
}
