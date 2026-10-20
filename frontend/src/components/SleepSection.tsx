import { type FormEvent, type KeyboardEvent, useEffect, useState } from 'react'

import { deleteSleep, setSleep } from '../api/body'
import { BODY_RANGES, type BodyRange, BodyRangeSwitch } from './BodyRange'
import { ClockField } from './ClockField'
import { EditorDrawer } from './EditorDrawer'
import { PageErrorAlert } from './PageErrorAlert'
import { StableButtonLabel } from './StableButtonLabel'
import { useLocale } from '../context/LocaleContext'
import { intlLocale } from '../i18n/t'
import { dayNumber, formatDay } from '../lib/bodyFormat'
import { shiftDateKey } from '../lib/datetime'
import { formatApiError } from '../lib/errors'
import {
  type Night,
  type SleepNorm,
  averageNights,
  formatDuration,
  nightClock,
  normalizeClock,
  sleepBand,
  toNight,
} from '../lib/sleep'
import type { SleepLog, SleepQuality } from '../types/body'

const QUALITIES: SleepQuality[] = ['hard', 'ok', 'good']

/** A big clock with "AM" / "PM" set small, so it stays on one line. */
function bigClock(clock: string) {
  const [time, period] = clock.split(' ')
  return period ? (
    <>
      {time}
      <small>{period}</small>
    </>
  ) : (
    clock
  )
}

/** "7 h" or "7.5 h" for the legend. */
function normHours(minutes: number, dateLocale: string, unit: string): string {
  return `${new Intl.NumberFormat(dateLocale, { maximumFractionDigits: 1 }).format(minutes / 60)} ${unit}`
}

/** Three colours against the person's own norm (GP-61); nothing reads as a grade. */
function SleepLegend({ norm }: { norm: SleepNorm }) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const unit = t('body.hoursShort')
  return (
    <div className="body-sleep-legend">
      <span>
        <i className="body-sleep-swatch is-short" />
        {t('body.sleepNormShort', { hours: normHours(norm.min, dateLocale, unit) })}
      </span>
      <span>
        <i className="body-sleep-swatch is-normal" />
        {t('body.sleepNormIn', {
          from: normHours(norm.min, dateLocale, '').trim(),
          to: normHours(norm.max, dateLocale, unit),
        })}
      </span>
      <span>
        <i className="body-sleep-swatch is-long" />
        {t('body.sleepNormLong', { hours: normHours(norm.max, dateLocale, unit) })}
      </span>
    </div>
  )
}

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
  norm: SleepNorm | null
  onRecord: () => void
  onOpenStats: () => void
}

/** Sleep on «Моё» (GP-48): averages for the last 7 nights and the week as bars, no "8 hours" norm. */
export function SleepSection({ logs, asOf, today, weekDays, norm, onRecord, onOpenStats }: SleepSectionProps) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const nights = logs.map(toNight)
  const recent = nights.filter((night) => night.day <= asOf && dayNumber(night.day) > dayNumber(asOf) - 7)
  const average = averageNights(recent)
  const week = nights.filter((night) => night.day >= weekDays[0] && night.day <= weekDays[6])
  const scale = week.length > 0 ? hourTicks(week) : null
  const at = (minutes: number) => scale ? ((minutes - scale.start) / (scale.end - scale.start)) * 100 : 0
  const openOnKey = (event: KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onOpenStats()
    }
  }

  return (
    <div className="body-sleep">
      <div className="body-food-head">
        <strong>{t('body.sleepTitle')}</strong>
        {average ? <span className="body-label">{t('body.sleepAverage')}</span> : null}
      </div>
      {/* The averages and the week open the stats (GP-60). */}
      <div
        className={logs.length > 0 ? 'body-sleep-summary body-stats-open' : 'body-sleep-summary'}
        role={logs.length > 0 ? 'button' : undefined}
        tabIndex={logs.length > 0 ? 0 : undefined}
        aria-label={logs.length > 0 ? t('body.statsOpen', { title: t('body.sleepTitle') }) : undefined}
        onClick={logs.length > 0 ? onOpenStats : undefined}
        onKeyDown={logs.length > 0 ? openOnKey : undefined}
      >
      {average ? (
        <>
          <div className="body-sleep-times">
            <div>
              <span className="body-label">{t('body.sleepBed')}</span>
              <strong>{bigClock(nightClock(average.bed))}</strong>
            </div>
            <div>
              <span className="body-label">{t('body.sleepWake')}</span>
              <strong>{bigClock(nightClock(average.wake))}</strong>
            </div>
            {average.up !== null ? (
              <div>
                <span className="body-label">{t('body.sleepUp')}</span>
                <strong>{bigClock(nightClock(average.up))}</strong>
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
                <div key={day} className={`body-sleep-row${night && norm ? ` is-${sleepBand(night.sleep, norm)}` : ''}`}>
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
                  {nightClock(tick, { short: true })}
                </span>
              ))}
            </span>
          </div>
        </div>
      ) : null}
      {scale && norm ? <SleepLegend norm={norm} /> : null}
      {logs.length > 0 ? (
        <span className="body-chevron body-sleep-chevron" aria-hidden>
          ›
        </span>
      ) : null}
      </div>
      <button type="button" className="button button-secondary body-wide" onClick={onRecord}>
        {t('body.sleepRecord')}
      </button>
    </div>
  )
}

/** Nights as vertical bars over a month to a year: asleep in one tone, lying after waking lighter. */
function SleepChart({ nights, from, to, norm }: { nights: Night[]; from: string; to: string; norm: SleepNorm | null }) {
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
            {nightClock(tick, { short: true })}
          </text>
        </g>
      ))}
      {nights.map((night) => (
        <g key={night.day} className={norm ? `is-${sleepBand(night.sleep, norm)}` : undefined}>
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
  /** The morning to record or edit; null keeps the drawer closed. */
  target: string | null
  today: string
  logs: SleepLog[]
  onClose: () => void
  onChanged: () => Promise<void>
}

const DEFAULT_TIMES = { bed: '23:00', wake: '07:00', up: '' }

export function SleepDrawer({ target, today, logs, onClose, onChanged }: SleepDrawerProps) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const open = target !== null
  const [day, setDay] = useState(today)
  const [bed, setBed] = useState(DEFAULT_TIMES.bed)
  const [wake, setWake] = useState(DEFAULT_TIMES.wake)
  const [up, setUp] = useState(DEFAULT_TIMES.up)
  const [quality, setQuality] = useState<SleepQuality | null>(null)
  const [note, setNote] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const existing = logs.find((log) => log.day === day) ?? null

  useEffect(() => {
    if (target === null) return
    setDay(target)
    setError(null)
  }, [target])

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
          <div>
            <span className="body-label">{t('body.sleepBed')}</span>
            <ClockField ariaLabel={t('body.sleepBed')} value={bed} required onChange={setBed} />
          </div>
          <div>
            <span className="body-label">{t('body.sleepWake')}</span>
            <ClockField ariaLabel={t('body.sleepWake')} value={wake} required onChange={setWake} />
          </div>
          <div>
            <span className="body-label">{t('body.sleepUp')}</span>
            <ClockField ariaLabel={t('body.sleepUp')} value={up} placeholder="—" onChange={setUp} />
          </div>
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

        <p className="my-gentle muted">{t('body.sleepGentle')}</p>
      </form>
    </EditorDrawer>
  )
}

type SleepStatsDrawerProps = {
  open: boolean
  today: string
  logs: SleepLog[]
  norm: SleepNorm | null
  onClose: () => void
  onRecord: (day: string) => void
}

/** Sleep over a month to a year (GP-60): the nights as bars, averages for the period and every night. */
export function SleepStatsDrawer({ open, today, logs, norm, onClose, onRecord }: SleepStatsDrawerProps) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const [range, setRange] = useState<BodyRange>('month')
  const from = shiftDateKey(today, -BODY_RANGES[range] + 1)
  const nights = logs.filter((log) => log.day >= from && log.day <= today).map(toNight)
  const average = averageNights(nights)
  const inNorm = norm ? nights.filter((night) => sleepBand(night.sleep, norm) === 'normal').length : 0
  const byDay = new Map(logs.map((log) => [log.day, log]))

  return (
    <EditorDrawer
      open={open}
      title={t('body.sleepTitle')}
      onClose={onClose}
      footer={
        <div className="button-row">
          <button type="button" className="button my-primary" onClick={() => onRecord(today)}>
            {t('body.sleepRecord')}
          </button>
        </div>
      }
    >
      <div className="form">
        <div className="body-chart">
          <BodyRangeSwitch value={range} onChange={setRange} />
          {nights.length > 0 ? (
            <SleepChart nights={nights} from={from} to={today} norm={norm} />
          ) : (
            <p className="my-empty">{t('body.sleepChartFew')}</p>
          )}
          {nights.length > 0 && norm ? <SleepLegend norm={norm} /> : null}
          <p className="my-level-hint">{t('body.sleepChartHint')}</p>
        </div>

        {average ? (
          <div className="body-stats">
            <span>
              <span className="body-label">{t('body.statsBed')}</span>
              <strong>{nightClock(average.bed)}</strong>
            </span>
            <span>
              <span className="body-label">{t('body.statsWake')}</span>
              <strong>{nightClock(average.wake)}</strong>
            </span>
            <span>
              <span className="body-label">{t('body.statsSleep')}</span>
              <strong>{formatDuration(t, average.sleep)}</strong>
            </span>
            <span>
              <span className="body-label">{t('body.statsNights')}</span>
              <strong>{nights.length}</strong>
            </span>
          </div>
        ) : null}

        {norm && nights.length > 0 ? (
          <p className="body-label body-sleep-in-norm">{t('body.sleepInNorm', { count: inNorm, total: nights.length })}</p>
        ) : null}

        {nights.length > 0 ? (
          <div className="body-history">
            <span className="form-label">{t('body.statsNightsList')}</span>
            <ul>
              {[...nights].reverse().map((night) => {
                const quality = byDay.get(night.day)?.quality
                return (
                  <li key={night.day}>
                    <button type="button" onClick={() => onRecord(night.day)}>
                      <span>{formatDay(night.day, dateLocale, { weekday: 'short', day: 'numeric', month: 'short' })}</span>
                      <span>
                        {norm ? <i className={`body-sleep-swatch is-${sleepBand(night.sleep, norm)}`} /> : null}
                        {nightClock(night.bed)}–{nightClock(night.wake)} · {formatDuration(t, night.sleep)}
                        {quality ? ` · ${t(`body.quality.${quality}`)}` : ''}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </div>
        ) : null}
        <p className="my-gentle muted">{t('body.sleepStatsGentle')}</p>
      </div>
    </EditorDrawer>
  )
}
