import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { listGalleryPhotos } from '../api/moodEntries'
import { AttachmentImage } from '../components/AttachmentImage'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { PhotoLightbox } from '../components/PhotoLightbox'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { intlLocale } from '../i18n/t'
import { formatMonthHeading, monthKey } from '../lib/datetime'
import { ApiError, formatApiError } from '../lib/errors'
import type { GalleryPhotoPublic } from '../types/mood'

const PAGE_SIZE = 48

type MonthGroup = {
  key: string
  year: number
  month: number
  photos: { photo: GalleryPhotoPublic; index: number }[]
}

function groupPhotosByMonth(
  photos: GalleryPhotoPublic[],
  timeZone: string,
): MonthGroup[] {
  const groups: MonthGroup[] = []
  const byKey = new Map<string, MonthGroup>()

  photos.forEach((photo, index) => {
    const key = monthKey(photo.created_at, timeZone)
    let group = byKey.get(key)
    if (!group) {
      const [year, monthNumber] = key.split('-').map(Number)
      group = { key, year, month: monthNumber - 1, photos: [] }
      byKey.set(key, group)
      groups.push(group)
    }
    group.photos.push({ photo, index })
  })

  return groups
}

export function GalleryPage() {
  const { user } = useAuth()
  const { locale, t } = useLocale()
  const timeZone = user?.timezone ?? 'UTC'
  const dateLocale = intlLocale(locale)

  const [photos, setPhotos] = useState<GalleryPhotoPublic[]>([])
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)

  const loadMoreRef = useRef<HTMLDivElement | null>(null)
  const loadingRef = useRef(false)

  usePageAmbientGlow(['#64748b', '#94a3b8', '#cbd5e1'])

  const loadPage = useCallback(
    async (pageOffset: number, replace: boolean) => {
      if (!user?.email_verified || loadingRef.current) {
        return
      }
      loadingRef.current = true
      if (replace) {
        setIsLoading(true)
      } else {
        setIsLoadingMore(true)
      }
      setError(null)
      try {
        const response = await listGalleryPhotos({ limit: PAGE_SIZE, offset: pageOffset })
        setPhotos((current) => (replace ? response.items : [...current, ...response.items]))
        setOffset(pageOffset + response.items.length)
        setHasMore(response.items.length >= PAGE_SIZE)
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError(t('errors.verifyToViewGallery'))
        } else {
          setError(formatApiError(err, t, 'errors.failedLoadGallery'))
        }
        if (replace) {
          setPhotos([])
          setHasMore(false)
        }
      } finally {
        loadingRef.current = false
        setIsLoading(false)
        setIsLoadingMore(false)
      }
    },
    [t, user?.email_verified],
  )

  useEffect(() => {
    if (!user?.email_verified) {
      setPhotos([])
      setOffset(0)
      setHasMore(false)
      setIsLoading(false)
      return
    }
    setOffset(0)
    setHasMore(true)
    void loadPage(0, true)
  }, [loadPage, user?.email_verified])

  useEffect(() => {
    const node = loadMoreRef.current
    if (!node || !hasMore || isLoading || isLoadingMore) {
      return
    }
    const observer = new IntersectionObserver(
      (records) => {
        if (records[0]?.isIntersecting) {
          void loadPage(offset, false)
        }
      },
      { rootMargin: '240px' },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [hasMore, isLoading, isLoadingMore, loadPage, offset])

  const monthGroups = useMemo(
    () => groupPhotosByMonth(photos, timeZone),
    [photos, timeZone],
  )

  return (
    <section className="page page-gallery">
      <EmailVerificationBanner />

      <header className="page-header">
        <h1>{t('gallery.title')}</h1>
      </header>

      <PageErrorAlert error={error} />

      {isLoading ? <p className="muted">{t('common.loadingGallery')}</p> : null}

      {!isLoading && photos.length === 0 && !error ? (
        <p className="muted">
          {t('gallery.empty')} {t('gallery.emptyHint')}
        </p>
      ) : null}

      {photos.length > 0 ? (
        <div className="gallery-months">
          {monthGroups.map((group) => (
            <section key={group.key} className="gallery-month">
              <h2 className="gallery-month-heading">
                {formatMonthHeading(group.year, group.month, dateLocale)}
              </h2>
              <div className="gallery-grid">
                {group.photos.map(({ photo, index }) => (
                  <button
                    key={photo.id}
                    type="button"
                    className="gallery-tile"
                    aria-label={t('media.viewPhoto', { name: photo.original_name })}
                    onClick={() => setLightboxIndex(index)}
                  >
                    <AttachmentImage
                      className="gallery-tile-image"
                      entryId={photo.mood_entry_id}
                      attachmentId={photo.id}
                      alt={photo.original_name}
                    />
                  </button>
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : null}

      {hasMore && user?.email_verified ? (
        <div ref={loadMoreRef} className="load-more-sentinel">
          {isLoadingMore ? <p className="muted">{t('common.loadingMore')}</p> : null}
        </div>
      ) : null}

      {lightboxIndex !== null ? (
        <PhotoLightbox
          photos={photos.map((photo) => ({
            id: photo.id,
            entryId: photo.mood_entry_id,
            originalName: photo.original_name,
            createdAt: photo.created_at,
          }))}
          index={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
          onIndexChange={setLightboxIndex}
          showOpenEntry
          timeZone={timeZone}
        />
      ) : null}
    </section>
  )
}
