import { useEffect, useId, useMemo, useRef, type CSSProperties, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { withHexAlpha } from '../design'
import { useColorScheme } from '../hooks/useColorScheme'
import { intlLocale } from '../i18n/t'
import { MAX_MOOD, MIN_MOOD, buildMonthRecap, formatRecapDate, weekdayNames } from '../lib/monthRecap'
import type { CalendarDayPublic, MoodEntryStatsResponse, MoodInsightPublic } from '../types/mood'
import { HeartIcon } from './HeartIcon'
import {
  RecapCalendar,
  RecapMoodFlow,
  RecapMoodMix,
  RecapTopList,
  RecapWeekRhythm,
} from './monthRecap/RecapCharts'
import { MoodScoreIcon } from './MoodScoreIcon'
import { TagIcon } from './TagIcon'

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

type Verdict = MoodEntryStatsResponse['comparison']['verdict']

function verdictTone(verdict: Verdict): 'up' | 'down' | 'flat' | 'none' {
  switch (verdict) {
    case 'much_better':
    case 'better':
      return 'up'
    case 'much_worse':
    case 'worse':
      return 'down'
    case 'similar':
      return 'flat'
    default:
      return 'none'
  }
}

const VERDICT_ARROW = { up: '↑', down: '↓', flat: '→', none: '' } as const

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
  const { t, tp, locale } = useLocale()
  const { getScoreStyle } = useMoodPreferences()
  const colorScheme = useColorScheme()
  const titleId = useId()
  const gradientId = `recap-flow-${useId().replace(/:/g, '')}`
  const closeRef = useRef<HTMLButtonElement>(null)
  const dateLocale = intlLocale(locale)

  const data = useMemo(() => buildMonthRecap(stats, days, year, month), [days, month, stats, year])

  useEffect(() => {
    if (!open) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    closeRef.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      event.preventDefault()
      event.stopImmediatePropagation()
      onClose()
    }
    document.addEventListener('keydown', onKeyDown, true)
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', onKeyDown, true)
    }
  }, [onClose, open])

  if (!open) return null

  const dominantStyle = data.dominantScore === null ? null : getScoreStyle(data.dominantScore)
  const heroColor = dominantStyle?.color ?? '#60a5fa'
  const tone = verdictTone(stats.comparison.verdict)
  const number = new Intl.NumberFormat(dateLocale)
  const moodNumber = new Intl.NumberFormat(dateLocale, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })
  const topTag = stats.tags[0]
  const favoriteCount = stats.favorite_count ?? 0
  const longWeekdays = weekdayNames(dateLocale, 'long')
  const showFlow = data.days.length >= 2
  const showRhythm = data.bestWeekday !== null

  const glow = {
    '--recap-hero': heroColor,
    '--recap-glow-a': withHexAlpha(heroColor, 0x66),
    '--recap-glow-b': withHexAlpha(getScoreStyle(data.bestDay?.score ?? MAX_MOOD).color, 0x44),
  } as CSSProperties

  const moments: { key: string; icon: ReactNode; text: string }[] = []
  if (data.bestDay) {
    moments.push({
      key: 'best-day',
      icon: (
        <MoodScoreIcon
          style={getScoreStyle(data.bestDay.score)}
          className="recap-moment-icon"
          fallbackScore={data.bestDay.score}
        />
      ),
      text: t('monthSummary.momentBestDay', { date: formatRecapDate(data.bestDay.date, dateLocale) }),
    })
  }
  if (data.bestWeekday) {
    moments.push({
      key: 'weekday',
      icon: <span className="recap-moment-glyph">☀</span>,
      text: t('monthSummary.momentWeekday', { day: longWeekdays[data.bestWeekday.weekday] }),
    })
  }
  if (topTag) {
    moments.push({
      key: 'tag',
      icon: (
        <TagIcon
          style={{ color: topTag.color, icon_type: topTag.icon_type, icon: topTag.icon }}
          className="recap-moment-icon"
        />
      ),
      text: t('monthSummary.momentTag', { tag: topTag.label }),
    })
  }

  const kpis: { key: string; label: string; value: string; unit: string; meter?: number; icon?: ReactNode }[] = [
    {
      key: 'days',
      label: t('monthSummary.metricDays'),
      value: number.format(stats.active_days),
      unit: t('monthSummary.ofDays', { total: data.daysInMonth }),
      meter: stats.active_days / data.daysInMonth,
    },
    {
      key: 'entries',
      label: t('monthSummary.metricEntries'),
      value: number.format(stats.total_entries),
      unit: '',
    },
    {
      key: 'streak',
      label: t('monthSummary.metricStreak'),
      value: number.format(data.longestStreak),
      unit: tp(data.longestStreak, {
        one: 'monthSummary.streakDaysOne',
        few: 'monthSummary.streakDaysFew',
        many: 'monthSummary.streakDaysMany',
      }),
    },
    {
      key: 'favorites',
      label: t('monthSummary.metricFavorites'),
      value: number.format(favoriteCount),
      unit: '',
      icon: <HeartIcon filled={favoriteCount > 0} />,
    },
  ]

  let sectionIndex = 0
  const section = (key: string, title: string, lead: string | null, body: ReactNode) => {
    sectionIndex += 1
    return (
      <section
        key={key}
        className="recap-section"
        style={{ '--section-delay': `${260 + sectionIndex * 110}ms` } as CSSProperties}
        aria-label={title}
      >
        <header className="recap-section-head">
          <h3>{title}</h3>
          {lead ? <p>{lead}</p> : null}
        </header>
        {body}
      </section>
    )
  }

  return createPortal(
    <div
      className={`recap-backdrop is-${colorScheme}`}
      style={glow}
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div className="recap-sheet" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <button
          ref={closeRef}
          type="button"
          className="recap-close"
          onClick={onClose}
          aria-label={t('monthSummary.close')}
        >
          ×
        </button>

        <header className="recap-hero">
          <span className="recap-hero-glow" aria-hidden="true" />
          <p className="recap-kicker">
            {t('brand')} · {t('monthSummary.kicker')}
          </p>
          <h2 id={titleId} className="recap-title">
            {monthLabel}
          </h2>

          {dominantStyle && data.dominantScore !== null ? (
            <div className="recap-medallion" aria-hidden="true">
              <span className="recap-medallion-ring" />
              <MoodScoreIcon
                style={dominantStyle}
                className="recap-medallion-icon"
                fallbackScore={data.dominantScore}
              />
            </div>
          ) : null}

          <p className="recap-headline">
            {dominantStyle
              ? t('monthSummary.headline', { mood: dominantStyle.label })
              : t('monthSummary.headlineEmpty')}
          </p>

          {data.averageMood !== null ? (
            <div className="recap-meter">
              <div className="recap-meter-track">
                {[1, 2, 3, 4, 5].map((score) => (
                  <span key={score} style={{ background: getScoreStyle(score).color }} />
                ))}
                <i
                  className="recap-meter-marker"
                  style={{
                    left: `${((data.averageMood - MIN_MOOD) / (MAX_MOOD - MIN_MOOD)) * 100}%`,
                  }}
                />
              </div>
              <p className="recap-meter-caption">
                {t('monthSummary.averageMood', {
                  value: moodNumber.format(data.averageMood),
                  max: MAX_MOOD,
                })}
              </p>
            </div>
          ) : null}

          {tone !== 'none' ? (
            <p className={`recap-compare is-${tone}`}>
              <span aria-hidden="true">{VERDICT_ARROW[tone]}</span>
              {stats.comparison.message}
            </p>
          ) : null}

          {moments.length > 0 ? (
            <ul className="recap-moments">
              {moments.map((item) => (
                <li key={item.key}>
                  {item.icon}
                  <span>{item.text}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </header>

        <dl className="recap-kpis">
          {kpis.map((item, index) => (
            <div
              key={item.key}
              className="recap-kpi"
              style={{ '--kpi-delay': `${160 + index * 70}ms` } as CSSProperties}
            >
              <dt>{item.label}</dt>
              <dd>
                <span className="recap-kpi-value">
                  {item.icon}
                  {item.value}
                </span>
                {item.unit ? <span className="recap-kpi-unit">{item.unit}</span> : null}
                {item.meter !== undefined ? (
                  <span className="recap-kpi-meter" aria-hidden="true">
                    <span style={{ width: `${Math.min(1, item.meter) * 100}%` }} />
                  </span>
                ) : null}
              </dd>
            </div>
          ))}
        </dl>

        {section(
          'calendar',
          t('monthSummary.calendarTitle'),
          t('monthSummary.calendarLead'),
          <RecapCalendar data={data} year={year} month={month} scoreStyle={getScoreStyle} />,
        )}

        {showFlow
          ? section(
              'flow',
              t('monthSummary.flowTitle'),
              t('monthSummary.flowLead'),
              <RecapMoodFlow data={data} scoreStyle={getScoreStyle} gradientId={gradientId} />,
            )
          : null}

        {data.moodMix.length > 0
          ? section(
              'mix',
              t('monthSummary.mixTitle'),
              null,
              <RecapMoodMix data={data} scoreStyle={getScoreStyle} />,
            )
          : null}

        {showRhythm && data.bestWeekday
          ? section(
              'rhythm',
              t('monthSummary.rhythmTitle'),
              t('monthSummary.rhythmLead', { day: longWeekdays[data.bestWeekday.weekday] }),
              <RecapWeekRhythm data={data} scoreStyle={getScoreStyle} />,
            )
          : null}

        {stats.tags.length > 0 || stats.goals.length > 0 ? (
          <div className="recap-pair">
            {stats.tags.length > 0
              ? section('tags', t('monthSummary.tags'), null, <RecapTopList items={stats.tags} kind="tag" />)
              : null}
            {stats.goals.length > 0
              ? section('goals', t('monthSummary.goals'), null, <RecapTopList items={stats.goals} kind="goal" />)
              : null}
          </div>
        ) : null}

        {highlight
          ? section(
              'insight',
              t('monthSummary.insightTitle'),
              null,
              <blockquote className="recap-insight">
                <p className="recap-insight-title">{highlight.title}</p>
                <p>{highlight.body}</p>
              </blockquote>,
            )
          : null}

        <footer className="recap-footer">
          <p>{t('monthSummary.outro')}</p>
          <button type="button" className="button" onClick={onClose}>
            {t('monthSummary.done')}
          </button>
        </footer>
      </div>
    </div>,
    document.body,
  )
}
