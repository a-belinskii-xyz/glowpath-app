import { useEffect, useState } from 'react'

import { updateBodySettings } from '../api/body'
import { BODY_RANGES, type BodyRange, BodyRangeSwitch } from './BodyRange'
import { EditorDrawer } from './EditorDrawer'
import { PageErrorAlert } from './PageErrorAlert'
import { useLocale } from '../context/LocaleContext'
import { intlLocale } from '../i18n/t'
import { bodyMassIndex, dayNumber, formatDay, weekAverage } from '../lib/bodyFormat'
import { shiftDateKey } from '../lib/datetime'
import { formatApiError } from '../lib/errors'
import type { BodySettings, WeightPoint } from '../types/body'

// The BMI scale runs over this span; marks at the usual 18.5 / 25 / 30 cut-offs, without their names.
const BMI_SCALE = { min: 15, max: 40 }
const BMI_MARKS = [18.5, 25, 30]

/** A trend through each measurement: the mean of everything within a week on either side. */
function smoothed(points: WeightPoint[]): WeightPoint[] {
  return points.map((point) => {
    const center = dayNumber(point.day)
    const near = points.filter((other) => Math.abs(dayNumber(other.day) - center) <= 7)
    return { day: point.day, value: near.reduce((sum, other) => sum + other.value, 0) / near.length }
  })
}

type ChartProps = {
  points: WeightPoint[]
  width: number
  height: number
  showDots?: boolean
  className?: string
}

/** A quiet trend line in one neutral colour, with single measurements as dots behind it. */
export function WeightChart({ points, width, height, showDots = false, className }: ChartProps) {
  if (points.length < 2) return null
  const line = smoothed(points)
  const values = points.map((point) => point.value)
  const low = Math.min(...values)
  const high = Math.max(...values)
  // At least a 2 kg band, so a 0.3 kg wobble does not look like a cliff.
  const pad = Math.max(1 - (high - low) / 2, 0.3)
  const min = low - pad
  const max = high + pad
  const first = dayNumber(points[0].day)
  const span = Math.max(dayNumber(points[points.length - 1].day) - first, 1)
  const x = (day: string) => 4 + ((dayNumber(day) - first) / span) * (width - 8)
  const y = (value: number) => 4 + ((max - value) / (max - min)) * (height - 8)
  const path = line.map((point, index) => `${index ? 'L' : 'M'}${x(point.day).toFixed(1)},${y(point.value).toFixed(1)}`)
  return (
    <svg
      className={className}
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      preserveAspectRatio="none"
      aria-hidden
    >
      {showDots
        ? points.map((point) => (
            <circle
              key={point.day}
              className="body-chart-dot"
              cx={x(point.day)}
              cy={y(point.value)}
              r={2.6}
            />
          ))
        : null}
      <path className="body-chart-line" d={path.join(' ')} vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

type WeightStatsDrawerProps = {
  open: boolean
  today: string
  weights: WeightPoint[]
  settings: BodySettings
  onClose: () => void
  onRecord: (day: string) => void
  onSettingsChange: (settings: BodySettings) => void
  onOpenSettings: () => void
}

/** Weight over a month to a year (GP-60): the trend, a few plain numbers, BMI and every measurement. */
export function WeightStatsDrawer({
  open,
  today,
  weights,
  settings,
  onClose,
  onRecord,
  onSettingsChange,
  onOpenSettings,
}: WeightStatsDrawerProps) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const [range, setRange] = useState<BodyRange>('quarter')
  const [revealed, setRevealed] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setRevealed(false)
    setError(null)
  }, [open])

  const hidden = settings.hide_weight && !revealed
  const numbers = new Intl.NumberFormat(dateLocale, { minimumFractionDigits: 1, maximumFractionDigits: 1 })
  const from = shiftDateKey(today, -BODY_RANGES[range] + 1)
  const inRange = weights.filter((point) => point.day >= from && point.day <= today)
  const average = weekAverage(weights, today)
  const trend = smoothed(inRange)
  const change = trend.length >= 2 ? trend[trend.length - 1].value - trend[0].value : null
  const values = inRange.map((point) => point.value)
  const bmiWeight = average ?? (weights.length > 0 ? weights[weights.length - 1].value : null)
  const bmi = settings.height_cm !== null && bmiWeight !== null ? bodyMassIndex(bmiWeight, settings.height_cm) : null
  const bmiAt = (value: number) =>
    ((Math.min(Math.max(value, BMI_SCALE.min), BMI_SCALE.max) - BMI_SCALE.min) / (BMI_SCALE.max - BMI_SCALE.min)) * 100

  const kg = (value: number) => `${numbers.format(value)} ${t('body.kg')}`
  const changeLabel = (value: number) => {
    // Under 0.1 kg either way reads as "about the same", not as a tiny gain or loss.
    if (Math.abs(value) < 0.05) return t('body.statsSame')
    return `${value > 0 ? '+' : '−'}${kg(Math.abs(value))}`
  }

  const toggleHidden = async (hide: boolean) => {
    try {
      onSettingsChange(await updateBodySettings({ hide_weight: hide }))
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedSave'))
    }
  }

  return (
    <EditorDrawer
      open={open}
      title={t('body.weightTitle')}
      onClose={onClose}
      footer={
        <div className="button-row">
          <button type="button" className="button my-primary" onClick={() => onRecord(today)}>
            {t('body.recordWeight')}
          </button>
        </div>
      }
    >
      <div className="form">
        <PageErrorAlert error={error} />
        {weights.length === 0 ? <p className="my-empty">{t('body.weightEmpty')}</p> : null}
        {weights.length > 0 ? (
          <div className="body-chart">
            <BodyRangeSwitch value={range} onChange={setRange} />
            {inRange.length >= 2 ? (
              <WeightChart
                points={inRange}
                width={360}
                height={150}
                showDots
                className={`body-chart-svg${hidden ? ' is-hidden' : ''}`}
              />
            ) : (
              <p className="my-empty">{t('body.chartFew')}</p>
            )}
            <p className="my-level-hint">{t('body.chartHint')}</p>
          </div>
        ) : null}

        {inRange.length > 0 || average !== null ? (
          <button
            type="button"
            className={`body-stats${hidden ? ' is-hidden' : ''}`}
            aria-label={hidden ? t('body.reveal') : undefined}
            onClick={() => setRevealed((value) => !value)}
          >
            {average !== null ? (
              <span>
                <span className="body-label">{t('body.statsWeekAverage')}</span>
                <strong>{kg(average)}</strong>
              </span>
            ) : null}
            {change !== null ? (
              <span>
                <span className="body-label">{t('body.statsChange', { range: t(`body.rangeFor.${range}`) })}</span>
                <strong>{changeLabel(change)}</strong>
              </span>
            ) : null}
            {values.length > 0 ? (
              <span>
                <span className="body-label">{t('body.statsMinMax')}</span>
                <strong>
                  {numbers.format(Math.min(...values))} / {numbers.format(Math.max(...values))}
                </strong>
              </span>
            ) : null}
            {values.length > 0 ? (
              <span>
                <span className="body-label">{t('body.statsCount')}</span>
                <strong>{values.length}</strong>
              </span>
            ) : null}
          </button>
        ) : null}

        <div className="body-bmi">
          <span className="form-label">{t('body.bmiTitle')}</span>
          {bmi === null ? (
            <p className="my-level-hint">
              {settings.height_cm === null ? (
                <button type="button" className="link-button" onClick={onOpenSettings}>
                  {t('body.bmiNeedsHeight')}
                </button>
              ) : (
                t('body.bmiNeedsWeight')
              )}
            </p>
          ) : (
            <button
              type="button"
              className={`body-bmi-scale${hidden ? ' is-hidden' : ''}`}
              aria-label={hidden ? t('body.reveal') : undefined}
              onClick={() => setRevealed((value) => !value)}
            >
              <span className="body-bmi-value">
                {t('body.bmiValue', {
                  value: new Intl.NumberFormat(dateLocale, { maximumFractionDigits: 1 }).format(bmi),
                })}
              </span>
              <span className="body-bmi-track">
                {BMI_MARKS.map((mark) => (
                  <span key={mark} className="body-bmi-mark" style={{ left: `${bmiAt(mark)}%` }}>
                    <span>{new Intl.NumberFormat(dateLocale).format(mark)}</span>
                  </span>
                ))}
                <span className="body-bmi-dot" style={{ left: `${bmiAt(bmi)}%` }} />
              </span>
            </button>
          )}
          <p className="my-level-hint">{t('body.bmiNote')}</p>
        </div>

        {inRange.length > 0 ? (
          <div className="body-history">
            <span className="form-label">{t('body.statsEntries')}</span>
            <ul>
              {[...inRange].reverse().map((point) => (
                <li key={point.day}>
                  <button type="button" onClick={() => onRecord(point.day)}>
                    <span>
                      {point.day === today
                        ? t('body.todayCapital')
                        : formatDay(point.day, dateLocale, { weekday: 'short', day: 'numeric', month: 'short' })}
                    </span>
                    <span className={hidden ? 'is-hidden' : undefined}>{kg(point.value)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <label className="body-check">
          <input type="checkbox" checked={settings.hide_weight} onChange={(event) => void toggleHidden(event.target.checked)} />
          <span>{t('body.hideWeight')}</span>
        </label>
        <p className="my-gentle muted">{t('body.weightGentle')}</p>
      </div>
    </EditorDrawer>
  )
}
