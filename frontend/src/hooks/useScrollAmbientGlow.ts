import { useEffect, useMemo, useRef } from 'react'

import { ambientPaletteKey } from '../design'
import { useAmbientGlow } from '../context/AmbientGlowContext'

type GlowSource = {
  /** Element id used as IntersectionObserver target (without #). */
  id: string
  colors: string[]
}

/**
 * Observe glow sources (day sections / entries) and update shell ambient glow
 * from the most visible palette in the viewport.
 */
export function useScrollAmbientGlow(sources: GlowSource[], enabled = true) {
  const { setAmbientPalette } = useAmbientGlow()
  const sourcesRef = useRef(sources)
  sourcesRef.current = sources

  const ratiosRef = useRef(new Map<string, number>())
  const lastKeyRef = useRef('')
  const sourceIdsKey = useMemo(() => sources.map((s) => s.id).join('|'), [sources])

  useEffect(() => {
    if (!enabled) {
      setAmbientPalette(null)
      lastKeyRef.current = ''
      ratiosRef.current.clear()
      return
    }

    const applyBest = () => {
      // Prefer the strongest intersection; fall back to first source so the
      // shell always picks up a mood palette once the feed mounts.
      const ranked = [...ratiosRef.current.entries()]
        .filter(([, ratio]) => ratio > 0)
        .sort((a, b) => b[1] - a[1])

      const bestId = ranked[0]?.[0] ?? ''
      const source =
        (bestId ? sourcesRef.current.find((s) => s.id === bestId) : null) ??
        sourcesRef.current[0]
      const colors = source?.colors ?? []
      const key = ambientPaletteKey(colors)
      if (key === lastKeyRef.current) {
        return
      }
      lastKeyRef.current = key
      setAmbientPalette(colors)
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const id = entry.target.id
          if (!id) {
            continue
          }
          // Keep a mild score even when barely visible so scroll still tracks.
          const score = entry.isIntersecting
            ? Math.max(entry.intersectionRatio, 0.05)
            : 0
          ratiosRef.current.set(id, score)
        }
        applyBest()
      },
      {
        root: null,
        // Upper half of the viewport leads the glow (where the eye rests).
        rootMargin: '-8% 0px -45% 0px',
        threshold: [0, 0.05, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 1],
      },
    )

    const observed = new Map<string, Element>()

    const syncTargets = () => {
      const wanted = new Set(sourcesRef.current.map((s) => s.id))
      for (const [id, node] of observed) {
        if (!wanted.has(id)) {
          observer.unobserve(node)
          observed.delete(id)
          ratiosRef.current.delete(id)
        }
      }
      for (const source of sourcesRef.current) {
        if (observed.has(source.id)) {
          continue
        }
        const node = document.getElementById(source.id)
        if (!node) {
          continue
        }
        observed.set(source.id, node)
        observer.observe(node)
      }
      applyBest()
    }

    syncTargets()
    const raf = window.requestAnimationFrame(syncTargets)
    // Infinite scroll mounts new day sections after the initial paint.
    const interval = window.setInterval(syncTargets, 800)

    return () => {
      window.cancelAnimationFrame(raf)
      window.clearInterval(interval)
      observer.disconnect()
      ratiosRef.current.clear()
      lastKeyRef.current = ''
      setAmbientPalette(null)
    }
  }, [enabled, setAmbientPalette, sourceIdsKey])

  // When palette contents change for existing ids, re-apply without remounting observer.
  useEffect(() => {
    if (!enabled || sources.length === 0) {
      return
    }
    const ranked = [...ratiosRef.current.entries()]
      .filter(([, ratio]) => ratio > 0)
      .sort((a, b) => b[1] - a[1])
    const bestId = ranked[0]?.[0] ?? ''
    const source =
      (bestId ? sources.find((s) => s.id === bestId) : null) ?? sources[0]
    const colors = source?.colors ?? []
    const key = ambientPaletteKey(colors)
    if (key !== lastKeyRef.current) {
      lastKeyRef.current = key
      setAmbientPalette(colors)
    }
  }, [enabled, sources, setAmbientPalette])
}
