import { useEffect, useRef, useState } from 'react'

import { useLocale } from '../context/LocaleContext'
import {
  BOOT_CARD_MS,
  BOOT_RETRY_AFTER_SEC,
  bootPhaseIndex,
  bootProgressPercent,
} from '../lib/bootProgress'

const PHASE_KEYS = [
  'boot.phaseSpace',
  'boot.phaseSync',
  'boot.phaseWake',
  'boot.phaseSleep',
  'boot.phaseAlmost',
] as const

const CARD_KEYS = [
  'boot.cardRegularity',
  'boot.cardPhotos',
  'boot.cardSmall',
  'boot.cardPace',
  'boot.cardHere',
  'boot.cardWeek',
] as const

type AppBootLoaderProps = {
  pending: boolean
  exiting: boolean
  onRetry: () => void
}

export function AppBootLoader({ pending, exiting, onRetry }: AppBootLoaderProps) {
  const { t } = useLocale()
  const [phase, setPhase] = useState(0)
  const [card, setCard] = useState(0)
  const [showRetry, setShowRetry] = useState(false)
  const [percent, setPercent] = useState(0)
  const fillRef = useRef<HTMLDivElement>(null)
  const startedRef = useRef(0)

  useEffect(() => {
    startedRef.current = performance.now()
    let raf = 0
    let stopped = false

    const paint = (elapsedSec: number) => {
      const value = bootProgressPercent(elapsedSec, !pending)
      const node = fillRef.current
      if (node) {
        node.style.transform = `scaleX(${value / 100})`
      }
      const nextPercent = Math.round(value)
      setPercent((current) => (current === nextPercent ? current : nextPercent))
    }

    const tick = (now: number) => {
      if (stopped) {
        return
      }
      const elapsedSec = (now - startedRef.current) / 1000
      paint(elapsedSec)
      const nextPhase = bootPhaseIndex(elapsedSec)
      setPhase((current) => (current === nextPhase ? current : nextPhase))
      const retryVisible = elapsedSec >= BOOT_RETRY_AFTER_SEC
      setShowRetry((current) => (current === retryVisible ? current : retryVisible))
      raf = window.requestAnimationFrame(tick)
    }

    if (!pending) {
      paint(0)
      const node = fillRef.current
      if (node) {
        node.style.transform = 'scaleX(1)'
      }
      setPercent(100)
      return
    }

    raf = window.requestAnimationFrame(tick)
    return () => {
      stopped = true
      window.cancelAnimationFrame(raf)
    }
  }, [pending])

  useEffect(() => {
    const timer = window.setInterval(() => {
      setCard((current) => (current + 1) % CARD_KEYS.length)
    }, BOOT_CARD_MS)
    return () => window.clearInterval(timer)
  }, [])

  return (
    <div
      className={`boot-loader${exiting ? ' is-exiting' : ''}`}
      role="status"
      aria-live="polite"
      aria-busy={pending}
    >
      <div className="boot-loader-glow" aria-hidden="true">
        <span className="boot-loader-halo" />
        <span className="boot-loader-core" />
      </div>
      <p className="boot-loader-phase" key={phase}>
        {t(PHASE_KEYS[phase] ?? PHASE_KEYS[PHASE_KEYS.length - 1])}
      </p>
      <div
        className="boot-progress"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-label={t('boot.progressLabel')}
      >
        <div className="boot-progress-fill" ref={fillRef} />
      </div>
      <p className="boot-loader-card" key={card}>
        {t(CARD_KEYS[card])}
      </p>
      {showRetry && pending ? (
        <p className="boot-loader-retry">
          <span>{t('boot.slowHint')}</span>{' '}
          <button type="button" className="boot-loader-retry-button" onClick={onRetry}>
            {t('boot.retry')}
          </button>
        </p>
      ) : null}
    </div>
  )
}
