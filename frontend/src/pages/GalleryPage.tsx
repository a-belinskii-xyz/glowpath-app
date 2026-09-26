import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'

import { listGalleryPhotos } from '../api/moodEntries'
import { AttachmentImage } from '../components/AttachmentImage'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { GuestGalleryCallout } from '../components/GuestAccountPreviews'
import { MinusIcon, PlusIcon } from '../components/icons'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { PhotoLightbox } from '../components/PhotoLightbox'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { isGuestDiaryMode } from '../lib/guestMode'
import { hasAppAccess } from '../lib/authAccess'
import { intlLocale } from '../i18n/t'
import {
  dayKey,
  formatDayHeading,
  formatMonthHeading,
  formatWeekday,
  monthKey,
} from '../lib/datetime'
import { ApiError, formatApiError } from '../lib/errors'
import type { GalleryPhotoPublic } from '../types/mood'

const PAGE_SIZE = 48

type Grouping = 'day' | 'month'

/**
 * Index 0 is the closest zoom. Column counts per level live in CSS
 * (`.gallery-zoom-N`); crossing from level 1 to 2 switches day → month groups.
 */
const ZOOM_GROUPINGS: readonly Grouping[] = ['day', 'day', 'month', 'month']
const DEFAULT_ZOOM = 2
const MAX_ZOOM = ZOOM_GROUPINGS.length - 1
const ZOOM_STORAGE_KEY = 'mood_tracker_gallery_zoom'

// Pinch must grow/shrink by this factor before we step one level.
const PINCH_STEP_RATIO = 1.3
// Accumulated ctrl+wheel delta (trackpad pinch) per level step.
const WHEEL_STEP_DELTA = 80

type PhotoGroup = {
  key: string
  heading: string
  photos: { photo: GalleryPhotoPublic; index: number }[]
}

type ZoomAnchor = { photoId: string; top: number }

function readStoredZoom(): number {
  try {
    const stored = Number(localStorage.getItem(ZOOM_STORAGE_KEY))
    return Number.isInteger(stored) && stored >= 0 && stored <= MAX_ZOOM
      ? stored
      : DEFAULT_ZOOM
  } catch {
    return DEFAULT_ZOOM
  }
}

function storeZoom(level: number): void {
  try {
    localStorage.setItem(ZOOM_STORAGE_KEY, String(level))
  } catch {
    // Storage can be unavailable (private mode); the in-memory value still applies.
  }
}

function groupPhotos(
  photos: GalleryPhotoPublic[],
  grouping: Grouping,
  timeZone: string,
  locale: string,
): PhotoGroup[] {
  const groups: PhotoGroup[] = []
  const byKey = new Map<string, PhotoGroup>()

  photos.forEach((photo, index) => {
    const key =
      grouping === 'day'
        ? dayKey(photo.created_at, timeZone)
        : monthKey(photo.created_at, timeZone)
    let group = byKey.get(key)
    if (!group) {
      let heading: string
      if (grouping === 'day') {
        heading = `${formatWeekday(photo.created_at, timeZone, locale)}, ${formatDayHeading(
          photo.created_at,
          timeZone,
          locale,
        )}`
      } else {
        const [year, monthNumber] = key.split('-').map(Number)
        heading = formatMonthHeading(year, monthNumber - 1, locale)
      }
      group = { key, heading, photos: [] }
      byKey.set(key, group)
      groups.push(group)
    }
    group.photos.push({ photo, index })
  })

  return groups
}

/** The tile closest to `focusY` (viewport px), so zooming keeps it in place. */
function findZoomAnchor(root: HTMLElement, focusY: number): ZoomAnchor | null {
  let best: ZoomAnchor | null = null
  let bestDistance = Infinity
  root.querySelectorAll<HTMLElement>('[data-photo-id]').forEach((tile) => {
    const rect = tile.getBoundingClientRect()
    if (rect.bottom < 0 || rect.top > window.innerHeight) {
      return
    }
    const distance = Math.abs(rect.top + rect.height / 2 - focusY)
    if (distance < bestDistance) {
      bestDistance = distance
      best = { photoId: tile.dataset.photoId ?? '', top: rect.top }
    }
  })
  return best
}

function touchDistance(touches: TouchList): number {
  const [a, b] = [touches[0], touches[1]]
  return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY)
}

export function GalleryPage() {
  const { user } = useAuth()
  const { locale, t } = useLocale()
  const guestLocked = isGuestDiaryMode()
  const timeZone =
    user?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC'
  const dateLocale = intlLocale(locale)

  const [photos, setPhotos] = useState<GalleryPhotoPublic[]>([])
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [isLoading, setIsLoading] = useState(!guestLocked)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)
  const [zoom, setZoom] = useState(readStoredZoom)

  const loadMoreRef = useRef<HTMLDivElement | null>(null)
  const loadingRef = useRef(false)
  const gridRootRef = useRef<HTMLDivElement | null>(null)
  const zoomRef = useRef(zoom)
  const zoomAnchorRef = useRef<ZoomAnchor | null>(null)

  const applyZoom = useCallback((next: number, focusY = window.innerHeight / 3) => {
    const clamped = Math.min(MAX_ZOOM, Math.max(0, next))
    if (clamped === zoomRef.current) {
      return
    }
    const root = gridRootRef.current
    zoomAnchorRef.current = root ? findZoomAnchor(root, focusY) : null
    zoomRef.current = clamped
    setZoom(clamped)
    storeZoom(clamped)
  }, [])

  // Keep the photo that was under the zoom focus at the same screen position.
  useLayoutEffect(() => {
    const anchor = zoomAnchorRef.current
    zoomAnchorRef.current = null
    if (!anchor || !gridRootRef.current) {
      return
    }
    const tile = gridRootRef.current.querySelector<HTMLElement>(
      `[data-photo-id="${CSS.escape(anchor.photoId)}"]`,
    )
    if (tile) {
      window.scrollBy(0, tile.getBoundingClientRect().top - anchor.top)
    }
  }, [zoom])

  // Pinch (touch) and ctrl+wheel (trackpad pinch / ctrl+scroll) step the zoom.
  const hasPhotos = photos.length > 0
  useEffect(() => {
    const root = gridRootRef.current
    if (!root) {
      return
    }

    let pinchBaseDistance = 0

    const onTouchStart = (event: TouchEvent) => {
      if (event.touches.length === 2) {
        pinchBaseDistance = touchDistance(event.touches)
      }
    }
    const onTouchMove = (event: TouchEvent) => {
      if (event.touches.length !== 2 || pinchBaseDistance === 0) {
        return
      }
      event.preventDefault()
      const distance = touchDistance(event.touches)
      const ratio = distance / pinchBaseDistance
      const focusY = (event.touches[0].clientY + event.touches[1].clientY) / 2
      if (ratio >= PINCH_STEP_RATIO) {
        applyZoom(zoomRef.current - 1, focusY)
        pinchBaseDistance = distance
      } else if (ratio <= 1 / PINCH_STEP_RATIO) {
        applyZoom(zoomRef.current + 1, focusY)
        pinchBaseDistance = distance
      }
    }
    const onTouchEnd = (event: TouchEvent) => {
      if (event.touches.length < 2) {
        pinchBaseDistance = 0
      }
    }

    let wheelDelta = 0
    const onWheel = (event: WheelEvent) => {
      if (!event.ctrlKey) {
        return
      }
      event.preventDefault()
      wheelDelta += event.deltaY
      if (Math.abs(wheelDelta) >= WHEEL_STEP_DELTA) {
        applyZoom(zoomRef.current + Math.sign(wheelDelta), event.clientY)
        wheelDelta = 0
      }
    }

    root.addEventListener('touchstart', onTouchStart, { passive: true })
    root.addEventListener('touchmove', onTouchMove, { passive: false })
    root.addEventListener('touchend', onTouchEnd, { passive: true })
    root.addEventListener('touchcancel', onTouchEnd, { passive: true })
    root.addEventListener('wheel', onWheel, { passive: false })
    return () => {
      root.removeEventListener('touchstart', onTouchStart)
      root.removeEventListener('touchmove', onTouchMove)
      root.removeEventListener('touchend', onTouchEnd)
      root.removeEventListener('touchcancel', onTouchEnd)
      root.removeEventListener('wheel', onWheel)
    }
  }, [applyZoom, hasPhotos])

  usePageAmbientGlow(['#64748b', '#94a3b8', '#cbd5e1'])

  const loadPage = useCallback(
    async (pageOffset: number, replace: boolean) => {
      if (guestLocked || !hasAppAccess(user) || loadingRef.current) {
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
    [guestLocked, t, user],
  )

  useEffect(() => {
    if (guestLocked || !hasAppAccess(user)) {
      setPhotos([])
      setOffset(0)
      setHasMore(false)
      setIsLoading(false)
      return
    }
    setOffset(0)
    setHasMore(true)
    void loadPage(0, true)
  }, [guestLocked, loadPage, user])

  useEffect(() => {
    const node = loadMoreRef.current
    if (guestLocked || !node || !hasMore || isLoading || isLoadingMore) {
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
  }, [guestLocked, hasMore, isLoading, isLoadingMore, loadPage, offset])

  const grouping = ZOOM_GROUPINGS[zoom]
  const photoGroups = useMemo(
    () => groupPhotos(photos, grouping, timeZone, dateLocale),
    [dateLocale, grouping, photos, timeZone],
  )

  return (
    <section className="page page-gallery">
      <EmailVerificationBanner />

      <header className="page-header">
        <h1>{t('gallery.title')}</h1>
        {hasPhotos ? (
          <div className="gallery-zoom-controls" role="group" aria-label={t('gallery.zoomControls')}>
            <button
              type="button"
              className="icon-button icon-button-md"
              aria-label={t('gallery.zoomOut')}
              title={t('gallery.zoomOut')}
              disabled={zoom >= MAX_ZOOM}
              onClick={() => applyZoom(zoom + 1)}
            >
              <MinusIcon />
            </button>
            <button
              type="button"
              className="icon-button icon-button-md"
              aria-label={t('gallery.zoomIn')}
              title={t('gallery.zoomIn')}
              disabled={zoom <= 0}
              onClick={() => applyZoom(zoom - 1)}
            >
              <PlusIcon />
            </button>
          </div>
        ) : null}
      </header>

      {guestLocked ? <GuestGalleryCallout /> : null}

      <PageErrorAlert error={error} />

      {isLoading ? <p className="muted">{t('common.loadingGallery')}</p> : null}

      {!isLoading && photos.length === 0 && !error ? (
        <p className="muted">
          {t('gallery.empty')} {t('gallery.emptyHint')}
        </p>
      ) : null}

      {hasPhotos ? (
        <div
          ref={gridRootRef}
          className={`gallery-groups gallery-zoom-${zoom} gallery-by-${grouping}`}
        >
          {photoGroups.map((group) => (
            <section key={group.key} className="gallery-group">
              <h2 className="gallery-group-heading">{group.heading}</h2>
              <div className="gallery-grid">
                {group.photos.map(({ photo, index }) => (
                  <button
                    key={photo.id}
                    type="button"
                    className="gallery-tile"
                    data-photo-id={photo.id}
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

      {hasMore && hasAppAccess(user) ? (
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
