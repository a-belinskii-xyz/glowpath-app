import { type FormEvent, useEffect, useState } from 'react'

import { deleteSleep, setSleep } from '../api/body'
import { EditorDrawer } from './EditorDrawer'
import { PageErrorAlert } from './PageErrorAlert'
import { StableButtonLabel } from './StableButtonLabel'
import { useLocale } from '../context/LocaleContext'
import { intlLocale } from '../i18n/t'
import { dayNumber, formatDay } from '../lib/bodyFormat'
import { shiftDateKey } from '../lib/datetime'
import { formatApiError } from '../lib/errors'
import { type Night, averageNights, formatDuration, nightClock, normalizeClock, toNight, typeClock } from '../lib/sleep'
import type { SleepLog, SleepQuality } from '../types/body'

const QUALITIES: SleepQuality[] = ['hard', 'ok', 'good']
const RANGES = { month: 31, quarter: 92, year: 365 } as const
type Range = keyof typeof RANGES

/** Hour ticks covering the nights, two or four hours apart. */
function hourTicks(nights: Night[]): { start: number; end: number; ticks: number[] } {
  const start = Math.floor(Math.min(...nights.map((night) => night.bed)) / 120) * 120
  const end = Math.ceil(Math.max(...nights.map((night) => night.up ?? night.wake)) / 120) * 120
  const step = end - start > 10 * 60 ? 240 : 120
  const ticks: number[] = []
  for (let value = start; value <= end; value += step) ticks.push(value)
  return { start, end: Math.max(end, start + 60), ticks }
}

type SleepSectionProps = {
  logs: SleepLog[]
  asOf: string
  today: string
  weekDays: string[]
  onRecord: () => void
}

/** Sleep on «Моё» (GP-48): averages for the last 7 nights and the week as bars, no "8 hours" norm. */
export function SleepSection({ logs, asOf, today, weekDays, onRecord }: SleepSectionProps) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const nights = logs.map(toNight)
  const recent = nights.filter((night) => night.day <= asOf && dayNumber(night.day) > dayNumber(asOf) - 7)
  const average = averageNights(recent)
  const week = nights.filter((night) => night.day >= weekDays[0] && night.day <= weekDays[6])
  const scale = week.length > 0 ? hourTicks(week) : null
  const at = (minutes: number) => scale ? ((minutes - scale.start) / (scale.end - scale.start)) * 100 : 0

  return (
    <div className="body-sleep">
      <div className="body-food-head">
        <strong>{t('body.sleepTitle')}</strong>
        {average ? <span className="body-label">{t('body.sleepAverage')}</span> : null}
      </div>
      {average ? (
        <>
          <div className="body-sleep-times">
            <div>
              <span className="body-label">{t('body.sleepBed')}</span>
              <strong>{nightClock(average.bed)}</strong>
            </div>
            <div>
              <span className="body-label">{t('body.sleepWake')}</span>
              <strong>{nightClock(average.wake)}</strong>
            </div>
            {average.up !== null ? (
              <div>
                <span className="body-label">{t('body.sleepUp')}</span>
                <strong>{nightClock(average.up)}</strong>
              </div>
            ) : null}
          </div>
          <p className="body-label">
            {t('body.sleepAbout', { duration: formatDuration(t, average.sleep) })}
            {average.lying ? ` · ${t('body.sleepLying', { duration: formatDuration(t, average.lying) })}` : ''}
          </p>
        </>
      ) : (
        <p className="my-empty">{t('body.sleepEmpty')}</p>
      )}
      {scale ? (
        <div className="body-sleep-week" aria-hidden>
          {weekDays
            .filter((day) => day <= today)
            .map((day) => {
              const night = week.find((item) => item.day === day)
              return (
                <div key={day} className="body-sleep-row">
                  <span className="body-sleep-day">{formatDay(day, dateLocale, { weekday: 'short' })}</span>
                  <span className="body-sleep-track">
                    {night ? (
                      <>
                        <span
                          className="body-sleep-bar"
                          style={{ left: `${at(night.bed)}%`, width: `${at(night.wake) - at(night.bed)}%` }}
                        />
                        {night.up !== null && night.lying > 0 ? (
                          <span
                            className="body-sleep-tail"
                            style={{ left: `${at(night.wake)}%`, width: `${at(night.up) - at(night.wake)}%` }}
                          />
                        ) : null}
                      </>
                    ) : null}
                  </span>
                </div>
              )
            })}
          <div className="body-sleep-row body-sleep-axis">
            <span className="body-sleep-day" />
            <span className="body-sleep-track">
              {scale.ticks.map((tick, index) => (
                <span
                  key={tick}
                  // The last label hangs left of its tick so it stays inside the card.
                  style={{ left: `${at(tick)}%`, transform: index === scale.ticks.length - 1 ? 'translateX(-100%)' : undefined }}
                >
                  {nightClock(tick)}
                </span>
              ))}
            </span>
          </div>
        </div>
      ) : null}
      <button type="button" className="button button-secondary body-wide" onClick={onRecord}>
        {t('body.sleepRecord')}
      </button>
    </div>
  )
}

/** Nights as vertical bars over a month to a year: asleep in one tone, lying after waking lighter. */
function SleepChart({ nights, from, to }: { nights: Night[]; from: string; to: string }) {
  if (nights.length === 0) return null
  const { start, end, ticks } = hourTicks(nights)
  const width = 360
  const height = 170
  const left = 40
  const plot = width - left - 4
  const first = dayNumber(from)
  const span = Math.max(dayNumber(to) - first, 1)
  const slot = plot / (span + 1)
  const barWidth = Math.max(slot * 0.65, 1)
  const x = (day: string) => left + (dayNumber(day) - first) * slot + (slot - barWidth) / 2
  const y = (minutes: number) => 6 + ((minutes - start) / (end - start)) * (height - 12)
  return (
    <svg className="body-chart-svg" viewBox={`0 0 ${width} ${height}`} width="100%" aria-hidden>
      {ticks.map((tick) => (
        <g key={tick}>
          <line className="body-sleep-grid" x1={left} x2={width - 4} y1={y(tick)} y2={y(tick)} />
          <text className="body-sleep-tick" x={left - 6} y={y(tick) + 4} textAnchor="end">
            {nightClock(tick)}
          </text>
        </g>
      ))}
      {nights.map((night) => (
        <g key={night.day}>
          <rect
            className="body-sleep-bar-svg"
            x={x(night.day)}
            y={y(night.bed)}
            width={barWidth}
            height={Math.max(y(night.wake) - y(night.bed), 1)}
            rx={Math.min(barWidth / 2, 3)}
          />
          {night.up !== null && night.lying > 0 ? (
            <rect
              className="body-sleep-tail-svg"
              x={x(night.day)}
              y={y(night.wake)}
              width={barWidth}
              height={y(night.up) - y(night.wake)}
              rx={Math.min(barWidth / 2, 3)}
            />
          ) : null}
        </g>
      ))}
    </svg>
  )
}

type SleepDrawerProps = {
  open: boolean
  today: string
  logs: SleepLog[]
  onClose: () => void
  onChanged: () => Promise<void>
}

const DEFAULT_TIMES = { bed: '23:00', wake: '07:00', up: '' }

type ClockFieldProps = {
  label: string
  value: string
  required?: boolean
  onChange: (value: string) => void
}

/**
 * A plain text field with a digit keypad instead of type="time": the native time picker does not
 * open in some Telegram webviews, which left the sleep times impossible to change.
 */
function ClockField({ label, value, required = false, onChange }: ClockFieldProps) {
  const invalid = value !== '' && normalizeClock(value) === null
  return (
    <label>
      <span className="body-label">{label}</span>
      <input
        className={`form-input${invalid ? ' is-invalid' : ''}`}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        placeholder={required ? '23:00' : '—'}
        value={value}
        aria-invalid={invalid || undefined}
        // Typing replaces the old time instead of appending to it.
        onFocus={(event) => event.currentTarget.select()}
        onChange={(event) => onChange(typeClock(event.target.value))}
        onBlur={() => {
          const clock = normalizeClock(value)
          if (clock) onChange(clock)
        }}
      />
    </label>
  )
}

export function SleepDrawer({ open, today, logs, onClose, onChanged }: SleepDrawerProps) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const [day, setDay] = useState(today)
  const [bed, setBed] = useState(DEFAULT_TIMES.bed)
  const [wake, setWake] = useState(DEFAULT_TIMES.wake)
  const [up, setUp] = useState(DEFAULT_TIMES.up)
  const [quality, setQuality] = useState<SleepQuality | null>(null)
  const [note, setNote] = useState('')
  const [range, setRange] = useState<Range>('month')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const existing = logs.find((log) => log.day === day) ?? null

  useEffect(() => {
    if (!open) return
    setDay(today)
    setError(null)
  }, [open, today])

  useEffect(() => {
    if (!open) return
    const log = logs.find((item) => item.day === day)
    // A new night starts from the closest night before it: bedtimes rarely change much.
    const previous = [...logs].reverse().find((item) => item.day < day)
    const source = log ?? previous
    setBed(source ? source.bed_time.slice(0, 5) : DEFAULT_TIMES.bed)
    setWake(source ? source.wake_time.slice(0, 5) : DEFAULT_TIMES.wake)
    setUp(source?.up_time ? source.up_time.slice(0, 5) : DEFAULT_TIMES.up)
    setQuality(log?.quality ?? null)
    setNote(log?.note ?? '')
    // Only when the day changes, not after every save.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, day])

  const bedClock = normalizeClock(bed)
  const wakeClock = normalizeClock(wake)
  const upClock = up === '' ? null : normalizeClock(up)
  const upValid = up === '' || upClock !== null
  const draft =
    bedClock && wakeClock
      ? toNight({ day, bed_time: bedClock, wake_time: wakeClock, up_time: upClock, quality: null, note: null })
      : null
  const canSave = draft !== null && upValid && !isSaving
  const rangeStart = shiftDateKey(today, -RANGES[range] + 1)
  const chartNights = logs.filter((log) => log.day >= rangeStart).map(toNight)

  const run = async (action: () => Promise<unknown>) => {
    setIsSaving(true)
    setError(null)
    try {
      await action()
      await onChanged()
      onClose()
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedSave'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!canSave) return
    void run(() =>
      setSleep(day, {
        bed_time: bedClock ?? bed,
        wake_time: wakeClock ?? wake,
        up_time: upClock,
        quality,
        note: note.trim() || null,
      }),
    )
  }

  return (
    <EditorDrawer
      open={open}
      title={t('body.sleepTitle')}
      description={t('body.sleepNight', { date: formatDay(day, dateLocale, { day: 'numeric', month: 'long' }) })}
      onClose={() => {
        if (!isSaving) onClose()
      }}
      footer={
        <div className="button-row">
          <button type="submit" form="body-sleep-form" className="button my-primary" disabled={!canSave}>
            <StableButtonLabel
              active={isSaving ? t('common.saving') : t('common.save')}
              labels={[t('common.save'), t('common.saving')]}
            />
          </button>
          {existing ? (
            <button
              type="button"
              className="button button-secondary"
              disabled={isSaving}
              onClick={() => void run(() => deleteSleep(day))}
            >
              {t('body.sleepDelete')}
            </button>
          ) : null}
        </div>
      }
    >
      <form id="body-sleep-form" className="form" onSubmit={handleSubmit}>
        <PageErrorAlert error={error} />
        <div className="body-sleep-inputs">
          <ClockField label={t('body.sleepBed')} value={bed} required onChange={setBed} />
          <ClockField label={t('body.sleepWake')} value={wake} required onChange={setWake} />
          <ClockField label={t('body.sleepUp')} value={up} onChange={setUp} />
        </div>
        <div className="body-sleep-meta">
          <span className="body-label">
            {draft ? t('body.sleepAbout', { duration: formatDuration(t, draft.sleep) }) : ''}
          </span>
          <input
            className="form-input body-date"
            type="date"
            max={today}
            value={day}
            aria-label={t('body.sleepDay')}
            onChange={(event) => {
              if (event.target.value && event.target.value <= today) setDay(event.target.value)
            }}
          />
        </div>

        <span className="form-label">
          {t('body.sleepQuality')} <span className="muted">{t('body.optional')}</span>
        </span>
        <div className="body-meals body-sleep-quality" role="radiogroup" aria-label={t('body.sleepQuality')}>
          {QUALITIES.map((item) => (
            <button
              key={item}
              type="button"
              role="radio"
              aria-checked={quality === item}
              className={`body-meal${quality === item ? ' is-selected' : ''}`}
              onClick={() => setQuality(quality === item ? null : item)}
            >
              {t(`body.quality.${item}`)}
            </button>
          ))}
        </div>
        <input
          className="form-input"
          value={note}
          maxLength={500}
          placeholder={t('body.sleepNotePlaceholder')}
          aria-label={t('body.sleepNote')}
          onChange={(event) => setNote(event.target.value)}
        />

        {logs.length > 0 ? (
          <div className="body-chart">
            <div className="body-range" role="radiogroup" aria-label={t('body.chartRange')}>
              {(Object.keys(RANGES) as Range[]).map((key) => (
                <button
                  key={key}
                  type="button"
                  role="radio"
                  aria-checked={range === key}
                  className={range === key ? 'is-selected' : ''}
                  onClick={() => setRange(key)}
                >
                  {t(`body.range.${key}`)}
                </button>
              ))}
            </div>
            {chartNights.length > 0 ? (
              <SleepChart nights={chartNights} from={rangeStart} to={today} />
            ) : (
              <p className="my-empty">{t('body.sleepChartFew')}</p>
            )}
            <p className="my-level-hint">{t('body.sleepChartHint')}</p>
          </div>
        ) : null}
        <p className="my-gentle muted">{t('body.sleepGentle')}</p>
      </form>
    </EditorDrawer>
  )
}
