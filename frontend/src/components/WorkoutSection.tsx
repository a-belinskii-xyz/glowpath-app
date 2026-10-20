import { type FormEvent, useEffect, useMemo, useState } from 'react'

import { createExercise, deleteExercise, setWorkout, updateExercise } from '../api/body'
import { BODY_RANGES, type BodyRange, BodyRangeSwitch } from './BodyRange'
import { EditorDrawer } from './EditorDrawer'
import { PageErrorAlert } from './PageErrorAlert'
import { StableButtonLabel } from './StableButtonLabel'
import { useLocale } from '../context/LocaleContext'
import { intlLocale, tp } from '../i18n/t'
import { dayNumber, formatDay } from '../lib/bodyFormat'
import { shiftDateKey } from '../lib/datetime'
import { formatApiError } from '../lib/errors'
import {
  type ProgressMetric,
  type Session,
  bestSet,
  formatSets,
  parseReps,
  parseSetWeight,
  sessionValue,
  sessionsOf,
} from '../lib/workouts'
import type { Exercise, WorkoutSet } from '../types/body'

const SHOWN_EXERCISES = 4
const SPARK_DAYS = 90
const CHIP_EXERCISES = 8

type Point = { day: string; value: number }

/** A plain line with a dot per session; the band is padded so small steps do not look like jumps. */
function ProgressChart({ points, height, showDots, className }: { points: Point[]; height: number; showDots?: boolean; className?: string }) {
  if (points.length < 2) return null
  const width = 360
  const values = points.map((point) => point.value)
  const low = Math.min(...values)
  const high = Math.max(...values)
  const pad = Math.max((high - low) * 0.15, high * 0.05, 1)
  const min = low - pad
  const max = high + pad
  const first = dayNumber(points[0].day)
  const span = Math.max(dayNumber(points[points.length - 1].day) - first, 1)
  const x = (day: string) => 4 + ((dayNumber(day) - first) / span) * (width - 8)
  const y = (value: number) => 4 + ((max - value) / (max - min)) * (height - 8)
  const path = points.map((point, index) => `${index ? 'L' : 'M'}${x(point.day).toFixed(1)},${y(point.value).toFixed(1)}`)
  return (
    <svg className={className} viewBox={`0 0 ${width} ${height}`} width="100%" height={height} preserveAspectRatio="none" aria-hidden>
      <path className="body-chart-line" d={path.join(' ')} vectorEffect="non-scaling-stroke" />
      {showDots
        ? points.map((point) => (
            <circle key={point.day} className="body-progress-dot" cx={x(point.day)} cy={y(point.value)} r={3} />
          ))
        : null}
    </svg>
  )
}

function useSetWords() {
  const { locale, t } = useLocale()
  return useMemo(() => {
    const numbers = new Intl.NumberFormat(intlLocale(locale), { maximumFractionDigits: 2 })
    const words = { kg: t('body.kg'), reps: (list: string) => t('body.repsList', { list }) }
    return {
      numbers,
      describe: (sets: WorkoutSet[], withWeight: boolean) => formatSets(sets, withWeight, numbers, words),
    }
  }, [locale, t])
}

type WorkoutSectionProps = {
  exercises: Exercise[]
  sets: WorkoutSet[]
  today: string
  weekDays: string[]
  onRecord: () => void
  onOpenExercise: (exercise: Exercise) => void
}

/** Workouts on «Моё» (GP-58): the latest sets per exercise and a quiet line of how they grow. */
export function WorkoutSection({ exercises, sets, today, weekDays, onRecord, onOpenExercise }: WorkoutSectionProps) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const { describe } = useSetWords()
  const [expanded, setExpanded] = useState(false)
  const weekCount = new Set(sets.filter((set) => set.day >= weekDays[0] && set.day <= weekDays[6]).map((set) => set.day)).size
  const done = exercises.filter((exercise) => exercise.last_day !== null)
  const shown = expanded ? done : done.slice(0, SHOWN_EXERCISES)
  const sparkFrom = shiftDateKey(today, -SPARK_DAYS)

  return (
    <div className="body-workouts">
      <div className="body-food-head">
        <strong>{t('body.workoutsTitle')}</strong>
        {weekCount > 0 ? (
          <span className="body-label">
            {tp(locale, weekCount, {
              one: 'body.workoutsWeekOne',
              few: 'body.workoutsWeekFew',
              many: 'body.workoutsWeekMany',
            })}
          </span>
        ) : null}
      </div>
      {done.length === 0 ? (
        <p className="my-empty">{t('body.workoutsEmpty')}</p>
      ) : (
        <ul className="body-workout-list">
          {shown.map((exercise) => {
            const sessions = sessionsOf(sets, exercise.id)
            const last = sessions[sessions.length - 1]
            const spark = sessions
              .filter((session) => session.day >= sparkFrom)
              .map((session) => ({ day: session.day, value: sessionValue(session, exercise, 'best') }))
            return (
              <li key={exercise.id}>
                <button type="button" className="body-workout-row" onClick={() => onOpenExercise(exercise)}>
                  <span className="body-workout-text">
                    <strong>{exercise.name}</strong>
                    {last ? (
                      <span className="body-label">
                        {last.day === today
                          ? t('body.today')
                          : formatDay(last.day, dateLocale, { weekday: 'short', day: 'numeric', month: 'short' })}
                        {' · '}
                        {describe(last.sets, exercise.with_weight)}
                      </span>
                    ) : null}
                  </span>
                  <ProgressChart points={spark} height={28} className="body-workout-spark" />
                  <span className="body-chevron" aria-hidden>
                    ›
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
      {done.length > SHOWN_EXERCISES ? (
        <button type="button" className="link-button body-food-add" onClick={() => setExpanded((value) => !value)}>
          {expanded ? t('body.workoutsLess') : t('body.workoutsMore', { count: done.length })}
        </button>
      ) : null}
      <button type="button" className="button button-secondary body-wide" onClick={onRecord}>
        {t('body.workoutRecord')}
      </button>
    </div>
  )
}

type SetDraft = { weight: string; reps: string }

export type WorkoutTarget = { day: string; exerciseId: string | null }

type WorkoutDrawerProps = {
  target: WorkoutTarget | null
  today: string
  exercises: Exercise[]
  sets: WorkoutSet[]
  onClose: () => void
  onChanged: () => Promise<void>
}

/** Record the sets of one exercise on a day; "save and next" keeps the drawer for the next exercise. */
export function WorkoutDrawer({ target, today, exercises, sets, onClose, onChanged }: WorkoutDrawerProps) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const { numbers, describe } = useSetWords()
  const open = target !== null
  const [day, setDay] = useState(today)
  const [exerciseId, setExerciseId] = useState<string | null>(null)
  const [isNew, setIsNew] = useState(false)
  const [newName, setNewName] = useState('')
  const [newWithWeight, setNewWithWeight] = useState(true)
  const [rows, setRows] = useState<SetDraft[]>([])
  const [savedName, setSavedName] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const exercise = exercises.find((item) => item.id === exerciseId) ?? null
  const withWeight = isNew ? newWithWeight : (exercise?.with_weight ?? true)
  const chips = useMemo(
    () =>
      [...exercises]
        .sort((a, b) => b.recent_days - a.recent_days || (b.last_day ?? '').localeCompare(a.last_day ?? ''))
        .slice(0, CHIP_EXERCISES),
    [exercises],
  )
  // The chosen exercise stays visible even when it is not among the frequent ones.
  const shownChips = exercise && !chips.includes(exercise) ? [...chips, exercise] : chips
  const sessions = exercise ? sessionsOf(sets, exercise.id) : []
  const existing = sessions.find((session) => session.day === day) ?? null
  const previous = [...sessions].reverse().find((session) => session.day < day) ?? null

  const resetRows = (from: Session | null, before: Session | null) => {
    if (from) {
      setRows(from.sets.map((set) => ({ weight: set.weight_kg === null ? '' : numbers.format(set.weight_kg), reps: String(set.reps) })))
      return
    }
    // A new day starts from the weight used last time; reps are typed fresh.
    const first = before?.sets[0]
    setRows([{ weight: first?.weight_kg != null ? numbers.format(first.weight_kg) : '', reps: '' }])
  }

  useEffect(() => {
    if (!target) return
    setDay(target.day)
    setExerciseId(target.exerciseId)
    setIsNew(exercises.length === 0)
    setNewName('')
    setNewWithWeight(true)
    setSavedName(null)
    setError(null)
    // Only on opening.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target])

  useEffect(() => {
    if (!open) return
    resetRows(existing, previous)
    // Only when the exercise or day changes, not after every save.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, exerciseId, day, isNew])

  const parsed = rows.map((row) => ({
    weight: withWeight ? parseSetWeight(row.weight) : null,
    reps: parseReps(row.reps),
  }))
  const complete = parsed.filter((row) => row.reps !== null)
  const hasInvalid = rows.some(
    (row, index) => (row.reps !== '' && parsed[index].reps === null) || (withWeight && row.weight !== '' && parsed[index].weight === null),
  )
  const chosen = isNew ? newName.trim().length > 0 : exercise !== null
  const canSave = chosen && complete.length > 0 && !hasInvalid && !isSaving

  const save = async (next: boolean) => {
    if (!canSave) return
    setIsSaving(true)
    setError(null)
    try {
      const saved = isNew ? await createExercise({ name: newName.trim(), with_weight: newWithWeight }) : exercise
      if (!saved) return
      await setWorkout(
        day,
        saved.id,
        complete.map((row) => ({ weight_kg: row.weight, reps: row.reps as number })),
      )
      await onChanged()
      if (next) {
        setSavedName(saved.name)
        setExerciseId(null)
        setIsNew(false)
        setNewName('')
      } else {
        onClose()
      }
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedSave'))
    } finally {
      setIsSaving(false)
    }
  }

  const clearDay = async () => {
    if (!exercise) return
    setIsSaving(true)
    setError(null)
    try {
      await setWorkout(day, exercise.id, [])
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
    void save(false)
  }

  const updateRow = (index: number, patch: Partial<SetDraft>) =>
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)))

  return (
    <EditorDrawer
      open={open}
      title={isNew ? newName.trim() || t('body.workoutTitle') : (exercise?.name ?? t('body.workoutTitle'))}
      description={formatDay(day, dateLocale, { weekday: 'long', day: 'numeric', month: 'long' })}
      onClose={() => {
        if (!isSaving) onClose()
      }}
      footer={
        <div className="button-row">
          <button type="submit" form="body-workout-form" className="button my-primary" disabled={!canSave}>
            <StableButtonLabel
              active={isSaving ? t('common.saving') : t('common.save')}
              labels={[t('common.save'), t('common.saving')]}
            />
          </button>
          {existing && !isNew ? (
            <button type="button" className="button button-secondary" disabled={isSaving} onClick={() => void clearDay()}>
              {t('body.workoutDelete')}
            </button>
          ) : null}
        </div>
      }
    >
      <form id="body-workout-form" className="form" onSubmit={handleSubmit}>
        <PageErrorAlert error={error} />
        {savedName ? <p className="body-saved">{t('body.workoutSaved', { name: savedName })}</p> : null}
        <div className="body-meals" role="radiogroup" aria-label={t('body.exercisePick')}>
          {shownChips.map((item) => (
            <button
              key={item.id}
              type="button"
              role="radio"
              aria-checked={!isNew && exerciseId === item.id}
              className={`body-meal${!isNew && exerciseId === item.id ? ' is-selected' : ''}`}
              onClick={() => {
                setIsNew(false)
                setExerciseId(item.id)
              }}
            >
              {item.name}
            </button>
          ))}
          {exercises.length > CHIP_EXERCISES ? (
            <select
              className="form-input body-exercise-select"
              value=""
              aria-label={t('body.exerciseAll')}
              onChange={(event) => {
                if (!event.target.value) return
                setIsNew(false)
                setExerciseId(event.target.value)
              }}
            >
              <option value="">{t('body.exerciseAll')}</option>
              {[...exercises]
                .sort((a, b) => a.name.localeCompare(b.name, dateLocale))
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
            </select>
          ) : null}
          <button
            type="button"
            role="radio"
            aria-checked={isNew}
            className={`body-meal${isNew ? ' is-selected' : ''}`}
            onClick={() => {
              setIsNew(true)
              setExerciseId(null)
              setSavedName(null)
            }}
          >
            ＋ {t('body.exerciseNew')}
          </button>
        </div>

        {isNew ? (
          <>
            <input
              className="form-input"
              value={newName}
              maxLength={80}
              placeholder={t('body.exerciseNamePlaceholder')}
              aria-label={t('body.exerciseName')}
              onChange={(event) => setNewName(event.target.value)}
              autoFocus
            />
            <label className="body-check">
              <input type="checkbox" checked={!newWithWeight} onChange={(event) => setNewWithWeight(!event.target.checked)} />
              <span>{t('body.exerciseNoWeight')}</span>
            </label>
          </>
        ) : null}

        {chosen ? (
          <>
            {previous && exercise ? (
              <p className="body-label">
                {t('body.workoutLast', {
                  date: formatDay(previous.day, dateLocale, { weekday: 'short', day: 'numeric', month: 'short' }),
                  sets: describe(previous.sets, exercise.with_weight),
                })}
              </p>
            ) : null}
            <div className="body-sets">
              {rows.map((row, index) => {
                const hint = previous?.sets[index] ?? previous?.sets[previous.sets.length - 1]
                return (
                  <div key={index} className={`body-set${withWeight ? '' : ' is-bodyweight'}`}>
                    <span className="body-set-number">{index + 1}</span>
                    {withWeight ? (
                      <span className="body-set-field">
                        <input
                          className="form-input"
                          inputMode="decimal"
                          value={row.weight}
                          placeholder={hint?.weight_kg != null ? numbers.format(hint.weight_kg) : '0'}
                          aria-label={t('body.setWeight', { number: index + 1 })}
                          onChange={(event) => updateRow(index, { weight: event.target.value.replace(/[^0-9.,]/g, '') })}
                        />
                        <span className="muted">{t('body.kg')}</span>
                      </span>
                    ) : null}
                    {withWeight ? (
                      <span className="body-set-times" aria-hidden>
                        ×
                      </span>
                    ) : null}
                    <span className="body-set-field">
                      <input
                        className="form-input"
                        inputMode="numeric"
                        value={row.reps}
                        placeholder={hint ? String(hint.reps) : t('body.repsPlaceholder')}
                        aria-label={t('body.setReps', { number: index + 1 })}
                        onChange={(event) => updateRow(index, { reps: event.target.value.replace(/\D/g, '').slice(0, 4) })}
                      />
                      <span className="muted">{t('body.repsUnit')}</span>
                    </span>
                    <button
                      type="button"
                      className="body-food-remove"
                      aria-label={t('body.setRemove')}
                      disabled={rows.length === 1}
                      onClick={() => setRows((current) => current.filter((_, i) => i !== index))}
                    >
                      ×
                    </button>
                  </div>
                )
              })}
              {rows.length < 30 ? (
                <button
                  type="button"
                  className="link-button body-food-add"
                  onClick={() =>
                    // The next set usually repeats the one before it.
                    setRows((current) => [...current, { ...(current[current.length - 1] ?? { weight: '', reps: '' }) }])
                  }
                >
                  ＋ {t('body.setAdd')}
                </button>
              ) : null}
            </div>
            {hasInvalid ? <span className="my-level-hint">{t('body.setInvalid')}</span> : null}
          </>
        ) : (
          <p className="my-empty">{t('body.workoutPickFirst')}</p>
        )}

        {chosen ? (
          <button type="button" className="link-button body-workout-next" disabled={!canSave} onClick={() => void save(true)}>
            {t('body.workoutSaveNext')}
          </button>
        ) : null}
        <div className="body-sleep-meta">
          <span className="body-label">{t('body.workoutDay')}</span>
          <input
            className="form-input body-date"
            type="date"
            max={today}
            value={day}
            aria-label={t('body.workoutDay')}
            onChange={(event) => {
              if (event.target.value && event.target.value <= today) setDay(event.target.value)
            }}
          />
        </div>
        <p className="my-gentle muted">{t('body.workoutGentle')}</p>
      </form>
    </EditorDrawer>
  )
}

type ExerciseDrawerProps = {
  exercise: Exercise | null
  sets: WorkoutSet[]
  today: string
  onClose: () => void
  onRecord: (exerciseId: string, day: string) => void
  onChanged: () => Promise<void>
}

/** One exercise over time: the chart, then and now, the history, and renaming. */
export function ExerciseDrawer({ exercise, sets, today, onClose, onRecord, onChanged }: ExerciseDrawerProps) {
  const { locale, t } = useLocale()
  const dateLocale = intlLocale(locale)
  const { numbers, describe } = useSetWords()
  const [range, setRange] = useState<BodyRange>('quarter')
  const [metric, setMetric] = useState<ProgressMetric>('best')
  const [name, setName] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!exercise) return
    setName(exercise.name)
    setConfirmDelete(false)
    setError(null)
    // Only when another exercise opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exercise?.id])

  if (!exercise) return <EditorDrawer open={false} title="" onClose={onClose}>{null}</EditorDrawer>

  const sessions = sessionsOf(sets, exercise.id)
  const from = shiftDateKey(today, -BODY_RANGES[range] + 1)
  const inRange = sessions.filter((session) => session.day >= from)
  const points = inRange.map((session) => ({ day: session.day, value: sessionValue(session, exercise, metric) }))
  const first = inRange[0]
  const last = inRange[inRange.length - 1]
  const metrics = exercise.with_weight ? 'metric' : 'metricBodyweight'
  const formatBest = (session: Session) => {
    if (metric === 'volume') {
      const value = numbers.format(sessionValue(session, exercise, 'volume'))
      return exercise.with_weight ? `${value} ${t('body.kg')}` : t('body.repsList', { list: value })
    }
    const best = bestSet(session.sets)
    return best ? describe([best], exercise.with_weight) : ''
  }

  const run = async (action: () => Promise<unknown>, close: boolean) => {
    setIsSaving(true)
    setError(null)
    try {
      await action()
      await onChanged()
      if (close) onClose()
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedSave'))
    } finally {
      setIsSaving(false)
    }
  }

  const trimmed = name.trim()

  return (
    <EditorDrawer
      open
      title={exercise.name}
      description={exercise.with_weight ? undefined : t('body.exerciseNoWeight')}
      onClose={() => {
        if (!isSaving) onClose()
      }}
      footer={
        <div className="button-row">
          <button type="button" className="button my-primary" onClick={() => onRecord(exercise.id, today)}>
            {t('body.workoutRecord')}
          </button>
        </div>
      }
    >
      <div className="form">
        <PageErrorAlert error={error} />
        <div className="body-chart">
          <BodyRangeSwitch value={range} onChange={setRange} />
          <div className="body-range body-metric" role="radiogroup" aria-label={t('body.exerciseMetricTitle')}>
            {(['best', 'volume'] as ProgressMetric[]).map((key) => (
              <button
                key={key}
                type="button"
                role="radio"
                aria-checked={metric === key}
                className={metric === key ? 'is-selected' : ''}
                onClick={() => setMetric(key)}
              >
                {t(`body.${metrics}.${key}`)}
              </button>
            ))}
          </div>
          {points.length >= 2 ? (
            <ProgressChart points={points} height={140} showDots className="body-chart-svg" />
          ) : (
            <p className="my-empty">{t('body.exerciseFew')}</p>
          )}
          <p className="my-level-hint">{t(`body.${metrics}Hint.${metric}`)}</p>
        </div>

        {first && last && first !== last ? (
          <div className="body-stats">
            <div>
              <span className="body-label">
                {t('body.exerciseWas', { date: formatDay(first.day, dateLocale, { day: 'numeric', month: 'short' }) })}
              </span>
              <strong>{formatBest(first)}</strong>
            </div>
            <div>
              <span className="body-label">
                {t('body.exerciseNow', { date: formatDay(last.day, dateLocale, { day: 'numeric', month: 'short' }) })}
              </span>
              <strong>{formatBest(last)}</strong>
            </div>
          </div>
        ) : null}

        {sessions.length > 0 ? (
          <div className="body-history">
            <span className="form-label">{t('body.history')}</span>
            <ul>
              {[...inRange].reverse().map((session) => (
                <li key={session.day}>
                  <button type="button" onClick={() => onRecord(exercise.id, session.day)}>
                    <span>{formatDay(session.day, dateLocale, { weekday: 'short', day: 'numeric', month: 'short' })}</span>
                    <span>{describe(session.sets, exercise.with_weight)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <details className="body-exercise-edit">
          <summary>{t('body.exerciseEdit')}</summary>
          <div className="my-amount-row">
            <input
              className="form-input"
              value={name}
              maxLength={80}
              aria-label={t('body.exerciseName')}
              onChange={(event) => setName(event.target.value)}
            />
            <button
              type="button"
              className="button button-secondary"
              disabled={!trimmed || trimmed === exercise.name || isSaving}
              onClick={() => void run(() => updateExercise(exercise.id, { name: trimmed }), false)}
            >
              {t('common.save')}
            </button>
          </div>
          <label className="body-check">
            <input
              type="checkbox"
              checked={!exercise.with_weight}
              disabled={isSaving}
              onChange={(event) => void run(() => updateExercise(exercise.id, { with_weight: !event.target.checked }), false)}
            />
            <span>{t('body.exerciseNoWeight')}</span>
          </label>
          <button
            type="button"
            className="button button-secondary"
            disabled={isSaving}
            onClick={() => {
              if (!confirmDelete) setConfirmDelete(true)
              else void run(() => deleteExercise(exercise.id), true)
            }}
          >
            {confirmDelete ? t('body.exerciseDeleteConfirm') : t('body.exerciseDelete')}
          </button>
        </details>
      </div>
    </EditorDrawer>
  )
}
