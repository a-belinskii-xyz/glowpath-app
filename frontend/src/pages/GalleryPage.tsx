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

// Pinch scale (relative to the gesture start) needed to step one level.
const PINCH_STEP_RATIO = 1.3
// How far the live preview may scale past the last reachable level.
const PINCH_OVERSHOOT = 1.15
// ctrl+wheel (trackpad pinch) delta → scale factor, and idle time before commit.
const WHEEL_SCALE_PER_DELTA = 0.01
// A mouse-wheel notch (~100px) would otherwise jump several levels at once.
const WHEEL_MAX_DELTA = 30
const WHEEL_COMMIT_MS = 140
const ZOOM_ANIMATION = 'transform 300ms cubic-bezier(0.22, 1, 0.36, 1)'

type PhotoGroup = {
  key: string
  heading: string
  photos: { photo: GalleryPhotoPublic; index: number }[]
}

/** A tile and where it was drawn on screen before the zoom level changed. */
type ZoomAnchor = { photoId: string; rect: DOMRect }

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

/** The visible tile closest to the focus point, so zooming keeps it in place. */
function findZoomAnchor(root: HTMLElement, focusX: number, focusY: number): ZoomAnchor | null {
  let best: ZoomAnchor | null = null
  let bestDistance = Infinity
  root.querySelectorAll<HTMLElement>('[data-photo-id]').forEach((tile) => {
    const rect = tile.getBoundingClientRect()
    if (rect.bottom < 0 || rect.top > window.innerHeight) {
      return
    }
    const distance = Math.hypot(
      rect.left + rect.width / 2 - focusX,
      rect.top + rect.height / 2 - focusY,
    )
    if (distance < bestDistance) {
      bestDistance = distance
      best = { photoId: tile.dataset.photoId ?? '', rect }
    }
  })
  return best
}

function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** Animate `root` from `transform` back to identity. */
function animateToIdentity(root: HTMLElement, transform: string): void {
  root.style.transition = 'none'
  root.style.transform = transform
  if (prefersReducedMotion() || !transform) {
    root.style.transform = ''
    return
  }
  void root.offsetWidth
  root.style.transition = ZOOM_ANIMATION
  root.style.transform = ''
}

/** Levels to step for a pinch scale: >1 zooms in (negative steps). */
function pinchSteps(scale: number): number {
  const steps = Math.floor(Math.abs(Math.log(scale)) / Math.log(PINCH_STEP_RATIO))
  return scale >= 1 ? -steps : steps
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

  const lightboxOpenRef = useRef(false)
  lightboxOpenRef.current = lightboxIndex !== null

  const applyZoom = useCallback(
    (next: number, focusX = window.innerWidth / 2, focusY = window.innerHeight / 3) => {
      const clamped = Math.min(MAX_ZOOM, Math.max(0, next))
      const root = gridRootRef.current
      if (clamped === zoomRef.current) {
        // Nothing to switch to: let a live pinch preview spring back.
        if (root?.style.transform) {
          animateToIdentity(root, root.style.transform)
        }
        return
      }
      zoomAnchorRef.current = root ? findZoomAnchor(root, focusX, focusY) : null
      zoomRef.current = clamped
      setZoom(clamped)
      storeZoom(clamped)
    },
    [],
  )

  // Keep the anchor tile in place, then animate from its old on-screen size (FLIP).
  useLayoutEffect(() => {
    const anchor = zoomAnchorRef.current
    zoomAnchorRef.current = null
    const root = gridRootRef.current
    if (!root) {
      return
    }
    root.style.transition = 'none'
    root.style.transform = ''
    if (!anchor) {
      return
    }
    const tile = root.querySelector<HTMLElement>(
      `[data-photo-id="${CSS.escape(anchor.photoId)}"]`,
    )
    if (!tile) {
      return
    }
    window.scrollBy(0, tile.getBoundingClientRect().top - anchor.rect.top)
    const from = anchor.rect
    const to = tile.getBoundingClientRect()
    const rootRect = root.getBoundingClientRect()
    const scale = from.width / to.width
    const tx = from.left - rootRect.left - (to.left - rootRect.left) * scale
    const ty = from.top - rootRect.top - (to.top - rootRect.top) * scale
    root.style.transformOrigin = '0 0'
    animateToIdentity(root, `translate3d(${tx}px, ${ty}px, 0) scale(${scale})`)
  }, [zoom])

  // Pinch (touch) and ctrl+wheel (trackpad pinch / ctrl+scroll) anywhere on the
  // page scale the grid live, then commit to the nearest zoom level on release.
  const hasPhotos = photos.length > 0
  useEffect(() => {
    if (!hasPhotos) {
      return
    }

    let liveScale = 1
    let originX = 0
    let originY = 0
    let frame = 0

    const limitScale = (raw: number) => {
      const max = PINCH_STEP_RATIO ** zoomRef.current * PINCH_OVERSHOOT
      const min = 1 / (PINCH_STEP_RATIO ** (MAX_ZOOM - zoomRef.current) * PINCH_OVERSHOOT)
      return Math.min(max, Math.max(min, raw))
    }

    const beginPreview = (focusX: number, focusY: number) => {
      const root = gridRootRef.current
      if (!root) {
        return false
      }
      root.style.transition = 'none'
      root.style.transform = ''
      const rect = root.getBoundingClientRect()
      originX = focusX - rect.left
      originY = focusY - rect.top
      root.style.transformOrigin = `${originX}px ${originY}px`
      root.style.willChange = 'transform'
      liveScale = 1
      return true
    }

    const renderPreview = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        const root = gridRootRef.current
        if (root) {
          root.style.transform = `scale(${liveScale})`
        }
      })
    }

    const commitPreview = (focusX: number, focusY: number) => {
      cancelAnimationFrame(frame)
      const root = gridRootRef.current
      if (!root) {
        return
      }
      root.style.transform = `scale(${liveScale})`
      root.style.willChange = ''
      applyZoom(zoomRef.current + pinchSteps(liveScale), focusX, focusY)
      liveScale = 1
    }

    let pinchBaseDistance = 0
    let pinchFocusX = 0
    let pinchFocusY = 0

    const onTouchStart = (event: TouchEvent) => {
      if (event.touches.length !== 2 || lightboxOpenRef.current) {
        return
      }
      const [a, b] = [event.touches[0], event.touches[1]]
      pinchFocusX = (a.clientX + b.clientX) / 2
      pinchFocusY = (a.clientY + b.clientY) / 2
      if (beginPreview(pinchFocusX, pinchFocusY)) {
        pinchBaseDistance = touchDistance(event.touches)
      }
    }
    const onTouchMove = (event: TouchEvent) => {
      if (pinchBaseDistance === 0 || event.touches.length !== 2) {
        return
      }
      event.preventDefault()
      liveScale = limitScale(touchDistance(event.touches) / pinchBaseDistance)
      renderPreview()
    }
    const onTouchEnd = (event: TouchEvent) => {
      if (pinchBaseDistance === 0 || event.touches.length >= 2) {
        return
      }
      pinchBaseDistance = 0
      commitPreview(pinchFocusX, pinchFocusY)
    }
    // iOS Safari zooms the page on gesture events even when touchmove is cancelled.
    const onGesture = (event: Event) => {
      if (!lightboxOpenRef.current) {
        event.preventDefault()
      }
    }

    let wheelTimer = 0
    let wheelActive = false
    let wheelFocusX = 0
    let wheelFocusY = 0
    const onWheel = (event: WheelEvent) => {
      if (!event.ctrlKey || lightboxOpenRef.current) {
        return
      }
      event.preventDefault()
      if (!wheelActive) {
        wheelFocusX = event.clientX
        wheelFocusY = event.clientY
        wheelActive = beginPreview(wheelFocusX, wheelFocusY)
        if (!wheelActive) {
          return
        }
      }
      liveScale = limitScale(liveScale *
          Math.exp(
            -Math.max(-WHEEL_MAX_DELTA, Math.min(WHEEL_MAX_DELTA, event.deltaY)) *
              WHEEL_SCALE_PER_DELTA,
          ))
      renderPreview()
      window.clearTimeout(wheelTimer)
      wheelTimer = window.setTimeout(() => {
        wheelActive = false
        commitPreview(wheelFocusX, wheelFocusY)
      }, WHEEL_COMMIT_MS)
    }

    document.addEventListener('touchstart', onTouchStart, { passive: true })
    document.addEventListener('touchmove', onTouchMove, { passive: false })
    document.addEventListener('touchend', onTouchEnd, { passive: true })
    document.addEventListener('touchcancel', onTouchEnd, { passive: true })
    document.addEventListener('gesturestart', onGesture, { passive: false })
    document.addEventListener('gesturechange', onGesture, { passive: false })
    document.addEventListener('wheel', onWheel, { passive: false })
    return () => {
      cancelAnimationFrame(frame)
      window.clearTimeout(wheelTimer)
      document.removeEventListener('touchstart', onTouchStart)
      document.removeEventListener('touchmove', onTouchMove)
      document.removeEventListener('touchend', onTouchEnd)
      document.removeEventListener('touchcancel', onTouchEnd)
      document.removeEventListener('gesturestart', onGesture)
      document.removeEventListener('gesturechange', onGesture)
      document.removeEventListener('wheel', onWheel)
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
