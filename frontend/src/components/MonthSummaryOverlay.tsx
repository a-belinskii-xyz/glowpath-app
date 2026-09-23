import { useCallback, useEffect, useId, useMemo, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { useColorScheme } from '../hooks/useColorScheme'
import {
  buildGradientWash,
  motion,
  moodGlowBoxShadow,
  withHexAlpha,
  type GradientRecipe,
} from '../design'
import { buildMonthCalendarCells } from '../lib/datetime'
import type {
  CalendarDayPublic,
  MoodInsightPublic,
  MoodEntryStatsResponse,
  MoodRecapItemPublic,
} from '../types/mood'
import type { MoodScoreIconType, MoodScoreStylePublic } from '../types/moodPreferences'
import { GoalIcon } from './GoalIcon'
import { HeartIcon } from './HeartIcon'
import { MoodScoreIcon } from './MoodScoreIcon'
import { TagIcon } from './TagIcon'

type RecapPhase = 'form' | 'orbit' | 'reveal'
type RecapVariant = 'planet' | 'moons' | 'mosaic' | 'cover' | 'silk'
type RecapSatKind = 'mood' | 'tag' | 'goal'

const VARIANT_KEY = 'mood-tracker.recap-look'
const VARIANTS: RecapVariant[] = ['planet', 'moons', 'mosaic', 'cover', 'silk']

const COVER_WASH: GradientRecipe = {
  washStrength: 0.38,
  chromaScale: 0.92,
  orderPower: 1.12,
  angleDeg: 158,
  midStopMinColors: 3,
  targetL: 1,
}

const COVER_WASH_DARK: GradientRecipe = {
  ...COVER_WASH,
  washStrength: 0.62,
  chromaScale: 0.7,
  targetL: 0.28,
}

type LitDay = {
  date: string
  entryCount: number
  score: number
  color: string
}

type RecapSatellite = {
  key: string
  kind: RecapSatKind
  label: string
  color: string
  count: number
  ring: number
  angle: number
  size: number
  icon_type: MoodScoreIconType
  icon: string
  score?: number
}

type MonthSummaryOverlayProps = {
  open: boolean
  monthLabel: string
  year: number
  month: number
  stats: MoodEntryStatsResponse
  days?: CalendarDayPublic[]
  highlight?: MoodInsightPublic | null
  onClose: () => void
}

function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
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

function readVariant(): RecapVariant {
  try {
    const stored = window.localStorage.getItem(VARIANT_KEY)
    if (
      stored === 'planet' ||
      stored === 'moons' ||
      stored === 'mosaic' ||
      stored === 'cover' ||
      stored === 'silk'
    ) {
      return stored
    }
  } catch {
    /* ignore */
  }
  return 'planet'
}

function planetScale(
  stats: MoodEntryStatsResponse,
  compact = false,
): { size: string; glow: number } {
  const density = Math.min(1, Math.max(0.28, stats.active_days / 22))
  const energy = Math.min(1, Math.max(0.32, Math.sqrt(Math.max(1, stats.total_entries)) / 7))
  const mix = density * 0.62 + energy * 0.38
  if (compact) {
    return {
      size: `${(7.6 + mix * 2.6).toFixed(2)}rem`,
      glow: Number((0.36 + mix * 0.48).toFixed(3)),
    }
  }
  return {
    size: `${(12.8 + mix * 5.4).toFixed(2)}rem`,
    glow: Number((0.42 + mix * 0.58).toFixed(3)),
  }
}

const SAT_EDGE_GAP = 0.72

function satSize(count: number, kind: RecapSatKind): number {
  const base = kind === 'mood' ? 2.9 : 2.7
  return Number((base + Math.min(0.4, Math.sqrt(Math.max(1, count)) * 0.16)).toFixed(2))
}

function ringCapacity(radius: number, itemSize: number): number {
  const slot = itemSize + SAT_EDGE_GAP
  return Math.max(1, Math.floor((2 * Math.PI * radius) / slot))
}

function placeOnRing<T extends { count: number; kind: RecapSatKind }>(
  items: T[],
  ring: number,
  phase: number,
): RecapSatellite[] {
  const count = items.length
  if (count === 0) {
    return []
  }
  const step = 360 / count
  return items.map((item, index) => ({
    ...item,
    ring,
    angle: phase + index * step,
    size: satSize(item.count, item.kind),
  })) as unknown as RecapSatellite[]
}

function persistVariant(variant: RecapVariant): void {
  try {
    window.localStorage.setItem(VARIANT_KEY, variant)
  } catch {
    /* ignore */
  }
}

function dominantScore(
  scores: { score: number; count?: number; score_color?: string }[],
): { score: number; color?: string } {
  const first = scores[0]
  if (!first) {
    return { score: 3 }
  }
  return { score: first.score, color: first.score_color }
}

function collectLitDays(
  days: CalendarDayPublic[],
  stats: MoodEntryStatsResponse,
  getScoreColor: (score: number) => string,
): LitDay[] {
  const fromCalendar = [...days]
    .filter((day) => day.entry_count > 0)
    .sort((left, right) => left.date.localeCompare(right.date))
    .map((day) => {
      const top = dominantScore(day.scores)
      return {
        date: day.date,
        entryCount: day.entry_count,
        score: top.score,
        color: top.color ?? getScoreColor(top.score),
      }
    })
  if (fromCalendar.length > 0) {
    return fromCalendar
  }
  return (stats.weeks ?? [])
    .filter((week) => week.entry_count > 0)
    .map((week) => {
      const ranked = [...week.scores].sort((left, right) => right.count - left.count)
      const top = ranked[0]
      const score = top?.score ?? 3
      return {
        date: `week-${week.week}`,
        entryCount: week.entry_count,
        score,
        color: getScoreColor(score),
      }
    })
}

function chunkWeeks<T>(cells: T[]): T[][] {
  const weeks: T[][] = []
  for (let index = 0; index < cells.length; index += 7) {
    weeks.push(cells.slice(index, index + 7))
  }
  return weeks
}

function sampleColors(days: LitDay[], max = 8): string[] {
  if (days.length === 0) {
    return []
  }
  if (days.length <= max) {
    return days.map((day) => day.color)
  }
  return Array.from({ length: max }, (_, index) => {
    const at = Math.round((index / Math.max(1, max - 1)) * (days.length - 1))
    return days[at]?.color ?? days[0].color
  })
}

function collectSatelliteSeeds(
  stats: MoodEntryStatsResponse,
  getScoreStyle: (score: number) => MoodScoreStylePublic,
) {
  const moods = stats.scores
    .filter((item) => item.count > 0)
    .slice(0, 5)
    .map((item) => {
      const style = getScoreStyle(item.score)
      return {
        key: `mood-${item.score}`,
        kind: 'mood' as const,
        label: item.score_label || style.label,
        color: style.color,
        count: item.count,
        icon_type: style.icon_type,
        icon: style.icon,
        score: item.score,
      }
    })
  const tags = (stats.tags ?? []).slice(0, 6).map((item) => ({
    key: `tag-${item.id}`,
    kind: 'tag' as const,
    label: item.label,
    color: item.color,
    count: item.count,
    icon_type: item.icon_type,
    icon: item.icon,
  }))
  const goals = (stats.goals ?? []).slice(0, 5).map((item) => ({
    key: `goal-${item.id}`,
    kind: 'goal' as const,
    label: item.label,
    color: item.color,
    count: item.count,
    icon_type: item.icon_type,
    icon: item.icon,
  }))
  return { moods, tags, goals }
}

function maxSatSize(
  items: { count: number; kind: RecapSatKind }[],
  fallback: number,
): number {
  if (items.length === 0) {
    return fallback
  }
  return Math.max(...items.map((item) => satSize(item.count, item.kind)))
}

function buildMoonRings(
  stats: MoodEntryStatsResponse,
  getScoreStyle: (score: number) => MoodScoreStylePublic,
  coreRem: number,
) {
  const seeds = collectSatelliteSeeds(stats, getScoreStyle)
  const moodSize = maxSatSize(seeds.moods, 2.9)
  const tagSize = maxSatSize(seeds.tags, 2.7)
  const goalSize = maxSatSize(seeds.goals, 2.7)
  const r0 = coreRem / 2 + 0.95 + moodSize / 2 + SAT_EDGE_GAP
  const r1 = r0 + moodSize / 2 + tagSize / 2 + SAT_EDGE_GAP
  const r2 = r1 + tagSize / 2 + goalSize / 2 + SAT_EDGE_GAP
  const moods = seeds.moods.slice(0, ringCapacity(r0, moodSize))
  const tags = seeds.tags.slice(0, ringCapacity(r1, tagSize))
  const goals = seeds.goals.slice(0, ringCapacity(r2, goalSize))
  return [
    {
      id: 0,
      radius: r0,
      duration: '38s',
      reverse: false,
      items: placeOnRing(moods, 0, -10),
    },
    {
      id: 1,
      radius: r1,
      duration: '52s',
      reverse: false,
      items: placeOnRing(tags, 1, 26),
    },
    {
      id: 2,
      radius: r2,
      duration: '68s',
      reverse: false,
      items: placeOnRing(goals, 2, 48),
    },
  ]
}

export function MonthSummaryOverlay({
  open,
  monthLabel,
  year,
  month,
  stats,
  days = [],
  highlight = null,
  onClose,
}: MonthSummaryOverlayProps) {
  const { t, tp } = useLocale()
  const { getScoreColor, getScoreStyle } = useMoodPreferences()
  const colorScheme = useColorScheme()
  const titleId = useId()
  const closeRef = useRef<HTMLButtonElement>(null)
  const openStatsRef = useRef<HTMLButtonElement>(null)
  const openedRef = useRef(false)
  const [phase, setPhase] = useState<RecapPhase>('form')
  const [variant, setVariant] = useState<RecapVariant>(readVariant)

  const litDays = useMemo(
    () => collectLitDays(days, stats, getScoreColor),
    [days, getScoreColor, stats],
  )
  const litByDate = useMemo(() => {
    const map = new Map<string, LitDay>()
    for (const day of litDays) {
      map.set(day.date, day)
    }
    return map
  }, [litDays])
  const cells = useMemo(() => buildMonthCalendarCells(year, month), [month, year])
  const weeks = useMemo(() => chunkWeeks(cells), [cells])
  const featuredTags = (stats.tags ?? []).slice(0, 3)
  const coverWash = useMemo(() => {
    const colors = sampleColors(litDays)
    return colors.length > 0
      ? buildGradientWash(colors, colorScheme === 'dark' ? COVER_WASH_DARK : COVER_WASH)
      : null
  }, [colorScheme, litDays])
  const auroraColors = useMemo(() => {
    const used = sampleColors(litDays, 4)
    const fallback = ['#60a5fa', '#34d399', '#94a3b8', '#f59e0b']
    const palette = [...used, ...fallback].slice(0, 4)
    return {
      ['--recap-c1' as string]: withHexAlpha(palette[0] ?? fallback[0], 0xb8),
      ['--recap-c2' as string]: withHexAlpha(palette[1] ?? fallback[1], 0x9e),
      ['--recap-c3' as string]: withHexAlpha(palette[2] ?? fallback[2], 0x8c),
      ['--recap-c4' as string]: withHexAlpha(palette[3] ?? fallback[3], 0x7a),
    } as CSSProperties
  }, [litDays])

  const planetLook = useMemo(
    () => planetScale(stats, variant === 'moons'),
    [stats, variant],
  )
  const moonRings = useMemo(
    () => buildMoonRings(stats, getScoreStyle, Number.parseFloat(planetLook.size)),
    [getScoreStyle, planetLook.size, stats],
  )

  const openStats = useCallback(() => {
    openedRef.current = true
    setPhase('reveal')
  }, [])

  const chooseVariant = useCallback((next: RecapVariant) => {
    setVariant(next)
    persistVariant(next)
  }, [])

  useEffect(() => {
    if (!open) {
      openedRef.current = false
      setPhase('form')
      return
    }

    const reduced = prefersReducedMotion()
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    if (reduced) {
      openedRef.current = true
      setPhase('reveal')
      closeRef.current?.focus()
      return () => {
        document.body.style.overflow = previousOverflow
      }
    }

    openedRef.current = false
    openStatsRef.current?.focus()
    const orbit = window.setTimeout(() => {
      if (!openedRef.current) {
        setPhase('orbit')
      }
    }, motion.recap.formMs)
    return () => {
      window.clearTimeout(orbit)
      document.body.style.overflow = previousOverflow
    }
  }, [open])

  useEffect(() => {
    if (phase === 'reveal') {
      closeRef.current?.focus()
    }
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
      onClose()
    }
    document.addEventListener('keydown', onKeyDown, true)
    return () => document.removeEventListener('keydown', onKeyDown, true)
  }, [onClose, open])

  if (!open) {
    return null
  }

  const moodChips = stats.scores.filter((item) => item.count > 0)
  const favoriteCount = stats.favorite_count ?? 0
  const waitingForClick = phase !== 'reveal'
  const isPlanetLook = variant === 'planet' || variant === 'moons'
  const tileStagger = Math.min(38, 720 / Math.max(1, cells.filter((cell) => cell.inMonth).length))

  return createPortal(
    <div
      className={`month-recap-backdrop is-${phase} is-${colorScheme}`}
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
          if (waitingForClick) {
            openStats()
            return
          }
          onClose()
        }}
      >
        <h2 id={titleId} className="visually-hidden">
          {t('monthSummary.kicker')} {monthLabel}
        </h2>
        <div className="month-recap-toolbar">
          {waitingForClick ? (
            <div className="month-recap-variants" role="radiogroup" aria-label={t('monthSummary.variants')}>
              {VARIANTS.map((item) => (
                <button
                  key={item}
                  type="button"
                  role="radio"
                  aria-checked={variant === item}
                  className={`month-recap-variant${variant === item ? ' is-current' : ''}`}
                  onClick={() => chooseVariant(item)}
                >
                  {t(`monthSummary.variant.${item}`)}
                </button>
              ))}
            </div>
          ) : (
            <span />
          )}
          <div className="month-recap-toolbar-end">
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

        {isPlanetLook ? (
          <div className={`month-recap-planet-scene${variant === 'moons' ? ' is-moons' : ''}`}>
            <div
              className="month-recap-planet-rig"
              style={
                {
                  ['--planet-size' as string]: planetLook.size,
                  ['--planet-glow' as string]: planetLook.glow,
                } as CSSProperties
              }
            >
              <span className="month-recap-planet-bloom is-outer" />
              <span className="month-recap-planet-bloom is-mid" />
              {variant === 'moons'
                ? moonRings.map((ring) =>
                    ring.items.length > 0 ? (
                      <div
                        key={ring.id}
                        className={`month-recap-orbit-ring${ring.reverse ? ' is-reverse' : ''}`}
                        style={
                          {
                            ['--orbit-r' as string]: `${ring.radius.toFixed(2)}rem`,
                            ['--orbit-dur' as string]: ring.duration,
                          } as CSSProperties
                        }
                      >
                        {ring.items.map((item, index) => (
                          <button
                            key={item.key}
                            type="button"
                            className={`month-recap-sat is-${item.kind}`}
                            style={
                              {
                                ['--sat-a' as string]: `${item.angle.toFixed(1)}deg`,
                                ['--sat-size' as string]: `${item.size}rem`,
                                ['--sat-color' as string]: item.color,
                                ['--sat-delay' as string]: `${160 + ring.id * 90 + index * 55}ms`,
                              } as CSSProperties
                            }
                            title={`${item.label} · ${item.count}`}
                            aria-label={`${item.label} · ${item.count}`}
                          >
                            <span className="month-recap-sat-face">
                              <RecapSatIcon item={item} getScoreStyle={getScoreStyle} />
                            </span>
                          </button>
                        ))}
                      </div>
                    ) : null,
                  )
                : null}
              <span className="month-recap-planet-ring" />
              <span className="month-recap-planet-core">
                <span className="month-recap-planet-body" />
                <span className="month-recap-planet-bands" />
                <span className="month-recap-planet-spec" />
              </span>
            </div>
            <p className="month-recap-planet-name">{monthLabel}</p>
          </div>
        ) : (
        <article className={`month-recap-poster is-${variant}`}>
          {variant === 'cover' && coverWash ? (
            <div className="month-recap-cover-wash" style={coverWash} aria-hidden="true" />
          ) : null}

          <header className="month-recap-poster-top">
            <p className="month-recap-poster-brand">{t('brand')}</p>
            <p className="month-recap-poster-kicker">{t('monthSummary.kicker')}</p>
            <h3 className="month-recap-poster-title">{monthLabel}</h3>
          </header>

          {variant === 'mosaic' ? (
            <div className="month-recap-mosaic" aria-hidden="true">
              <div className="month-recap-mosaic-grid">
                {cells.map((cell, index) => {
                  const lit = cell.inMonth ? litByDate.get(cell.date) : undefined
                  const delay = cell.inMonth
                    ? 60 + cells.slice(0, index).filter((item) => item.inMonth).length * tileStagger
                    : 0
                  return (
                    <span
                      key={cell.key}
                      className={`month-recap-tile${cell.inMonth ? '' : ' is-pad'}${lit ? ' is-lit' : ''}`}
                      style={
                        {
                          ['--tile-delay' as string]: `${delay}ms`,
                          ...(lit
                            ? {
                                background: lit.color,
                                boxShadow: moodGlowBoxShadow(
                                  lit.color,
                                  lit.entryCount > 2 ? 'md' : 'sm',
                                ),
                              }
                            : {}),
                        } as CSSProperties
                      }
                    />
                  )
                })}
              </div>
            </div>
          ) : null}

          {variant === 'silk' ? (
            <div className="month-recap-silk" aria-hidden="true">
              {weeks
                .filter((week) => week.some((cell) => cell.inMonth))
                .map((week, weekIndex) => (
                  <div
                    key={week[0]?.key ?? weekIndex}
                    className="month-recap-ribbon"
                    style={{ ['--ribbon-delay' as string]: `${180 + weekIndex * 90}ms` } as CSSProperties}
                  >
                    {week.map((cell) => {
                      const lit = cell.inMonth ? litByDate.get(cell.date) : undefined
                      return (
                        <span
                          key={cell.key}
                          className={`month-recap-ribbon-seg${cell.inMonth ? '' : ' is-pad'}${lit ? ' is-lit' : ''}`}
                          style={
                            lit
                              ? {
                                  background: lit.color,
                                  boxShadow: moodGlowBoxShadow(lit.color, 'sm'),
                                }
                              : undefined
                          }
                        />
                      )
                    })}
                  </div>
                ))}
            </div>
          ) : null}

          {variant === 'cover' ? (
            <div className="month-recap-cover-body">
              <p className="month-recap-cover-hero">{stats.active_days}</p>
              <p className="month-recap-cover-hero-label">{t('monthSummary.coverDays')}</p>
              <div className="month-recap-cover-spine" aria-hidden="true">
                {litDays.length > 0
                  ? litDays.map((day) => (
                      <span
                        key={day.date}
                        style={{
                          background: day.color,
                          flexGrow: Math.max(1, day.entryCount),
                        }}
                      />
                    ))
                  : null}
              </div>
            </div>
          ) : null}

          <footer className="month-recap-poster-foot">
            {featuredTags.length > 0 ? (
              <div className="month-recap-poster-tags">
                {featuredTags.map((item) => (
                  <span
                    key={item.id}
                    className="month-recap-poster-tag"
                    style={{ color: item.color }}
                  >
                    <TagIcon
                      style={{
                        color: item.color,
                        icon_type: item.icon_type,
                        icon: item.icon,
                      }}
                      className="month-recap-chip-icon"
                    />
                    {item.label}
                  </span>
                ))}
              </div>
            ) : litDays.length === 0 ? (
              <p className="month-recap-poster-empty">{t('monthSummary.pathEmpty')}</p>
            ) : (
              <span />
            )}
            <p className="month-recap-poster-meta">
              {tp(stats.total_entries, {
                one: 'monthSummary.entriesOne',
                few: 'monthSummary.entriesFew',
                many: 'monthSummary.entriesMany',
              })}
            </p>
          </footer>
        </article>
        )}

        {waitingForClick && !isPlanetLook ? (
          <p className="month-recap-share-hint">{t('monthSummary.shareHint')}</p>
        ) : null}

        {waitingForClick ? (
          <button
            ref={openStatsRef}
            type="button"
            className="month-recap-open-cta"
            onClick={openStats}
          >
            {t('monthSummary.openStats')}
          </button>
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
                <RecapNamedChip key={item.id} item={item} />
              ))
            )}
          </RecapChipRow>

          <RecapChipRow label={t('monthSummary.goals')}>
            {stats.goals.length === 0 ? (
              <span className="muted">{t('monthSummary.emptyGoals')}</span>
            ) : (
              stats.goals.slice(0, 8).map((item) => (
                <RecapNamedChip key={item.id} item={item} />
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

function RecapSatIcon({
  item,
  getScoreStyle,
}: {
  item: RecapSatellite
  getScoreStyle: (score: number) => MoodScoreStylePublic
}) {
  if (item.kind === 'mood') {
    return (
      <MoodScoreIcon
        style={getScoreStyle(item.score ?? 3)}
        className="month-recap-chip-icon"
        fallbackScore={item.score ?? 3}
      />
    )
  }
  if (item.kind === 'goal') {
    return (
      <GoalIcon
        style={{ color: item.color, icon_type: item.icon_type, icon: item.icon }}
        className="month-recap-chip-icon"
      />
    )
  }
  return (
    <TagIcon
      style={{ color: item.color, icon_type: item.icon_type, icon: item.icon }}
      className="month-recap-chip-icon"
    />
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

function RecapNamedChip({ item }: { item: MoodRecapItemPublic }) {
  return (
    <span className="month-recap-chip" title={item.label} style={{ color: item.color }}>
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
