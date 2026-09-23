import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from 'react'

import { motion } from '../design'
import { useLocale } from '../context/LocaleContext'
import { ArrowDownIcon, ArrowUpIcon } from './icons'
import { IconButton } from './IconButton'

const IGNORE_SELECTOR =
  'a, button, input, textarea, select, [role="slider"], [role="dialog"], .entry-audio-player, .photo-lightbox, .confirm-dialog-backdrop'

const DRAG_LOCK_PX = 8
const EDGE_PX = 12
const SNAP_RATIO = 0.14
const SNAP_PX = 56
const EDGE_HINT_PX = 36
const RUBBER = 0.32

type LockMode = 'none' | 'pager' | 'scroll' | 'ignore'

type EntryReaderPagerProps = {
  hasPrev: boolean
  hasNext: boolean
  /** True when there is no newer entry left to load. */
  reachedStart: boolean
  /** True when there is no older entry left to load. */
  reachedEnd: boolean
  onPrev: () => void
  onNext: () => void
  showDesktopControls: boolean
  prev: ReactNode
  current: ReactNode
  next: ReactNode
}

function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function slideEdges(inner: HTMLElement | null) {
  if (!inner) {
    return { atTop: true, atBottom: true }
  }
  const top = inner.scrollTop
  const max = Math.max(0, inner.scrollHeight - inner.clientHeight)
  return {
    atTop: top <= EDGE_PX,
    atBottom: top >= max - EDGE_PX,
  }
}

function resistance(delta: number) {
  return delta * RUBBER
}

export function EntryReaderPager({
  hasPrev,
  hasNext,
  reachedStart,
  reachedEnd,
  onPrev,
  onNext,
  showDesktopControls,
  prev,
  current,
  next,
}: EntryReaderPagerProps) {
  const { t } = useLocale()
  const viewportRef = useRef<HTMLDivElement>(null)
  const lockRef = useRef<LockMode>('none')
  const startRef = useRef({ x: 0, y: 0, pointerId: -1 })
  const dragOriginRef = useRef(0)
  const dragRef = useRef(0)
  const wheelLockRef = useRef(false)
  const snappingRef = useRef(false)
  const [dragY, setDragY] = useState(0)
  const [snapTo, setSnapTo] = useState<number | null>(null)
  const [edgeHint, setEdgeHint] = useState<'start' | 'end' | null>(null)

  const viewportHeight = () => viewportRef.current?.clientHeight ?? window.innerHeight

  const activeInner = () =>
    viewportRef.current?.querySelector<HTMLElement>('[data-entry-reader-slide="active"]') ?? null

  const resetDrag = useCallback(() => {
    dragRef.current = 0
    dragOriginRef.current = 0
    snappingRef.current = false
    setDragY(0)
    setSnapTo(null)
    setEdgeHint(null)
    lockRef.current = 'none'
  }, [])

  const showBoundaryHint = useCallback((direction: 'prev' | 'next') => {
    if (direction === 'prev' && reachedStart) {
      setEdgeHint('start')
      return true
    }
    if (direction === 'next' && reachedEnd) {
      setEdgeHint('end')
      return true
    }
    return false
  }, [reachedEnd, reachedStart])

  const commit = useCallback(
    (direction: 'prev' | 'next' | 'cancel') => {
      if (snappingRef.current && direction !== 'cancel') {
        return
      }
      const height = viewportHeight()
      if (direction === 'prev' && hasPrev) {
        snappingRef.current = true
        setEdgeHint(null)
        if (prefersReducedMotion()) {
          onPrev()
          resetDrag()
          return
        }
        setSnapTo(height)
        window.setTimeout(() => {
          onPrev()
          resetDrag()
          const slide = activeInner()
          if (slide) {
            slide.scrollTop = 0
          }
        }, motion.pager.durationMs)
        return
      }
      if (direction === 'next' && hasNext) {
        snappingRef.current = true
        setEdgeHint(null)
        if (prefersReducedMotion()) {
          onNext()
          resetDrag()
          return
        }
        setSnapTo(-height)
        window.setTimeout(() => {
          onNext()
          resetDrag()
          const slide = activeInner()
          if (slide) {
            slide.scrollTop = 0
          }
        }, motion.pager.durationMs)
        return
      }
      if (direction === 'prev' || direction === 'next') {
        showBoundaryHint(direction)
      }
      if (prefersReducedMotion()) {
        resetDrag()
        if (direction === 'prev' || direction === 'next') {
          showBoundaryHint(direction)
          window.setTimeout(() => setEdgeHint(null), 900)
        }
        return
      }
      setSnapTo(0)
      window.setTimeout(() => {
        const keepHint = direction === 'prev' || direction === 'next'
        resetDrag()
        if (keepHint) {
          showBoundaryHint(direction)
          window.setTimeout(() => setEdgeHint(null), 900)
        }
      }, motion.pager.durationMs)
    },
    [hasNext, hasPrev, onNext, onPrev, resetDrag, showBoundaryHint],
  )

  const beginPager = (clientY: number, direction: 'prev' | 'next') => {
    lockRef.current = 'pager'
    dragOriginRef.current = clientY
    dragRef.current = 0
    setDragY(0)
    if (direction === 'prev' && !hasPrev) {
      showBoundaryHint('prev')
    } else if (direction === 'next' && !hasNext) {
      showBoundaryHint('next')
    } else {
      setEdgeHint(null)
    }
  }

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0 || snappingRef.current) {
      return
    }
    if (event.target instanceof Element && event.target.closest(IGNORE_SELECTOR)) {
      lockRef.current = 'ignore'
      return
    }
    startRef.current = { x: event.clientX, y: event.clientY, pointerId: event.pointerId }
    lockRef.current = 'none'
    dragOriginRef.current = event.clientY
    dragRef.current = 0
  }

  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (startRef.current.pointerId !== event.pointerId || lockRef.current === 'ignore') {
      return
    }
    const dx = event.clientX - startRef.current.x
    const dy = event.clientY - startRef.current.y

    if (lockRef.current === 'none') {
      if (Math.abs(dx) < DRAG_LOCK_PX && Math.abs(dy) < DRAG_LOCK_PX) {
        return
      }
      if (Math.abs(dx) > Math.abs(dy)) {
        lockRef.current = 'ignore'
        return
      }
      const direction: 'prev' | 'next' = dy > 0 ? 'prev' : 'next'
      const { atTop, atBottom } = slideEdges(activeInner())
      const atEdge = direction === 'prev' ? atTop : atBottom
      if (atEdge) {
        beginPager(event.clientY, direction)
        viewportRef.current?.setPointerCapture(event.pointerId)
      } else {
        lockRef.current = 'scroll'
      }
    }

    if (lockRef.current === 'scroll') {
      const direction: 'prev' | 'next' = dy > 0 ? 'prev' : 'next'
      const { atTop, atBottom } = slideEdges(activeInner())
      const atEdge = direction === 'prev' ? atTop : atBottom
      // Take over once the note is scrolled to an edge and the finger keeps going.
      if (atEdge && Math.abs(dy) > DRAG_LOCK_PX) {
        beginPager(event.clientY, direction)
        viewportRef.current?.setPointerCapture(event.pointerId)
      } else {
        return
      }
    }

    if (lockRef.current !== 'pager') {
      return
    }

    let nextDelta = event.clientY - dragOriginRef.current
    const pullingPrev = nextDelta > 0
    const pullingNext = nextDelta < 0
    if ((pullingPrev && !hasPrev) || (pullingNext && !hasNext)) {
      nextDelta = resistance(nextDelta)
      if (Math.abs(nextDelta) > EDGE_HINT_PX * RUBBER) {
        setEdgeHint(pullingPrev ? 'start' : 'end')
      }
    } else {
      setEdgeHint(null)
    }
    dragRef.current = nextDelta
    setDragY(nextDelta)
  }

  const onPointerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (startRef.current.pointerId !== event.pointerId) {
      return
    }
    if (snappingRef.current) {
      startRef.current.pointerId = -1
      return
    }
    startRef.current.pointerId = -1
    if (lockRef.current !== 'pager') {
      lockRef.current = 'none'
      return
    }
    const height = viewportHeight()
    const threshold = Math.max(SNAP_PX, height * SNAP_RATIO)
    // Compare against raw finger travel; dragY may already include rubber resistance.
    const rawIntent = event.clientY - dragOriginRef.current
    if (rawIntent > threshold && hasPrev) {
      commit('prev')
      return
    }
    if (rawIntent < -threshold && hasNext) {
      commit('next')
      return
    }
    if (rawIntent > EDGE_HINT_PX && !hasPrev) {
      commit('prev')
      return
    }
    if (rawIntent < -EDGE_HINT_PX && !hasNext) {
      commit('next')
      return
    }
    commit('cancel')
  }

  useEffect(() => {
    const node = viewportRef.current
    if (!node) {
      return
    }
    const onTouchMove = (event: TouchEvent) => {
      if (lockRef.current === 'pager') {
        event.preventDefault()
      }
    }
    node.addEventListener('touchmove', onTouchMove, { passive: false })
    return () => node.removeEventListener('touchmove', onTouchMove)
  }, [])

  useEffect(() => {
    const node = viewportRef.current
    if (!node) {
      return
    }
    const onWheel = (event: WheelEvent) => {
      if (event.target instanceof Element && event.target.closest(IGNORE_SELECTOR)) {
        return
      }
      if (wheelLockRef.current || snapTo !== null) {
        event.preventDefault()
        return
      }
      const direction: 'prev' | 'next' = event.deltaY < 0 ? 'prev' : 'next'
      const { atTop, atBottom } = slideEdges(activeInner())
      const atEdge = direction === 'prev' ? atTop : atBottom
      if (!atEdge) {
        return
      }
      if ((direction === 'prev' && !hasPrev) || (direction === 'next' && !hasNext)) {
        event.preventDefault()
        showBoundaryHint(direction)
        window.setTimeout(() => setEdgeHint(null), 900)
        return
      }
      event.preventDefault()
      wheelLockRef.current = true
      commit(direction)
      window.setTimeout(() => {
        wheelLockRef.current = false
      }, motion.pager.lockMs)
    }
    node.addEventListener('wheel', onWheel, { passive: false })
    return () => node.removeEventListener('wheel', onWheel)
  }, [commit, hasNext, hasPrev, showBoundaryHint, snapTo])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLElement) {
        const tag = event.target.tagName
        if (tag === 'INPUT' || tag === 'TEXTAREA' || event.target.isContentEditable) {
          return
        }
      }
      if (event.key === 'ArrowUp' || event.key === 'k' || event.key === 'K' || event.key === 'PageUp') {
        event.preventDefault()
        if (!hasPrev) {
          showBoundaryHint('prev')
          window.setTimeout(() => setEdgeHint(null), 900)
          return
        }
        commit('prev')
        return
      }
      if (
        event.key === 'ArrowDown' ||
        event.key === 'j' ||
        event.key === 'J' ||
        event.key === 'PageDown'
      ) {
        event.preventDefault()
        if (!hasNext) {
          showBoundaryHint('next')
          window.setTimeout(() => setEdgeHint(null), 900)
          return
        }
        commit('next')
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [commit, hasNext, hasPrev, showBoundaryHint])

  // Clear sticky edge hint when feed grows past the boundary.
  useEffect(() => {
    if (edgeHint === 'start' && !reachedStart) {
      setEdgeHint(null)
    }
    if (edgeHint === 'end' && !reachedEnd) {
      setEdgeHint(null)
    }
  }, [edgeHint, reachedEnd, reachedStart])

  const offset = snapTo ?? dragY
  const animating = snapTo !== null
  const hintOpacity = edgeHint
    ? Math.min(1, Math.max(0.45, Math.abs(dragY) / (EDGE_HINT_PX * 1.4) || 0.85))
    : 0

  return (
    <div className="entry-reader-stage">
      <div
        ref={viewportRef}
        className="entry-reader-viewport"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <div
          className={`entry-reader-edge-hint is-start${edgeHint === 'start' ? ' is-visible' : ''}`}
          style={edgeHint === 'start' ? { opacity: hintOpacity } : undefined}
          aria-hidden={edgeHint !== 'start'}
        >
          <ArrowUpIcon />
          <span>{t('entries.readerReachedStart')}</span>
        </div>
        <div
          className={`entry-reader-edge-hint is-end${edgeHint === 'end' ? ' is-visible' : ''}`}
          style={edgeHint === 'end' ? { opacity: hintOpacity } : undefined}
          aria-hidden={edgeHint !== 'end'}
        >
          <span>{t('entries.readerReachedEnd')}</span>
          <ArrowDownIcon />
        </div>
        <div
          className={`entry-reader-track${animating ? ' is-snapping' : ''}`}
          style={{ transform: `translate3d(0, ${offset}px, 0)` }}
        >
          {prev ? (
            <div className="entry-reader-slide is-prev" aria-hidden="true">
              {prev}
            </div>
          ) : null}
          <div className="entry-reader-slide is-current" data-entry-reader-slide="active">
            {current}
          </div>
          {next ? (
            <div className="entry-reader-slide is-next" aria-hidden="true">
              {next}
            </div>
          ) : null}
        </div>
      </div>
      {showDesktopControls ? (
        <div className="entry-reader-desktop-nav">
          <IconButton
            label={t('entries.readerPrevious')}
            onClick={() => commit('prev')}
            disabled={!hasPrev && !reachedStart}
          >
            <ArrowUpIcon />
          </IconButton>
          <IconButton
            label={t('entries.readerNext')}
            onClick={() => commit('next')}
            disabled={!hasNext && !reachedEnd}
          >
            <ArrowDownIcon />
          </IconButton>
        </div>
      ) : null}
    </div>
  )
}
