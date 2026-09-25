import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'

import { AttachmentImage } from './AttachmentImage'
import { useLocale } from '../context/LocaleContext'
import { motion } from '../design'
import { intlLocale } from '../i18n/t'
import { formatDayHeading, formatWeekday } from '../lib/datetime'

const AXIS_LOCK_PX = 10
const SNAP_RATIO = 0.18
const SNAP_MIN_PX = 56
const FLICK_VELOCITY = 0.55
const FLICK_MIN_PX = 18
const RUBBER = 0.32
const GESTURE_IGNORE = 'button, a, input, textarea, select'

type GestureAxis = 'none' | 'x' | 'y'

type Gesture = {
  pointerId: number
  startX: number
  startY: number
  lastX: number
  lastT: number
  velocity: number
  axis: GestureAxis
}

function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function resistedOffset(raw: number, canPrev: boolean, canNext: boolean) {
  if (raw > 0 && !canPrev) {
    return raw * RUBBER
  }
  if (raw < 0 && !canNext) {
    return raw * RUBBER
  }
  return raw
}

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
  const stageRef = useRef<HTMLDivElement>(null)
  const trackRef = useRef<HTMLDivElement>(null)
  const gestureRef = useRef<Gesture | null>(null)
  const offsetRef = useRef(0)
  const indexRef = useRef(index)
  const onIndexChangeRef = useRef(onIndexChange)
  const pendingDirRef = useRef<-1 | 0 | 1>(0)
  const settlingRef = useRef(false)
  const settleTimerRef = useRef<number | null>(null)
  const [offset, setOffset] = useState(0)
  const [dragging, setDragging] = useState(false)
  const [animating, setAnimating] = useState(false)

  const photo = photos[index]
  const hasMultiple = photos.length > 1
  const canPrev = index > 0
  const canNext = index < photos.length - 1
  const dateLocale = intlLocale(locale)
  indexRef.current = index
  onIndexChangeRef.current = onIndexChange

  const clearSettleTimer = () => {
    if (settleTimerRef.current !== null) {
      window.clearTimeout(settleTimerRef.current)
      settleTimerRef.current = null
    }
  }

  const finishSettle = () => {
    if (!settlingRef.current) {
      return
    }
    settlingRef.current = false
    clearSettleTimer()
    const dir = pendingDirRef.current
    pendingDirRef.current = 0
    offsetRef.current = 0
    setOffset(0)
    setAnimating(false)
    if (dir !== 0) {
      onIndexChangeRef.current(indexRef.current + dir)
    }
  }

  const settleTo = (target: number, dir: -1 | 0 | 1) => {
    gestureRef.current = null
    setDragging(false)
    if (prefersReducedMotion() || (dir === 0 && Math.abs(offsetRef.current) < 1)) {
      pendingDirRef.current = dir
      settlingRef.current = true
      finishSettle()
      return
    }
    pendingDirRef.current = dir
    settlingRef.current = true
    offsetRef.current = target
    setOffset(target)
    setAnimating(true)
    clearSettleTimer()
    settleTimerRef.current = window.setTimeout(finishSettle, motion.pager.durationMs + 80)
  }

  useEffect(() => {
    const node = trackRef.current
    if (!node) {
      return
    }
    const onEnd = (event: TransitionEvent) => {
      if (event.propertyName !== 'transform' || event.target !== node) {
        return
      }
      finishSettle()
    }
    node.addEventListener('transitionend', onEnd)
    return () => {
      node.removeEventListener('transitionend', onEnd)
      clearSettleTimer()
    }
  }, [photo?.id])

  useEffect(() => {
    if (settlingRef.current) {
      return
    }
    offsetRef.current = 0
    setOffset(0)
    setDragging(false)
  }, [index])

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
        return
      }
      if (!hasMultiple || settlingRef.current) {
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
  const slides = hasMultiple
    ? [canPrev ? photos[index - 1] : null, photo, canNext ? photos[index + 1] : null]
    : [photo]

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0 || settlingRef.current) {
      return
    }
    if (event.target instanceof Element && event.target.closest(GESTURE_IGNORE)) {
      return
    }
    gestureRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      lastX: event.clientX,
      lastT: event.timeStamp,
      velocity: 0,
      axis: 'none',
    }
  }

  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const gesture = gestureRef.current
    if (!gesture || gesture.pointerId !== event.pointerId || settlingRef.current) {
      return
    }
    const dx = event.clientX - gesture.startX
    const dy = event.clientY - gesture.startY
    if (gesture.axis === 'none') {
      if (Math.abs(dx) < AXIS_LOCK_PX && Math.abs(dy) < AXIS_LOCK_PX) {
        return
      }
      gesture.axis = Math.abs(dx) > Math.abs(dy) ? 'x' : 'y'
      if (gesture.axis === 'y') {
        return
      }
      stageRef.current?.setPointerCapture(event.pointerId)
      setDragging(true)
    }
    if (gesture.axis !== 'x') {
      return
    }
    const stepDt = Math.max(1, event.timeStamp - gesture.lastT)
    gesture.velocity = (event.clientX - gesture.lastX) / stepDt
    gesture.lastX = event.clientX
    gesture.lastT = event.timeStamp
    const nextOffset = resistedOffset(dx, canPrev, canNext)
    offsetRef.current = nextOffset
    setOffset(nextOffset)
  }

  const onPointerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    const gesture = gestureRef.current
    if (!gesture || gesture.pointerId !== event.pointerId) {
      return
    }
    if (stageRef.current?.hasPointerCapture(event.pointerId)) {
      stageRef.current.releasePointerCapture(event.pointerId)
    }
    if (gesture.axis !== 'x' || settlingRef.current) {
      gestureRef.current = null
      setDragging(false)
      return
    }
    const raw = event.clientX - gesture.startX
    const idle = event.timeStamp - gesture.lastT
    const velocity = idle > 80 ? 0 : gesture.velocity
    const width = stageRef.current?.clientWidth ?? 1
    const threshold = Math.max(SNAP_MIN_PX, width * SNAP_RATIO)
    const flickNext = velocity < -FLICK_VELOCITY && raw < -FLICK_MIN_PX
    const flickPrev = velocity > FLICK_VELOCITY && raw > FLICK_MIN_PX
    if ((raw < -threshold || flickNext) && canNext) {
      settleTo(-width, 1)
      return
    }
    if ((raw > threshold || flickPrev) && canPrev) {
      settleTo(width, -1)
      return
    }
    settleTo(0, 0)
  }

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

        <div
          className={`photo-lightbox-stage${dragging ? ' is-dragging' : ''}`}
          ref={stageRef}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
        >
          <div
            className="photo-lightbox-track"
            ref={trackRef}
            style={{
              transform: hasMultiple
                ? `translate3d(calc(-100% + ${offset}px), 0, 0)`
                : `translate3d(${offset}px, 0, 0)`,
              transition:
                dragging || !animating
                  ? 'none'
                  : `transform ${motion.pager.durationMs}ms ${motion.pager.easing}`,
            }}
          >
            {slides.map((slide, slideIndex) => {
              const edge = slideIndex === 0 ? 'prev' : slideIndex === 2 ? 'next' : 'current'
              const current = edge === 'current'
              return (
                <div
                  key={slide ? slide.id : `empty-${edge}`}
                  className="photo-lightbox-slide"
                  aria-hidden={current ? undefined : true}
                >
                  {slide ? (
                    <AttachmentImage
                      className="photo-lightbox-image"
                      entryId={slide.entryId}
                      attachmentId={slide.id}
                      alt={current ? slide.originalName : ''}
                    />
                  ) : null}
                </div>
              )
            })}
          </div>
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
