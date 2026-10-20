import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'

import { setGoalCheckin } from '../api/goals'
import {
  createFood,
  deleteFood,
  deleteWeight,
  listExercises,
  listFood,
  listSleep,
  listWeights,
  listWorkoutSets,
  setWeight,
  updateBodySettings,
  updateFood,
} from '../api/body'
import { BodyCopyDrawer } from './BodyCopyDrawer'
import { EditorDrawer } from './EditorDrawer'
import { PageErrorAlert } from './PageErrorAlert'
import { SleepDrawer, SleepSection, SleepStatsDrawer } from './SleepSection'
import { StableButtonLabel } from './StableButtonLabel'
import { WeightChart, WeightStatsDrawer } from './WeightStats'
import { WorkoutDrawer, WorkoutSection, type WorkoutTarget } from './WorkoutSection'
import { useLocale } from '../context/LocaleContext'
import { intlLocale } from '../i18n/t'
import { dayNumber, formatDay, weekAverage } from '../lib/bodyFormat'
import { shiftDateKey } from '../lib/datetime'
import { sleepNormOf } from '../lib/sleep'
import { formatApiError } from '../lib/errors'
import {
  type FoodInputMode,
  type FoodItem,
  emptyItem,
  formatFoodLine,
  parseFoodItems,
  readFoodInputMode,
  saveFoodInputMode,
  serializeFoodItems,
} from '../lib/foodItems'
import { type FoodSuggestion, buildFoodSuggestions, hasFoodItem, matchFoodSuggestions } from '../lib/foodSuggestions'
import type { BodySettings, Exercise, FoodLog, Meal, SleepLog, WeightPoint, WorkoutSet } from '../types/body'
import type { GoalPublic } from '../types/goal'

const MEALS: Meal[] = ['morning', 'day', 'evening', 'snack']
const MIN_WEIGHT = 20
const MAX_WEIGHT = 400
const MAX_FOOD_GOALS = 3
// The longest chart range; the card reads its summary from the same points.
const HISTORY_DAYS = 365
const SPARK_DAYS = 60
const MIN_HEIGHT = 100
const MAX_HEIGHT = 250
// The usual adult range, a starting point the person can change (GP-61).
const DEFAULT_SLEEP_NORM = { min: 7 * 60, max: 9 * 60 }
const MIN_SLEEP_NORM_HOURS = 3
const MAX_SLEEP_NORM_HOURS = 15

/** Minutes as "7" or "7,5" hours for the norm inputs, with the locale's decimal mark. */
function hoursText(minutes: number, locale: string): string {
  const value = String(Math.round((minutes / 60) * 10) / 10)
  return locale === 'ru' ? value.replace('.', ',') : value
}

/** "7,5" hours to minutes, rounded to 5 minutes; null if empty or out of range. */
function parseNormHours(raw: string): number | null {
  const value = Number.parseFloat(raw.replace(',', '.'))
  if (!Number.isFinite(value) || value < MIN_SLEEP_NORM_HOURS || value > MAX_SLEEP_NORM_HOURS) return null
  return Math.round((value * 60) / 5) * 5
}

// Food items from this many days back are offered again while writing (GP-59).
const SUGGESTION_DAYS = 90
const FREQUENT_FOODS = 8

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

/** Weight, sleep, workouts and food on «Моё» (GP-47, GP-48, GP-58): no targets, no calories, nothing to fall behind on. */
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
  const [weightStatsOpen, setWeightStatsOpen] = useState(false)
  // The day the weight drawer edits, and whether closing it goes back to the stats.
  const [weightTarget, setWeightTarget] = useState<{ day: string; fromStats: boolean } | null>(null)
  const [foodTarget, setFoodTarget] = useState<{ day: string; log: FoodLog | null } | null>(null)
  const [foodDay, setFoodDay] = useState(asOf)
  const [copyOpen, setCopyOpen] = useState(false)
  const [sleep, setSleepLogs] = useState<SleepLog[]>([])
  const [sleepStatsOpen, setSleepStatsOpen] = useState(false)
  const [sleepTarget, setSleepTarget] = useState<{ day: string; fromStats: boolean } | null>(null)
  const [exercises, setExercises] = useState<Exercise[]>([])
  const [workoutSets, setWorkoutSets] = useState<WorkoutSet[]>([])
  const [workoutTarget, setWorkoutTarget] = useState<WorkoutTarget | null>(null)
  // Past food notes for suggestions; loaded the first time the food drawer opens.
  const [foodHistory, setFoodHistory] = useState<FoodLog[] | null>(null)

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

  const loadSleep = useCallback(async () => {
    setSleepLogs(await listSleep(shiftDateKey(today, -HISTORY_DAYS), today))
  }, [today])

  useEffect(() => {
    if (!settings.show_sleep) return
    void loadSleep().catch((err) => setError(formatApiError(err, t, 'errors.requestFailed')))
  }, [settings.show_sleep, loadSleep, t])

  const loadWorkouts = useCallback(async () => {
    const [nextExercises, nextSets] = await Promise.all([
      listExercises(),
      listWorkoutSets(shiftDateKey(today, -HISTORY_DAYS), today),
    ])
    setExercises(nextExercises)
    setWorkoutSets(nextSets)
  }, [today])

  useEffect(() => {
    if (!settings.show_workouts) return
    void loadWorkouts().catch((err) => setError(formatApiError(err, t, 'errors.requestFailed')))
  }, [settings.show_workouts, loadWorkouts, t])

  useEffect(() => {
    if (foodTarget === null || foodHistory !== null) return
    // Suggestions are a nicety: without them the drawer works as before.
    void listFood(shiftDateKey(today, -SUGGESTION_DAYS + 1), today)
      .then(setFoodHistory)
      .catch(() => setFoodHistory([]))
  }, [foodTarget, foodHistory, today])

  const foodSuggestions = useMemo(() => buildFoodSuggestions(foodHistory ?? []), [foodHistory])
  const sleepNorm = sleepNormOf(settings)

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
  const foodGoals = settings.food_goal_ids
    .map((id) => goals.find((goal) => goal.id === id))
    .filter((goal): goal is GoalPublic => goal !== undefined)

  return (
    <section className="card my-card body-card" aria-labelledby="my-body-title">
      <div className="my-card-head">
        <h2 id="my-body-title">{t('body.title')}</h2>
        <div className="body-head-links">
          <button type="button" className="link-button my-card-link" onClick={() => setCopyOpen(true)}>
            {t('body.copyOpen')}
          </button>
          <button type="button" className="link-button my-card-link" onClick={onOpenSettings}>
            {t('body.configure')}
          </button>
        </div>
      </div>
      <PageErrorAlert error={error} />

      {settings.show_weight ? (
        <div className="body-weight">
          {shown === null ? (
            <p className="my-empty">{t('body.weightEmpty')}</p>
          ) : (
            // The whole summary opens the stats (GP-60); a hidden number stays hidden until revealed there.
            <button
              type="button"
              className="body-weight-summary body-stats-open"
              aria-label={t('body.statsOpen', { title: t('body.weightTitle') })}
              onClick={() => setWeightStatsOpen(true)}
            >
              <span className="body-weight-text">
                <span className="body-label">
                  {average !== null ? t('body.weightAverage') : t('body.weightLast')}
                </span>
                <span className={`body-weight-value${settings.hide_weight ? ' is-hidden' : ''}`}>
                  {numberFormat.format(shown)} <small>{t('body.kg')}</small>
                </span>
                {latest ? (
                  <span className="body-label">
                    {t('body.lastMeasured', { date: latestLabel(latest.day) })}
                  </span>
                ) : null}
              </span>
              {!settings.hide_weight ? (
                <WeightChart points={spark} width={120} height={48} className="body-spark" />
              ) : null}
              <span className="body-chevron" aria-hidden>
                ›
              </span>
            </button>
          )}
          <button
            type="button"
            className="button button-secondary body-wide"
            onClick={() => setWeightTarget({ day: today, fromStats: false })}
          >
            {t('body.recordWeight')}
          </button>
        </div>
      ) : null}

      {settings.show_sleep ? (
        <SleepSection
          logs={sleep}
          asOf={asOf}
          today={today}
          weekDays={weekDays}
          norm={sleepNorm}
          onRecord={() => setSleepTarget({ day: today, fromStats: false })}
          onOpenStats={() => setSleepStatsOpen(true)}
        />
      ) : null}

      {settings.show_workouts ? (
        <WorkoutSection
          exercises={exercises}
          sets={workoutSets}
          today={today}
          weekDays={weekDays}
          onRecord={() => setWorkoutTarget({ day: today, exerciseId: null })}
        />
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
          </div>
        </div>
      ) : null}

      <WeightStatsDrawer
        open={weightStatsOpen}
        today={today}
        weights={weights}
        settings={settings}
        onClose={() => setWeightStatsOpen(false)}
        onRecord={(day) => {
          setWeightStatsOpen(false)
          setWeightTarget({ day, fromStats: true })
        }}
        onSettingsChange={onSettingsChange}
        onOpenSettings={() => {
          setWeightStatsOpen(false)
          onOpenSettings()
        }}
      />
      <WeightDrawer
        target={weightTarget?.day ?? null}
        today={today}
        weights={weights}
        onClose={() => {
          if (weightTarget?.fromStats) setWeightStatsOpen(true)
          setWeightTarget(null)
        }}
        onChanged={loadWeights}
      />
      <SleepStatsDrawer
        open={sleepStatsOpen}
        today={today}
        logs={sleep}
        norm={sleepNorm}
        onClose={() => setSleepStatsOpen(false)}
        onRecord={(day) => {
          setSleepStatsOpen(false)
          setSleepTarget({ day, fromStats: true })
        }}
      />
      <SleepDrawer
        target={sleepTarget?.day ?? null}
        today={today}
        logs={sleep}
        onClose={() => {
          if (sleepTarget?.fromStats) setSleepStatsOpen(true)
          setSleepTarget(null)
        }}
        onChanged={loadSleep}
      />
      <WorkoutDrawer
        target={workoutTarget}
        today={today}
        exercises={exercises}
        sets={workoutSets}
        onClose={() => setWorkoutTarget(null)}
        onChanged={loadWorkouts}
      />
      <BodyCopyDrawer
        open={copyOpen}
        today={today}
        timeZone={timeZone}
        settings={settings}
        onClose={() => setCopyOpen(false)}
      />
      <FoodDrawer
        target={foodTarget}
        today={today}
        goals={foodGoals}
        suggestions={foodSuggestions}
        onClose={() => setFoodTarget(null)}
        onSaved={async () => {
          setFoodTarget(null)
          // The next drawer offers what was just written too.
          setFoodHistory(null)
          await loadFood()
        }}
        onGoalChange={onGoalChange}
      />
    </section>
  )
}

type WeightDrawerProps = {
  /** The day to record or edit; null keeps the drawer closed. */
  target: string | null
  today: string
  weights: WeightPoint[]
  onClose: () => void
  onChanged: () => Promise<void>
}

/** Only the input: the chart, BMI and the list live in the weight stats drawer (GP-60). */
function WeightDrawer({ target, today, weights, onClose, onChanged }: WeightDrawerProps) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const open = target !== null
  const [day, setDay] = useState(today)
  const [raw, setRaw] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const existing = weights.find((point) => point.day === day) ?? null

  useEffect(() => {
    if (target === null) return
    setDay(target)
    setError(null)
  }, [target])

  useEffect(() => {
    if (!open) return
    const point = weights.find((item) => item.day === day)
    setRaw(point ? String(point.value).replace('.', locale === 'ru' ? ',' : '.') : '')
    // Only when the day changes, not after every save.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, day])

  const value = parseWeight(raw)

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
        <p className="my-gentle muted">{t('body.weightGentle')}</p>
      </form>
    </EditorDrawer>
  )
}

type FoodDrawerProps = {
  target: { day: string; log: FoodLog | null } | null
  today: string
  goals: GoalPublic[]
  /** Items from past notes, most frequent first (GP-59). */
  suggestions: FoodSuggestion[]
  onClose: () => void
  onSaved: () => Promise<void>
  onGoalChange: (goal: GoalPublic) => void
}

function FoodDrawer({ target, today, goals, suggestions, onClose, onSaved, onGoalChange }: FoodDrawerProps) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const [meal, setMeal] = useState<Meal | null>(null)
  const [text, setText] = useState('')
  const [mode, setMode] = useState<FoodInputMode>(readFoodInputMode)
  const [items, setItems] = useState<FoodItem[]>([emptyItem()])
  const [focusRow, setFocusRow] = useState<number | null>(null)
  // The list row being typed in, whose matches show under it.
  const [activeRow, setActiveRow] = useState<number | null>(null)
  const [marked, setMarked] = useState<string[]>([])
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!target) return
    setMeal(target.log ? target.log.meal : target.day === today ? mealNow() : null)
    setText(target.log?.text ?? '')
    setItems(parseFoodItems(target.log?.text ?? ''))
    setFocusRow(null)
    setActiveRow(null)
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

  const unit = t('body.gramsUnit')
  const finalText = mode === 'list' ? serializeFoodItems(items, unit) : text.trim()
  const tooLong = finalText.length > 500
  const canSave = finalText.length > 0 && !tooLong && !isSaving

  const switchMode = (next: FoodInputMode) => {
    if (next === mode) return
    // Carry what is typed over, so switching never loses a note.
    if (next === 'list') setItems(parseFoodItems(text))
    else setText(serializeFoodItems(items, unit))
    setMode(next)
    saveFoodInputMode(next)
  }

  const changeItem = (index: number, patch: Partial<FoodItem>) =>
    setItems((current) => current.map((item, i) => (i === index ? { ...item, ...patch } : item)))

  const addItem = () => {
    setItems((current) => [...current, emptyItem()])
    setFocusRow(items.length)
  }

  const written = mode === 'list' ? items.map((item) => item.name) : parseFoodItems(text).map((item) => item.name)
  const frequent = suggestions.filter((item) => !hasFoodItem(written, item)).slice(0, FREQUENT_FOODS)

  const pickFrequent = (suggestion: FoodSuggestion) => {
    const picked = { name: suggestion.name, grams: suggestion.grams }
    if (mode === 'text') {
      const line = formatFoodLine(picked, unit)
      setText((current) => (current.trim() ? `${current.replace(/\s+$/, '')}\n${line}` : line))
      return
    }
    setItems((current) => {
      const empty = current.findIndex((item) => !item.name.trim())
      if (empty === -1) return [...current, picked]
      return current.map((item, i) => (i === empty ? { name: picked.name, grams: item.grams || picked.grams } : item))
    })
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!target || !canSave) return
    setIsSaving(true)
    setError(null)
    try {
      if (target.log) {
        await updateFood(target.log.id, { meal, text: finalText })
      } else {
        await createFood({ day, meal, text: finalText })
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
        <div className="body-range body-food-mode" role="radiogroup" aria-label={t('body.foodMode')}>
          {(['text', 'list'] as FoodInputMode[]).map((item) => (
            <button
              key={item}
              type="button"
              role="radio"
              aria-checked={mode === item}
              className={mode === item ? 'is-selected' : ''}
              onClick={() => switchMode(item)}
            >
              {t(`body.foodModes.${item}`)}
            </button>
          ))}
        </div>
        {frequent.length > 0 ? (
          <div className="body-food-frequent">
            <span className="body-label">{t('body.foodFrequent')}</span>
            <div className="body-meals">
              {frequent.map((item) => (
                <button key={item.name} type="button" className="body-meal" onClick={() => pickFrequent(item)}>
                  {item.name}
                </button>
              ))}
            </div>
          </div>
        ) : null}
        {mode === 'text' ? (
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
        ) : (
          <div className="body-food-items">
            {items.map((item, index) => {
              const matches = activeRow === index ? matchFoodSuggestions(suggestions, item.name) : []
              return (
              <div key={index} className="body-food-item">
                <input
                  className="form-input"
                  value={item.name}
                  autoComplete="off"
                  onFocus={() => setActiveRow(index)}
                  onBlur={() => setActiveRow((current) => (current === index ? null : current))}
                  placeholder={index === 0 ? t('body.foodItemPlaceholder') : ''}
                  aria-label={t('body.foodItem', { number: index + 1 })}
                  maxLength={200}
                  autoFocus={focusRow === index || (focusRow === null && index === 0)}
                  onChange={(event) => changeItem(index, { name: event.target.value })}
                  onKeyDown={(event) => {
                    // Enter goes on to the grams instead of saving half a list.
                    if (event.key === 'Enter') {
                      event.preventDefault()
                      ;(event.currentTarget.nextElementSibling as HTMLInputElement | null)?.focus()
                    }
                  }}
                />
                <input
                  className="form-input body-food-grams"
                  inputMode="numeric"
                  value={item.grams}
                  placeholder={unit}
                  aria-label={t('body.foodGrams')}
                  onChange={(event) => changeItem(index, { grams: event.target.value.replace(/[^0-9]/g, '').slice(0, 4) })}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      event.preventDefault()
                      addItem()
                    }
                  }}
                />
                {items.length > 1 ? (
                  <button
                    type="button"
                    className="body-food-remove"
                    aria-label={t('body.foodItemRemove')}
                    onClick={() => setItems((current) => current.filter((_, i) => i !== index))}
                  >
                    ×
                  </button>
                ) : null}
                {matches.length > 0 ? (
                  <ul className="body-food-suggest" role="listbox" aria-label={t('body.foodSuggestions')}>
                    {matches.map((match) => (
                      <li key={match.name}>
                        <button
                          type="button"
                          role="option"
                          aria-selected={false}
                          // Keep focus in the field so the list does not close before the tap lands.
                          onMouseDown={(event) => event.preventDefault()}
                          onClick={() => {
                            changeItem(index, { name: match.name, grams: item.grams || match.grams })
                            setActiveRow(null)
                          }}
                        >
                          <span>{match.name}</span>
                          {match.grams ? (
                            <span className="body-label">{t('body.foodUsually', { grams: match.grams, unit })}</span>
                          ) : null}
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
              )
            })}
            <button type="button" className="link-button body-food-add" onClick={addItem}>
              ＋ {t('body.foodItemAdd')}
            </button>
            <span className="my-level-hint">{t('body.foodGramsHint')}</span>
          </div>
        )}
        {tooLong ? <span className="my-level-hint">{t('body.foodTooLong')}</span> : null}
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

/** Turn weight, sleep, workouts and food on or off for «Моё»; all start off. */
export function BodySettingsDrawer({ open, settings, goals, onClose, onSettingsChange }: BodySettingsDrawerProps) {
  const { locale, t } = useLocale()
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const binaryGoals = goals.filter((goal) => goal.tracking_kind === 'binary')
  const [height, setHeight] = useState('')
  const [normFrom, setNormFrom] = useState('')
  const [normTo, setNormTo] = useState('')

  useEffect(() => {
    if (open) setHeight(settings.height_cm === null ? '' : String(settings.height_cm))
  }, [open, settings.height_cm])

  useEffect(() => {
    if (!open) return
    setNormFrom(settings.sleep_norm_min === null ? '' : hoursText(settings.sleep_norm_min, locale))
    setNormTo(settings.sleep_norm_max === null ? '' : hoursText(settings.sleep_norm_max, locale))
  }, [open, settings.sleep_norm_min, settings.sleep_norm_max, locale])

  const normMin = parseNormHours(normFrom)
  const normMax = parseNormHours(normTo)
  const normValid = normMin !== null && normMax !== null && normMin < normMax
  const saveNorm = () => {
    if (!normValid) return
    if (normMin !== settings.sleep_norm_min || normMax !== settings.sleep_norm_max) {
      void save({ sleep_norm_min: normMin, sleep_norm_max: normMax })
    }
  }

  const parsedHeight = Number.parseFloat(height.replace(',', '.'))
  const heightValid = height === '' || (Number.isFinite(parsedHeight) && parsedHeight >= MIN_HEIGHT && parsedHeight <= MAX_HEIGHT)
  const saveHeight = () => {
    if (!heightValid) return
    const next = height === '' ? null : Math.round(parsedHeight * 10) / 10
    if (next !== settings.height_cm) void save({ height_cm: next })
  }

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
        {settings.show_weight ? (
          <label className="body-height">
            <span className="form-label">{t('body.height')}</span>
            <span className="my-amount-row">
              <input
                className="form-input"
                inputMode="decimal"
                value={height}
                placeholder="175"
                onChange={(event) => setHeight(event.target.value.replace(/[^0-9.,]/g, ''))}
                onBlur={saveHeight}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') saveHeight()
                }}
              />
              <span className="muted">{t('body.cm')}</span>
            </span>
            <span className="my-level-hint">
              {heightValid ? t('body.heightHint') : t('body.heightRange', { min: MIN_HEIGHT, max: MAX_HEIGHT })}
            </span>
          </label>
        ) : null}
        <label className="body-check">
          <input
            type="checkbox"
            checked={settings.show_sleep}
            disabled={isSaving}
            onChange={(event) => void save({ show_sleep: event.target.checked })}
          />
          <span>
            <strong>{t('body.showSleep')}</strong>
            <span className="my-level-hint">{t('body.showSleepHint')}</span>
          </span>
        </label>
        {settings.show_sleep ? (
          <div className="body-sleep-norm">
            <label className="body-check">
              <input
                type="checkbox"
                checked={settings.sleep_norm_min !== null}
                disabled={isSaving}
                onChange={(event) =>
                  void save(
                    event.target.checked
                      ? { sleep_norm_min: DEFAULT_SLEEP_NORM.min, sleep_norm_max: DEFAULT_SLEEP_NORM.max }
                      : { sleep_norm_min: null, sleep_norm_max: null },
                  )
                }
              />
              <span>
                <strong>{t('body.sleepNormTitle')}</strong>
                <span className="my-level-hint">{t('body.sleepNormHint')}</span>
              </span>
            </label>
            {settings.sleep_norm_min !== null ? (
              <span className="my-amount-row body-sleep-norm-range">
                <input
                  className="form-input"
                  inputMode="decimal"
                  value={normFrom}
                  aria-label={t('body.sleepNormFrom')}
                  onChange={(event) => setNormFrom(event.target.value.replace(/[^0-9.,]/g, ''))}
                  onBlur={saveNorm}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') saveNorm()
                  }}
                />
                <span className="muted">—</span>
                <input
                  className="form-input"
                  inputMode="decimal"
                  value={normTo}
                  aria-label={t('body.sleepNormTo')}
                  onChange={(event) => setNormTo(event.target.value.replace(/[^0-9.,]/g, ''))}
                  onBlur={saveNorm}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') saveNorm()
                  }}
                />
                <span className="muted">{t('body.hoursShort')}</span>
              </span>
            ) : null}
            {settings.sleep_norm_min !== null && !normValid ? (
              <span className="my-level-hint">{t('body.sleepNormRange')}</span>
            ) : null}
          </div>
        ) : null}
        <label className="body-check">
          <input
            type="checkbox"
            checked={settings.show_workouts}
            disabled={isSaving}
            onChange={(event) => void save({ show_workouts: event.target.checked })}
          />
          <span>
            <strong>{t('body.showWorkouts')}</strong>
            <span className="my-level-hint">{t('body.showWorkoutsHint')}</span>
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
