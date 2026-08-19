import { useCallback, useEffect, useId, useMemo, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { motion, moodGlowFilter, withHexAlpha } from '../design'
import {
  isRecapSoundMuted,
  persistRecapSoundMuted,
  startRecapSound,
  type RecapHoverKind,
  type RecapSoundHandle,
} from '../lib/recapSound'
import type { MoodInsightPublic, MoodEntryStatsResponse, MoodRecapItemPublic } from '../types/mood'
import type { MoodScoreIconType } from '../types/moodPreferences'
import { GoalIcon } from './GoalIcon'
import { HeartIcon } from './HeartIcon'
import { SoundOffIcon, SoundOnIcon } from './icons'
import { MoodScoreIcon } from './MoodScoreIcon'
import { TagIcon } from './TagIcon'

type RecapPhase = 'form' | 'orbit' | 'reveal'

type ParticleKind = 'mood' | 'tag' | 'goal'

type RecapSatellite = {
  key: string
  kind: ParticleKind
  label: string
  color: string
  icon_type: MoodScoreIconType
  icon: string
  score?: number
  angle: number
  delayMs: number
  size: number
}

type RecapRing = {
  key: string
  radius: string
  duration: string
  reverse: boolean
  items: RecapSatellite[]
}

type MonthSummaryOverlayProps = {
  open: boolean
  monthLabel: string
  stats: MoodEntryStatsResponse
  highlight?: MoodInsightPublic | null
  onClose: () => void
}

function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function unitNoise(seed: number): number {
  const value = Math.sin(seed * 12.9898) * 43758.5453
  return value - Math.floor(value)
}

function comparisonClassName(verdict: MoodEntryStatsResponse['comparison']['verdict']): string {
  switch (verdict) {
    case 'much_better':
    case 'better':
      return 'month-recap-comparison is-better'
    case 'much_worse':
    case 'worse':
      return 'month-recap-comparison is-worse'
    case 'similar':
      return 'month-recap-comparison is-similar'
    default:
      return 'month-recap-comparison is-muted'
  }
}

function typicalMood(stats: MoodEntryStatsResponse): number {
  if (stats.month_index != null) {
    return stats.month_index
  }
  let weighted = 0
  let total = 0
  for (const item of stats.scores) {
    weighted += item.score * item.count
    total += item.count
  }
  return total > 0 ? weighted / total : 3
}

export function MonthSummaryOverlay({
  open,
  monthLabel,
  stats,
  highlight = null,
  onClose,
}: MonthSummaryOverlayProps) {
  const { t, tp } = useLocale()
  const { getScoreColor, getScoreStyle } = useMoodPreferences()
  const titleId = useId()
  const closeRef = useRef<HTMLButtonElement>(null)
  const skippedRef = useRef(false)
  const soundRef = useRef<RecapSoundHandle | null>(null)
  const [phase, setPhase] = useState<RecapPhase>('form')
  const [soundMuted, setSoundMuted] = useState(isRecapSoundMuted)
  const [soundAvailable, setSoundAvailable] = useState(false)

  const rings = useMemo(
    () => buildRings(stats, getScoreColor, getScoreStyle),
    [getScoreColor, getScoreStyle, stats],
  )
  const auroraColors = useMemo(() => {
    const used = stats.scores.filter((item) => item.count > 0).map((item) => getScoreColor(item.score))
    const fallback = ['#60a5fa', '#34d399', '#94a3b8', '#f59e0b']
    const palette = [...used, ...fallback].slice(0, 4)
    return {
      ['--recap-c1' as string]: withHexAlpha(palette[0] ?? fallback[0], 0xb8),
      ['--recap-c2' as string]: withHexAlpha(palette[1] ?? fallback[1], 0x9e),
      ['--recap-c3' as string]: withHexAlpha(palette[2] ?? fallback[2], 0x8c),
      ['--recap-c4' as string]: withHexAlpha(palette[3] ?? fallback[3], 0x7a),
    } as CSSProperties
  }, [getScoreColor, stats.scores])

  const skipToReveal = useCallback(() => {
    skippedRef.current = true
    setPhase('reveal')
  }, [])

  const toggleSound = useCallback(() => {
    const next = !soundMuted
    persistRecapSoundMuted(next)
    setSoundMuted(next)
    soundRef.current?.setMuted(next)
  }, [soundMuted])

  const playHover = useCallback((kind: RecapHoverKind, id: string) => {
    soundRef.current?.playHover(kind, id)
  }, [])

  useEffect(() => {
    if (!open) {
      skippedRef.current = false
      setPhase('form')
      return
    }

    const reduced = prefersReducedMotion()
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    closeRef.current?.focus()

    if (reduced) {
      skippedRef.current = true
      setPhase('reveal')
      setSoundAvailable(false)
      return () => {
        document.body.style.overflow = previousOverflow
      }
    }

    skippedRef.current = false
    const { formMs, orbitMs } = motion.recap
    const handle = startRecapSound({
      seed: stats.total_entries * 13 + stats.active_days * 7,
      mood: typicalMood(stats),
      muted: isRecapSoundMuted(),
      orbitMs,
    })
    soundRef.current = handle
    setSoundAvailable(handle !== null)
    setSoundMuted(isRecapSoundMuted())
    const orbit = window.setTimeout(() => {
      if (!skippedRef.current) {
        setPhase('orbit')
      }
    }, formMs)
    const reveal = window.setTimeout(() => {
      if (!skippedRef.current) {
        setPhase('reveal')
      }
    }, formMs + orbitMs)
    return () => {
      window.clearTimeout(orbit)
      window.clearTimeout(reveal)
      soundRef.current?.stop(true)
      soundRef.current = null
      document.body.style.overflow = previousOverflow
    }
  }, [open])

  useEffect(() => {
    soundRef.current?.setPhase(phase)
  }, [phase])

  useEffect(() => {
    if (!open) {
      return
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') {
        return
      }
      event.preventDefault()
      event.stopImmediatePropagation()
      if (phase !== 'reveal') {
        skipToReveal()
        return
      }
      onClose()
    }
    document.addEventListener('keydown', onKeyDown, true)
    return () => document.removeEventListener('keydown', onKeyDown, true)
  }, [onClose, open, phase, skipToReveal])

  if (!open) {
    return null
  }

  const moodChips = stats.scores.filter((item) => item.count > 0)
  const favoriteCount = stats.favorite_count ?? 0
  const showSkip = phase !== 'reveal'

  return createPortal(
    <div
      className={`month-recap-backdrop is-${phase}`}
      style={auroraColors}
      role="presentation"
    >
      <div className="month-recap-aurora" aria-hidden="true" />

      <div
        className="month-recap-stage"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onMouseDown={(event) => {
          const target = event.target as HTMLElement
          if (target.closest('button') || target.closest('.month-recap-card')) {
            return
          }
          if (phase !== 'reveal') {
            skipToReveal()
            return
          }
          onClose()
        }}
      >
        <h2 id={titleId} className="visually-hidden">
          {t('monthSummary.kicker')} {monthLabel}
        </h2>
        <div className="month-recap-toolbar">
          {showSkip ? (
            <button type="button" className="button button-secondary button-small" onClick={skipToReveal}>
              {t('monthSummary.skip')}
            </button>
          ) : (
            <span />
          )}
          <div className="month-recap-toolbar-end">
            {soundAvailable ? (
              <button
                type="button"
                className="month-recap-sound"
                onClick={toggleSound}
                aria-pressed={!soundMuted}
                aria-label={soundMuted ? t('monthSummary.soundOn') : t('monthSummary.soundOff')}
              >
                {soundMuted ? <SoundOffIcon /> : <SoundOnIcon />}
              </button>
            ) : null}
            <button
              ref={closeRef}
              type="button"
              className="month-recap-close"
              onClick={onClose}
              aria-label={t('monthSummary.close')}
            >
              ×
            </button>
          </div>
        </div>

        <div className="month-recap-cosmos" aria-hidden={phase === 'reveal'}>
          <div className="month-recap-orb-mist" />
          <div className="month-recap-orb">
            <span className="month-recap-orb-blob is-a" />
            <span className="month-recap-orb-blob is-b" />
            <span className="month-recap-orb-blob is-c" />
            <span className="month-recap-orb-glass" />
          </div>
          {rings.map((ring) => (
            <div
              key={ring.key}
              className={`month-recap-orbit${ring.reverse ? ' is-reverse' : ''}`}
              style={
                {
                  ['--orbit-dur' as string]: ring.duration,
                  ['--sat-r' as string]: ring.radius,
                } as CSSProperties
              }
            >
              {ring.items.map((item) => (
                <span
                  key={item.key}
                  className={`month-recap-sat is-${item.kind}`}
                  style={
                    {
                      ['--sat-a' as string]: `${item.angle}deg`,
                      ['--sat-delay' as string]: `${item.delayMs}ms`,
                      ['--sat-size' as string]: `${item.size}rem`,
                      ['--mood-color' as string]: item.color,
                      color: item.color,
                      filter: moodGlowFilter(item.color),
                    } as CSSProperties
                  }
                  title={item.label}
                  onMouseEnter={() => playHover(item.kind, item.key)}
                  onMouseDown={(event) => event.stopPropagation()}
                >
                  <span className="month-recap-sat-face">
                    <RecapParticleIcon particle={item} />
                  </span>
                </span>
              ))}
            </div>
          ))}
        </div>

        {phase !== 'reveal' ? (
          <p className="month-recap-status">{t('monthSummary.orbiting')}</p>
        ) : null}

        <section className="month-recap-card" aria-live="polite" aria-hidden={phase !== 'reveal'}>
          <header className="month-recap-card-header">
            <p className="month-recap-kicker">{t('monthSummary.kicker')}</p>
            <h2 className="month-recap-title">{monthLabel}</h2>
          </header>
          <p className={comparisonClassName(stats.comparison.verdict)}>{stats.comparison.message}</p>

          <dl className="month-recap-metrics">
            <div>
              <dt>{t('monthSummary.metricEntries')}</dt>
              <dd>
                {tp(stats.total_entries, {
                  one: 'monthSummary.entriesOne',
                  few: 'monthSummary.entriesFew',
                  many: 'monthSummary.entriesMany',
                })}
              </dd>
            </div>
            <div>
              <dt>{t('monthSummary.metricDays')}</dt>
              <dd>
                {tp(stats.active_days, {
                  one: 'monthSummary.daysOne',
                  few: 'monthSummary.daysFew',
                  many: 'monthSummary.daysMany',
                })}
              </dd>
            </div>
            <div>
              <dt>{t('monthSummary.metricFavorites')}</dt>
              <dd>
                <HeartIcon filled={favoriteCount > 0} />
                {tp(favoriteCount, {
                  one: 'monthSummary.favoritesOne',
                  few: 'monthSummary.favoritesFew',
                  many: 'monthSummary.favoritesMany',
                })}
              </dd>
            </div>
          </dl>

          {moodChips.length > 0 ? (
            <RecapChipRow label={t('monthSummary.moods')}>
              {moodChips.map((item) => {
                const style = getScoreStyle(item.score)
                return (
                  <span
                    key={item.score}
                    className="month-recap-chip"
                    title={item.score_label}
                    onMouseEnter={() => playHover('mood', `mood-${item.score}`)}
                  >
                    <MoodScoreIcon style={style} className="month-recap-chip-icon" fallbackScore={item.score} />
                    <span>{item.count}</span>
                  </span>
                )
              })}
            </RecapChipRow>
          ) : null}

          <RecapChipRow label={t('monthSummary.tags')}>
            {stats.tags.length === 0 ? (
              <span className="muted">{t('monthSummary.emptyTags')}</span>
            ) : (
              stats.tags.slice(0, 8).map((item) => (
                <RecapNamedChip key={item.id} item={item} onHover={playHover} />
              ))
            )}
          </RecapChipRow>

          <RecapChipRow label={t('monthSummary.goals')}>
            {stats.goals.length === 0 ? (
              <span className="muted">{t('monthSummary.emptyGoals')}</span>
            ) : (
              stats.goals.slice(0, 8).map((item) => (
                <RecapNamedChip key={item.id} item={item} onHover={playHover} />
              ))
            )}
          </RecapChipRow>

          {highlight ? (
            <blockquote className="month-recap-insight">
              <p className="month-recap-insight-title">{highlight.title}</p>
              <p>{highlight.body}</p>
            </blockquote>
          ) : null}
        </section>
      </div>
    </div>,
    document.body,
  )
}

function RecapChipRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="month-recap-row">
      <h3 className="month-recap-row-title">{label}</h3>
      <div className="month-recap-chips">{children}</div>
    </div>
  )
}

function RecapNamedChip({
  item,
  onHover,
}: {
  item: MoodRecapItemPublic
  onHover: (kind: RecapHoverKind, id: string) => void
}) {
  const kind: RecapHoverKind = item.kind === 'goal' ? 'goal' : 'tag'
  return (
    <span
      className="month-recap-chip"
      title={item.label}
      style={{ color: item.color }}
      onMouseEnter={() => onHover(kind, `${kind}-${item.id}`)}
    >
      {item.kind === 'goal' ? (
        <GoalIcon
          style={{ color: item.color, icon_type: item.icon_type, icon: item.icon }}
          className="month-recap-chip-icon"
        />
      ) : (
        <TagIcon
          style={{ color: item.color, icon_type: item.icon_type, icon: item.icon }}
          className="month-recap-chip-icon"
        />
      )}
      <span className="month-recap-chip-label">{item.label}</span>
      <span>{item.count}</span>
    </span>
  )
}

function RecapParticleIcon({
  particle,
}: {
  particle: Pick<RecapSatellite, 'kind' | 'color' | 'icon_type' | 'icon' | 'label' | 'score'>
}) {
  if (particle.kind === 'mood' && particle.score != null) {
    return (
      <MoodScoreIcon
        style={{
          color: particle.color,
          icon_type: particle.icon_type,
          icon: particle.icon,
          label: particle.label,
        }}
        className="month-recap-particle-icon"
        fallbackScore={particle.score}
      />
    )
  }
  if (particle.kind === 'goal') {
    return (
      <GoalIcon
        style={{ color: particle.color, icon_type: particle.icon_type, icon: particle.icon }}
        className="month-recap-particle-icon"
      />
    )
  }
  return (
    <TagIcon
      style={{ color: particle.color, icon_type: particle.icon_type, icon: particle.icon }}
      className="month-recap-particle-icon"
    />
  )
}

function placeOnRing<T>(
  items: T[],
  toSat: (item: T, index: number, angle: number) => RecapSatellite,
  seed: number,
): RecapSatellite[] {
  const count = items.length
  return items.map((item, index) => {
    const jitter = (unitNoise(seed + index * 11) - 0.5) * (count > 2 ? 14 : 0)
    const angle = (360 / Math.max(1, count)) * index + jitter
    return toSat(item, index, angle)
  })
}

function buildRings(
  stats: MoodEntryStatsResponse,
  getScoreColor: (score: number) => string,
  getScoreStyle: (score: number) => { color: string; icon_type: MoodScoreIconType; icon: string; label: string },
): RecapRing[] {
  const seed = stats.total_entries * 13 + stats.active_days * 7
  const moods = stats.scores.filter((item) => item.count > 0)
  const tags = stats.tags.slice(0, 8)
  const goals = stats.goals.slice(0, 6)

  const rings: RecapRing[] = []

  if (moods.length > 0) {
    rings.push({
      key: 'moods',
      radius: '6.5rem',
      duration: '38s',
      reverse: false,
      items: placeOnRing(
        moods,
        (item, index, angle) => {
          const style = getScoreStyle(item.score)
          return {
            key: `mood-${item.score}`,
            kind: 'mood',
            label: item.score_label,
            color: getScoreColor(item.score),
            icon_type: style.icon_type,
            icon: style.icon,
            score: item.score,
            angle,
            delayMs: 160 + index * 80,
            size: 1.85,
          }
        },
        seed,
      ),
    })
  }

  if (tags.length > 0) {
    rings.push({
      key: 'tags',
      radius: '8.7rem',
      duration: '52s',
      reverse: true,
      items: placeOnRing(
        tags,
        (item, index, angle) => ({
          key: `tag-${item.id}`,
          kind: 'tag',
          label: item.label,
          color: item.color,
          icon_type: item.icon_type,
          icon: item.icon,
          angle,
          delayMs: 240 + index * 70,
          size: 1.55,
        }),
        seed + 19,
      ),
    })
  }

  if (goals.length > 0) {
    rings.push({
      key: 'goals',
      radius: '10.7rem',
      duration: '68s',
      reverse: false,
      items: placeOnRing(
        goals,
        (item, index, angle) => ({
          key: `goal-${item.id}`,
          kind: 'goal',
          label: item.label,
          color: item.color,
          icon_type: item.icon_type,
          icon: item.icon,
          angle,
          delayMs: 320 + index * 80,
          size: 1.55,
        }),
        seed + 41,
      ),
    })
  }

  return rings
}
