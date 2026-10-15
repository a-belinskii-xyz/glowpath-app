import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'

import { setGoalCheckin } from '../api/goals'
import { listMoodEntries } from '../api/moodEntries'
import {
  createFood,
  deleteFood,
  deleteWeight,
  listFood,
  listWeights,
  setWeight,
  updateBodySettings,
  updateFood,
} from '../api/body'
import { EditorDrawer } from './EditorDrawer'
import { PageErrorAlert } from './PageErrorAlert'
import { StableButtonLabel } from './StableButtonLabel'
import { useLocale } from '../context/LocaleContext'
import { intlLocale } from '../i18n/t'
import { dayKey, getDayBounds, shiftDateKey } from '../lib/datetime'
import { formatApiError } from '../lib/errors'
import type { BodySettings, FoodLog, Meal, WeightPoint } from '../types/body'
import type { GoalPublic } from '../types/goal'

const MEALS: Meal[] = ['morning', 'day', 'evening', 'snack']
const MIN_WEIGHT = 20
const MAX_WEIGHT = 400
const MAX_FOOD_GOALS = 3
// The chart's longest range; the card reads its summary from the same points.
const HISTORY_DAYS = 365
const SPARK_DAYS = 60
const RANGES = { month: 31, quarter: 92, year: HISTORY_DAYS } as const
type Range = keyof typeof RANGES

function dayNumber(day: string): number {
  const [year, month, date] = day.split('-').map(Number)
  return Date.UTC(year, month - 1, date) / 86_400_000
}

function formatDay(day: string, dateLocale: string, options: Intl.DateTimeFormatOptions): string {
  const [year, month, date] = day.split('-').map(Number)
  return new Intl.DateTimeFormat(dateLocale, { ...options, timeZone: 'UTC' }).format(
    new Date(Date.UTC(year, month - 1, date)),
  )
}

/** The average of the measurements in the 7 days ending on ``day``, or null if there are none. */
function weekAverage(points: WeightPoint[], day: string): number | null {
  const end = dayNumber(day)
  const window = points.filter((point) => {
    const n = dayNumber(point.day)
    return n <= end && n > end - 7
  })
  if (window.length === 0) return null
  return window.reduce((sum, point) => sum + point.value, 0) / window.length
}

/** A trend through each measurement: the mean of everything within a week on either side. */
function smoothed(points: WeightPoint[]): WeightPoint[] {
  return points.map((point) => {
    const center = dayNumber(point.day)
    const near = points.filter((other) => Math.abs(dayNumber(other.day) - center) <= 7)
    return { day: point.day, value: near.reduce((sum, other) => sum + other.value, 0) / near.length }
  })
}

function parseWeight(raw: string): number | null {
  const value = Number.parseFloat(raw.replace(',', '.'))
  if (!Number.isFinite(value) || value < MIN_WEIGHT || value > MAX_WEIGHT) return null
  return Math.round(value * 10) / 10
}

/** A meal guess from the clock, only as a starting point. */
function mealNow(): Meal {
  const hour = new Date().getHours()
  if (hour < 11) return 'morning'
  if (hour < 16) return 'day'
  if (hour < 22) return 'evening'
  return 'snack'
}

type ChartProps = {
  points: WeightPoint[]
  width: number
  height: number
  showDots?: boolean
  className?: string
}

/** A quiet trend line in one neutral colour, with single measurements as dots behind it. */
function WeightChart({ points, width, height, showDots = false, className }: ChartProps) {
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

type BodyCardProps = {
  settings: BodySettings
  today: string
  timeZone: string
  weekDays: string[]
  isCurrentWeek: boolean
  goals: GoalPublic[]
  onSettingsChange: (settings: BodySettings) => void
  onGoalChange: (goal: GoalPublic) => void
  onOpenSettings: () => void
}

/** Weight and food on «Моё» (GP-47): no targets, no calories, nothing to fall behind on. */
export function BodyCard({
  settings,
  today,
  timeZone,
  weekDays,
  isCurrentWeek,
  goals,
  onSettingsChange,
  onGoalChange,
  onOpenSettings,
}: BodyCardProps) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const asOf = isCurrentWeek ? today : weekDays[6]
  const weekStart = weekDays[0]
  const weekEnd = weekDays[6]

  const [weights, setWeights] = useState<WeightPoint[]>([])
  const [food, setFood] = useState<FoodLog[]>([])
  const [error, setError] = useState<string | null>(null)
  const [revealed, setRevealed] = useState(false)
  const [weightOpen, setWeightOpen] = useState(false)
  const [foodTarget, setFoodTarget] = useState<{ day: string; log: FoodLog | null } | null>(null)
  const [foodDay, setFoodDay] = useState(asOf)
  const [copyOpen, setCopyOpen] = useState(false)

  useEffect(() => setFoodDay(asOf), [asOf])

  const loadWeights = useCallback(async () => {
    setWeights(await listWeights(shiftDateKey(today, -HISTORY_DAYS), today))
  }, [today])

  const loadFood = useCallback(async () => {
    setFood(await listFood(weekStart, weekEnd))
  }, [weekStart, weekEnd])

  useEffect(() => {
    if (!settings.show_weight) return
    void loadWeights().catch((err) => setError(formatApiError(err, t, 'errors.requestFailed')))
  }, [settings.show_weight, loadWeights, t])

  useEffect(() => {
    if (!settings.show_food) return
    void loadFood().catch((err) => setError(formatApiError(err, t, 'errors.requestFailed')))
  }, [settings.show_food, loadFood, t])

  const numberFormat = useMemo(
    () => new Intl.NumberFormat(dateLocale, { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
    [dateLocale],
  )
  const known = weights.filter((point) => point.day <= asOf)
  const latest = known.length > 0 ? known[known.length - 1] : null
  const average = weekAverage(known, asOf)
  const shown = average ?? latest?.value ?? null
  const spark = known.filter((point) => dayNumber(point.day) > dayNumber(asOf) - SPARK_DAYS)

  const latestLabel = (day: string) => {
    if (day === today) return t('body.today')
    if (day === shiftDateKey(today, -1)) return t('body.yesterday')
    return formatDay(day, dateLocale, { day: 'numeric', month: 'long' })
  }

  const dayFood = food.filter((log) => log.day === foodDay)
  const foodGoals = goals.filter((goal) => settings.food_goal_ids.includes(goal.id))

  return (
    <section className="card my-card body-card" aria-labelledby="my-body-title">
      <div className="my-card-head">
        <h2 id="my-body-title">{t('body.title')}</h2>
        <button type="button" className="link-button my-card-link" onClick={onOpenSettings}>
          {t('body.configure')}
        </button>
      </div>
      <PageErrorAlert error={error} />

      {settings.show_weight ? (
        <div className="body-weight">
          {shown === null ? (
            <p className="my-empty">{t('body.weightEmpty')}</p>
          ) : (
            <div className="body-weight-summary">
              <div>
                <span className="body-label">
                  {average !== null ? t('body.weightAverage') : t('body.weightLast')}
                </span>
                <button
                  type="button"
                  className={`body-weight-value${settings.hide_weight && !revealed ? ' is-hidden' : ''}`}
                  aria-label={settings.hide_weight && !revealed ? t('body.reveal') : undefined}
                  onClick={() => setRevealed((value) => !value)}
                >
                  {numberFormat.format(shown)} <small>{t('body.kg')}</small>
                </button>
                {latest ? (
                  <span className="body-label">
                    {t('body.lastMeasured', { date: latestLabel(latest.day) })}
                  </span>
                ) : null}
              </div>
              {!settings.hide_weight || revealed ? (
                <WeightChart points={spark} width={120} height={48} className="body-spark" />
              ) : null}
            </div>
          )}
          <button type="button" className="button button-secondary body-wide" onClick={() => setWeightOpen(true)}>
            {t('body.recordWeight')}
          </button>
        </div>
      ) : null}

      {settings.show_food ? (
        <div className="body-food">
          <div className="body-food-head">
            <strong>
              {foodDay === today ? t('body.foodToday') : formatDay(foodDay, dateLocale, { weekday: 'long', day: 'numeric', month: 'long' })}
            </strong>
            <span className="body-label">{t('body.noCounting')}</span>
          </div>
          <div className="my-goal-days body-days" role="tablist" aria-label={t('body.foodDays')}>
            {weekDays.map((day) => {
              const has = food.some((log) => log.day === day)
              const className = [
                'my-day',
                day === foodDay ? 'is-selected' : '',
                has ? 'has-food' : '',
                day === today ? 'is-today' : '',
              ]
                .filter(Boolean)
                .join(' ')
              const label = formatDay(day, dateLocale, { weekday: 'short' })
              if (day > today) {
                return (
                  <span key={day} className={`${className} is-before`} aria-hidden>
                    {label}
                  </span>
                )
              }
              return (
                <button
                  key={day}
                  type="button"
                  role="tab"
                  aria-selected={day === foodDay}
                  className={className}
                  title={formatDay(day, dateLocale, { weekday: 'long', day: 'numeric', month: 'long' })}
                  onClick={() => setFoodDay(day)}
                >
                  {label}
                </button>
              )
            })}
          </div>
          {dayFood.length === 0 ? (
            <p className="my-empty">{t('body.foodEmpty')}</p>
          ) : (
            <ul className="body-food-list">
              {dayFood.map((log) => (
                <li key={log.id}>
                  <button type="button" className="body-food-row" onClick={() => setFoodTarget({ day: log.day, log })}>
                    <span className="body-food-meal">{log.meal ? t(`body.meal.${log.meal}`) : ''}</span>
                    <span className="body-food-text">{log.text}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="body-food-actions">
            <button type="button" className="link-button body-food-add" onClick={() => setFoodTarget({ day: foodDay, log: null })}>
              ＋ {dayFood.length === 0 ? t('body.foodAddFirst') : t('body.foodAddMore')}
            </button>
            <button type="button" className="link-button body-food-copy" onClick={() => setCopyOpen(true)}>
              {t('body.copyOpen')}
            </button>
          </div>
        </div>
      ) : null}

      <WeightDrawer
        open={weightOpen}
        today={today}
        weights={weights}
        settings={settings}
        onClose={() => setWeightOpen(false)}
        onChanged={loadWeights}
        onSettingsChange={onSettingsChange}
      />
      <FoodCopyDrawer open={copyOpen} today={today} timeZone={timeZone} onClose={() => setCopyOpen(false)} />
      <FoodDrawer
        target={foodTarget}
        today={today}
        goals={foodGoals}
        onClose={() => setFoodTarget(null)}
        onSaved={async () => {
          setFoodTarget(null)
          await loadFood()
        }}
        onGoalChange={onGoalChange}
      />
    </section>
  )
}

type WeightDrawerProps = {
  open: boolean
  today: string
  weights: WeightPoint[]
  settings: BodySettings
  onClose: () => void
  onChanged: () => Promise<void>
  onSettingsChange: (settings: BodySettings) => void
}

function WeightDrawer({ open, today, weights, settings, onClose, onChanged, onSettingsChange }: WeightDrawerProps) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const [day, setDay] = useState(today)
  const [raw, setRaw] = useState('')
  const [range, setRange] = useState<Range>('quarter')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const existing = weights.find((point) => point.day === day) ?? null

  useEffect(() => {
    if (!open) return
    setDay(today)
    setError(null)
  }, [open, today])

  useEffect(() => {
    if (!open) return
    const point = weights.find((item) => item.day === day)
    setRaw(point ? String(point.value).replace('.', locale === 'ru' ? ',' : '.') : '')
    // Only when the day changes, not after every save.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, day])

  const value = parseWeight(raw)
  const rangeStart = shiftDateKey(today, -RANGES[range])
  const chartPoints = weights.filter((point) => point.day >= rangeStart)

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

  const toggleHidden = async (hide: boolean) => {
    try {
      onSettingsChange(await updateBodySettings({ hide_weight: hide }))
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedSave'))
    }
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (value === null || isSaving) return
    void run(() => setWeight(day, value))
  }

  return (
    <EditorDrawer
      open={open}
      title={t('body.weightTitle')}
      description={formatDay(day, dateLocale, { weekday: 'long', day: 'numeric', month: 'long' })}
      onClose={() => {
        if (!isSaving) onClose()
      }}
      footer={
        <div className="button-row">
          <button type="submit" form="body-weight-form" className="button my-primary" disabled={value === null || isSaving}>
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
              onClick={() => void run(() => deleteWeight(day))}
            >
              {t('body.weightDelete')}
            </button>
          ) : null}
        </div>
      }
    >
      <form id="body-weight-form" className="form" onSubmit={handleSubmit}>
        <PageErrorAlert error={error} />
        <div className="my-amount-row body-weight-row">
          <input
            className="form-input"
            inputMode="decimal"
            aria-label={t('body.weightTitle')}
            placeholder={t('body.weightPlaceholder')}
            value={raw}
            onChange={(event) => setRaw(event.target.value.replace(/[^0-9.,]/g, ''))}
            autoFocus
          />
          <span className="muted">{t('body.kg')}</span>
          <input
            className="form-input body-date"
            type="date"
            max={today}
            value={day}
            aria-label={t('body.weightDay')}
            onChange={(event) => {
              if (event.target.value && event.target.value <= today) setDay(event.target.value)
            }}
          />
        </div>
        {raw && value === null ? (
          <span className="my-level-hint">{t('body.weightRange', { min: MIN_WEIGHT, max: MAX_WEIGHT })}</span>
        ) : null}

        {weights.length >= 2 ? (
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
            {chartPoints.length >= 2 ? (
              <WeightChart points={chartPoints} width={360} height={150} showDots className="body-chart-svg" />
            ) : (
              <p className="my-empty">{t('body.chartFew')}</p>
            )}
            <p className="my-level-hint">{t('body.chartHint')}</p>
          </div>
        ) : null}

        <label className="body-check">
          <input type="checkbox" checked={settings.hide_weight} onChange={(event) => void toggleHidden(event.target.checked)} />
          <span>{t('body.hideWeight')}</span>
        </label>
        <p className="my-gentle muted">{t('body.weightGentle')}</p>
      </form>
    </EditorDrawer>
  )
}

type FoodDrawerProps = {
  target: { day: string; log: FoodLog | null } | null
  today: string
  goals: GoalPublic[]
  onClose: () => void
  onSaved: () => Promise<void>
  onGoalChange: (goal: GoalPublic) => void
}

function FoodDrawer({ target, today, goals, onClose, onSaved, onGoalChange }: FoodDrawerProps) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const [meal, setMeal] = useState<Meal | null>(null)
  const [text, setText] = useState('')
  const [marked, setMarked] = useState<string[]>([])
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!target) return
    setMeal(target.log ? target.log.meal : target.day === today ? mealNow() : null)
    setText(target.log?.text ?? '')
    setMarked([])
    setError(null)
  }, [target, today])

  const day = target?.day ?? today
  // Offer a goal only on a day it is active and not marked yet.
  const offered =
    target?.log == null
      ? goals.filter(
          (goal) =>
            goal.starts_on <= day &&
            (goal.ends_on == null || goal.ends_on >= day) &&
            !goal.week_marks.some((mark) => mark.date === day),
        )
      : []

  const canSave = text.trim().length > 0 && !isSaving

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!target || !canSave) return
    setIsSaving(true)
    setError(null)
    try {
      if (target.log) {
        await updateFood(target.log.id, { meal, text: text.trim() })
      } else {
        await createFood({ day, meal, text: text.trim() })
      }
      for (const goal of offered.filter((item) => marked.includes(item.id))) {
        onGoalChange(await setGoalCheckin(goal.id, day, { level: 'full' }))
      }
      await onSaved()
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedSave'))
    } finally {
      setIsSaving(false)
    }
  }

  const remove = async () => {
    if (!target?.log) return
    setIsSaving(true)
    setError(null)
    try {
      await deleteFood(target.log.id)
      await onSaved()
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedSave'))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <EditorDrawer
      open={target !== null}
      title={t('body.foodTitle')}
      description={formatDay(day, dateLocale, { weekday: 'long', day: 'numeric', month: 'long' })}
      onClose={() => {
        if (!isSaving) onClose()
      }}
      footer={
        <div className="button-row">
          <button type="submit" form="body-food-form" className="button my-primary" disabled={!canSave}>
            <StableButtonLabel
              active={isSaving ? t('common.saving') : t('common.save')}
              labels={[t('common.save'), t('common.saving')]}
            />
          </button>
          {target?.log ? (
            <button type="button" className="button button-secondary" disabled={isSaving} onClick={() => void remove()}>
              {t('common.delete')}
            </button>
          ) : null}
        </div>
      }
    >
      <form id="body-food-form" className="form my-win-form" onSubmit={(event) => void handleSubmit(event)}>
        <PageErrorAlert error={error} />
        <div className="body-meals" role="radiogroup" aria-label={t('body.mealLabel')}>
          {MEALS.map((item) => (
            <button
              key={item}
              type="button"
              role="radio"
              aria-checked={meal === item}
              className={`body-meal${meal === item ? ' is-selected' : ''}`}
              onClick={() => setMeal(meal === item ? null : item)}
            >
              {t(`body.meal.${item}`)}
            </button>
          ))}
        </div>
        <textarea
          className="form-input my-win-input"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={t('body.foodPlaceholder')}
          aria-label={t('body.foodTitle')}
          rows={3}
          maxLength={500}
          autoFocus
        />
        {offered.map((goal) => (
          <label key={goal.id} className="body-check">
            <input
              type="checkbox"
              checked={marked.includes(goal.id)}
              onChange={(event) =>
                setMarked((current) =>
                  event.target.checked ? [...current, goal.id] : current.filter((id) => id !== goal.id),
                )
              }
            />
            <span>{t('body.markGoal', { label: goal.label })}</span>
          </label>
        ))}
        <p className="my-gentle muted">{t('body.foodGentle')}</p>
      </form>
    </EditorDrawer>
  )
}

type BodySettingsDrawerProps = {
  open: boolean
  settings: BodySettings
  goals: GoalPublic[]
  onClose: () => void
  onSettingsChange: (settings: BodySettings) => void
}

/** Turn weight and food on or off for «Моё»; both start off. */
export function BodySettingsDrawer({ open, settings, goals, onClose, onSettingsChange }: BodySettingsDrawerProps) {
  const { t } = useLocale()
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const binaryGoals = goals.filter((goal) => goal.tracking_kind === 'binary')

  const save = async (patch: Partial<BodySettings>) => {
    setIsSaving(true)
    setError(null)
    try {
      onSettingsChange(await updateBodySettings(patch))
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedSave'))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <EditorDrawer open={open} title={t('body.settingsTitle')} description={t('body.settingsHint')} onClose={onClose}>
      <div className="form">
        <PageErrorAlert error={error} />
        <label className="body-check">
          <input
            type="checkbox"
            checked={settings.show_weight}
            disabled={isSaving}
            onChange={(event) => void save({ show_weight: event.target.checked })}
          />
          <span>
            <strong>{t('body.showWeight')}</strong>
            <span className="my-level-hint">{t('body.showWeightHint')}</span>
          </span>
        </label>
        <label className="body-check">
          <input
            type="checkbox"
            checked={settings.show_food}
            disabled={isSaving}
            onChange={(event) => void save({ show_food: event.target.checked })}
          />
          <span>
            <strong>{t('body.showFood')}</strong>
            <span className="my-level-hint">{t('body.showFoodHint')}</span>
          </span>
        </label>
        {settings.show_food && binaryGoals.length > 0 ? (
          <div className="body-goals">
            <span className="form-label">{t('body.foodGoals')}</span>
            {Array.from({ length: MAX_FOOD_GOALS }, (_, slot) => {
              const current = settings.food_goal_ids[slot] ?? ''
              // A slot opens only after the one before it is filled.
              if (slot > settings.food_goal_ids.length) return null
              const taken = settings.food_goal_ids.filter((id) => id !== current)
              return (
                <select
                  key={slot}
                  className="form-input"
                  value={current}
                  disabled={isSaving}
                  aria-label={t('body.foodGoalSlot', { number: slot + 1 })}
                  onChange={(event) => {
                    const next = [...settings.food_goal_ids]
                    if (event.target.value) next[slot] = event.target.value
                    else next.splice(slot, 1)
                    void save({ food_goal_ids: next })
                  }}
                >
                  <option value="">{t('body.foodGoalNone')}</option>
                  {binaryGoals
                    .filter((goal) => !taken.includes(goal.id))
                    .map((goal) => (
                      <option key={goal.id} value={goal.id}>
                        {goal.label}
                      </option>
                    ))}
                </select>
              )
            })}
          </div>
        ) : null}
      </div>
    </EditorDrawer>
  )
}

type CopyPeriod = 'today' | 'week' | 'month' | 'custom'
const COPY_PERIODS: CopyPeriod[] = ['today', 'week', 'month', 'custom']
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

type FoodCopyDrawerProps = {
  open: boolean
  today: string
  timeZone: string
  onClose: () => void
}

/** Food for a period as plain text, ready to paste into a chat with an assistant. */
export function FoodCopyDrawer({ open, today, timeZone, onClose }: FoodCopyDrawerProps) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const [period, setPeriod] = useState<CopyPeriod>('week')
  const [customFrom, setCustomFrom] = useState(shiftDateKey(today, -6))
  const [customTo, setCustomTo] = useState(today)
  const [withWeight, setWithWeight] = useState(true)
  const [withMood, setWithMood] = useState(true)
  const [text, setText] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [from, to] = (() => {
    if (period === 'today') return [today, today]
    if (period === 'week') return [shiftDateKey(today, -6), today]
    if (period === 'month') return [shiftDateKey(today, -29), today]
    return customFrom <= customTo ? [customFrom, customTo] : [customTo, customFrom]
  })()
  const tooLong = dayNumber(to) - dayNumber(from) > HISTORY_DAYS

  useEffect(() => {
    if (!open || tooLong) return
    let cancelled = false
    const build = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const [food, weights, moods] = await Promise.all([
          listFood(from, to),
          withWeight ? listWeights(from, to) : Promise.resolve([]),
          withMood ? loadMoodLabels(from, to, timeZone) : Promise.resolve(new Map<string, string[]>()),
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
        const lines = [t('body.copyHeading', { range }), t('body.copyGaps')]
        const days = [...new Set(food.map((log) => log.day))].sort()
        for (const day of days) {
          const heading = formatDay(day, dateLocale, { weekday: 'short', day: 'numeric', month: 'long' })
          lines.push('', heading.charAt(0).toUpperCase() + heading.slice(1))
          const meals = food
            .filter((log) => log.day === day)
            .sort((a, b) => (a.meal ? MEALS.indexOf(a.meal) : MEALS.length) - (b.meal ? MEALS.indexOf(b.meal) : MEALS.length))
          for (const log of meals) {
            lines.push(log.meal ? `- ${t(`body.meal.${log.meal}`)}: ${log.text}` : `- ${log.text}`)
          }
          const extra: string[] = []
          const weight = weights.find((point) => point.day === day)
          if (weight) extra.push(t('body.copyWeight', { value: numberFormat.format(weight.value) }))
          const mood = moods.get(day)
          if (mood?.length) extra.push(t('body.copyMood', { labels: mood.join(', ') }))
          if (extra.length > 0) lines.push(extra.join(' · '))
        }
        setText(days.length === 0 ? '' : lines.join('\n'))
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
  }, [open, from, to, tooLong, withWeight, withMood, timeZone, dateLocale, t])

  useEffect(() => setCopied(false), [text])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      // Some webviews block the async clipboard; fall back to a selected textarea.
      const area = document.createElement('textarea')
      area.value = text
      area.setAttribute('readonly', '')
      area.style.position = 'fixed'
      area.style.opacity = '0'
      document.body.appendChild(area)
      area.select()
      document.execCommand('copy')
      area.remove()
    }
    setCopied(true)
  }

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
            onClick={() => void copy()}
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
          <label className="body-check">
            <input type="checkbox" checked={withWeight} onChange={(event) => setWithWeight(event.target.checked)} />
            <span>{t('body.copyWithWeight')}</span>
          </label>
          <label className="body-check">
            <input type="checkbox" checked={withMood} onChange={(event) => setWithMood(event.target.checked)} />
            <span>{t('body.copyWithMood')}</span>
          </label>
        </div>
        {tooLong ? (
          <p className="my-empty">{t('body.copyTooLong')}</p>
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
