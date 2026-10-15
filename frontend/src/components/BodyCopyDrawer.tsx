import { useEffect, useState } from 'react'

import { listFood, listSleep, listWeights } from '../api/body'
import { listMoodEntries } from '../api/moodEntries'
import { EditorDrawer } from './EditorDrawer'
import { PageErrorAlert } from './PageErrorAlert'
import { StableButtonLabel } from './StableButtonLabel'
import { useLocale } from '../context/LocaleContext'
import { intlLocale } from '../i18n/t'
import { bodyMassIndex, copyToClipboard, dayNumber, formatDay } from '../lib/bodyFormat'
import { dayKey, getDayBounds, shiftDateKey } from '../lib/datetime'
import { formatApiError } from '../lib/errors'
import { formatDuration, toNight } from '../lib/sleep'
import type { BodySettings, Meal, WeightPoint } from '../types/body'

const MEALS: Meal[] = ['morning', 'day', 'evening', 'snack']
const MAX_DAYS = 365
type CopyPeriod = 'today' | 'week' | 'month' | 'custom'
const COPY_PERIODS: CopyPeriod[] = ['today', 'week', 'month', 'custom']
type Part = 'food' | 'sleep' | 'weight' | 'bmi' | 'mood'
const PARTS: Part[] = ['food', 'sleep', 'weight', 'bmi', 'mood']
const MOOD_PAGE = 100
const MOOD_PAGES_MAX = 20

async function loadMoodLabels(from: string, to: string, timeZone: string): Promise<Map<string, string[]>> {
  const byDay = new Map<string, string[]>()
  const recorded_from = getDayBounds(from, timeZone).recorded_from
  const recorded_to = getDayBounds(to, timeZone).recorded_to
  for (let page = 0; page < MOOD_PAGES_MAX; page += 1) {
    const response = await listMoodEntries({ recorded_from, recorded_to, limit: MOOD_PAGE, offset: page * MOOD_PAGE })
    for (const entry of response.items) {
      const day = dayKey(entry.recorded_at, timeZone)
      byDay.set(day, [...(byDay.get(day) ?? []), entry.score_label])
    }
    if (response.items.length < MOOD_PAGE) break
  }
  // The list is newest first; read each day from morning to evening.
  for (const labels of byDay.values()) labels.reverse()
  return byDay
}

/** The average of the weights in the 7 days ending on ``day``. */
function weekAverage(points: WeightPoint[], day: string): number | null {
  const end = dayNumber(day)
  const window = points.filter((point) => dayNumber(point.day) <= end && dayNumber(point.day) > end - 7)
  if (window.length === 0) return null
  return window.reduce((sum, point) => sum + point.value, 0) / window.length
}

type BodyCopyDrawerProps = {
  open: boolean
  today: string
  timeZone: string
  settings: BodySettings
  onClose: () => void
}

/** Body notes for a period as plain text, ready to paste into a chat with an assistant. */
export function BodyCopyDrawer({ open, today, timeZone, settings, onClose }: BodyCopyDrawerProps) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const [period, setPeriod] = useState<CopyPeriod>('week')
  const [customFrom, setCustomFrom] = useState(shiftDateKey(today, -6))
  const [customTo, setCustomTo] = useState(today)
  const [parts, setParts] = useState<Part[]>([])
  const [text, setText] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const offered = PARTS.filter((part) => {
    if (part === 'food') return settings.show_food
    if (part === 'sleep') return settings.show_sleep
    if (part === 'weight') return settings.show_weight
    if (part === 'bmi') return settings.show_weight && settings.height_cm !== null
    return true
  })

  useEffect(() => {
    if (!open) return
    // Start with what the card shows; BMI only when asked for.
    setParts(offered.filter((part) => part !== 'bmi'))
    // Only on opening.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const [from, to] = (() => {
    if (period === 'today') return [today, today]
    if (period === 'week') return [shiftDateKey(today, -6), today]
    if (period === 'month') return [shiftDateKey(today, -29), today]
    return customFrom <= customTo ? [customFrom, customTo] : [customTo, customFrom]
  })()
  const tooLong = dayNumber(to) - dayNumber(from) > MAX_DAYS
  const partsKey = parts.join(',')

  useEffect(() => {
    if (!open || tooLong) return
    const has = (part: Part) => partsKey.split(',').includes(part)
    let cancelled = false
    const build = async () => {
      setIsLoading(true)
      setError(null)
      try {
        // BMI uses the week before the period too, so its first days have an average.
        const [food, sleep, weights, moods] = await Promise.all([
          has('food') ? listFood(from, to) : Promise.resolve([]),
          has('sleep') ? listSleep(from, to) : Promise.resolve([]),
          has('weight') || has('bmi') ? listWeights(shiftDateKey(from, -6), to) : Promise.resolve([]),
          has('mood') ? loadMoodLabels(from, to, timeZone) : Promise.resolve(new Map<string, string[]>()),
        ])
        if (cancelled) return
        const numberFormat = new Intl.NumberFormat(dateLocale, { maximumFractionDigits: 1 })
        const rangeFormat = new Intl.DateTimeFormat(dateLocale, {
          day: 'numeric',
          month: 'long',
          year: 'numeric',
          timeZone: 'UTC',
        })
        const asDate = (day: string) => new Date(dayNumber(day) * 86_400_000)
        const startFormat = new Intl.DateTimeFormat(dateLocale, {
          day: 'numeric',
          month: 'long',
          ...(from.slice(0, 4) === to.slice(0, 4) ? {} : { year: 'numeric' }),
          timeZone: 'UTC',
        })
        const range =
          from === to
            ? rangeFormat.format(asDate(from))
            : `${startFormat.format(asDate(from))} – ${rangeFormat.format(asDate(to))}`
        const inPeriod = weights.filter((point) => point.day >= from)
        const lines = [t('body.copyHeading', { range }), t('body.copyGaps')]
        const height = settings.height_cm
        const average = weekAverage(weights, to)
        if (has('bmi') && height !== null && average !== null) {
          lines.push(
            t('body.copyBmi', {
              value: numberFormat.format(bodyMassIndex(average, height)),
              height: numberFormat.format(height),
            }),
          )
        }
        const days = [
          ...new Set([
            ...food.map((log) => log.day),
            ...sleep.map((log) => log.day),
            ...(has('weight') ? inPeriod.map((point) => point.day) : []),
            ...[...moods.keys()].filter((day) => day >= from && day <= to),
          ]),
        ].sort()
        for (const day of days) {
          const heading = formatDay(day, dateLocale, { weekday: 'short', day: 'numeric', month: 'long' })
          lines.push('', heading.charAt(0).toUpperCase() + heading.slice(1))
          const night = sleep.find((log) => log.day === day)
          if (night) {
            const span = toNight(night)
            const times = [
              t('body.copySleepBed', { time: night.bed_time.slice(0, 5) }),
              t('body.copySleepWake', { time: night.wake_time.slice(0, 5) }),
              ...(night.up_time ? [t('body.copySleepUp', { time: night.up_time.slice(0, 5) })] : []),
            ].join(', ')
            let line = t('body.copySleep', { times, duration: formatDuration(t, span.sleep) })
            if (night.quality) line += `, ${t(`body.copyQuality.${night.quality}`)}`
            if (night.note) line += `. ${night.note}`
            lines.push(line)
          }
          const meals = food
            .filter((log) => log.day === day)
            .sort((a, b) => (a.meal ? MEALS.indexOf(a.meal) : MEALS.length) - (b.meal ? MEALS.indexOf(b.meal) : MEALS.length))
          for (const log of meals) {
            // List-mode notes are one item per line; keep each meal on one line.
            const eaten = log.text.split('\n').join('; ')
            lines.push(log.meal ? `- ${t(`body.meal.${log.meal}`)}: ${eaten}` : `- ${eaten}`)
          }
          const extra: string[] = []
          const weight = has('weight') ? inPeriod.find((point) => point.day === day) : undefined
          if (weight) extra.push(t('body.copyWeight', { value: numberFormat.format(weight.value) }))
          const mood = moods.get(day)
          if (mood?.length) extra.push(t('body.copyMood', { labels: mood.join(', ') }))
          if (extra.length > 0) lines.push(extra.join(' · '))
        }
        setText(lines.length <= 2 ? '' : lines.join('\n'))
      } catch (err) {
        if (!cancelled) setError(formatApiError(err, t, 'errors.requestFailed'))
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }
    void build()
    return () => {
      cancelled = true
    }
  }, [open, from, to, tooLong, partsKey, settings.height_cm, timeZone, dateLocale, t])

  useEffect(() => setCopied(false), [text])

  return (
    <EditorDrawer
      open={open}
      title={t('body.copyTitle')}
      description={t('body.copyHint')}
      onClose={onClose}
      footer={
        <div className="button-row">
          <button
            type="button"
            className="button my-primary"
            disabled={!text || isLoading || tooLong}
            onClick={() => void copyToClipboard(text).then(() => setCopied(true))}
          >
            <StableButtonLabel
              active={copied ? t('body.copied') : t('body.copyAction')}
              labels={[t('body.copyAction'), t('body.copied')]}
            />
          </button>
        </div>
      }
    >
      <div className="form">
        <PageErrorAlert error={error} />
        <div className="body-meals" role="radiogroup" aria-label={t('body.copyPeriod')}>
          {COPY_PERIODS.map((item) => (
            <button
              key={item}
              type="button"
              role="radio"
              aria-checked={period === item}
              className={`body-meal${period === item ? ' is-selected' : ''}`}
              onClick={() => setPeriod(item)}
            >
              {t(`body.copyPeriods.${item}`)}
            </button>
          ))}
        </div>
        {period === 'custom' ? (
          <div className="body-copy-dates">
            <input
              className="form-input"
              type="date"
              max={today}
              value={customFrom}
              aria-label={t('body.copyFrom')}
              onChange={(event) => event.target.value && setCustomFrom(event.target.value)}
            />
            <span className="muted">—</span>
            <input
              className="form-input"
              type="date"
              max={today}
              value={customTo}
              aria-label={t('body.copyTo')}
              onChange={(event) => event.target.value && setCustomTo(event.target.value)}
            />
          </div>
        ) : null}
        <div className="body-copy-options">
          {offered.map((part) => (
            <label key={part} className="body-check">
              <input
                type="checkbox"
                checked={parts.includes(part)}
                onChange={(event) =>
                  setParts((current) =>
                    event.target.checked
                      ? PARTS.filter((item) => item === part || current.includes(item))
                      : current.filter((item) => item !== part),
                  )
                }
              />
              <span>{t(`body.copyParts.${part}`)}</span>
            </label>
          ))}
        </div>
        {tooLong ? (
          <p className="my-empty">{t('body.copyTooLong')}</p>
        ) : parts.length === 0 ? (
          <p className="my-empty">{t('body.copyPick')}</p>
        ) : isLoading && !text ? (
          <p className="muted">{t('common.loading')}</p>
        ) : text ? (
          <pre className="body-copy-preview">{text}</pre>
        ) : (
          <p className="my-empty">{t('body.copyEmpty')}</p>
        )}
      </div>
    </EditorDrawer>
  )
}
