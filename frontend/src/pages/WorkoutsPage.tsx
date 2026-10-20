import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { listExercises, listWorkoutSets } from '../api/body'
import { type BodyRange, BodyRangeSwitch } from '../components/BodyRange'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { ExerciseCard, ExerciseDrawer, WorkoutDrawer, type WorkoutTarget } from '../components/WorkoutSection'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { shiftDateKey, todayKey } from '../lib/datetime'
import { formatApiError } from '../lib/errors'
import type { Exercise, WorkoutSet } from '../types/body'

const HISTORY_DAYS = 365

/** Exercises done lately first; ones without sets yet go last, by name. */
function byRecent(a: Exercise, b: Exercise): number {
  if (a.last_day !== b.last_day) {
    if (a.last_day === null) return 1
    if (b.last_day === null) return -1
    return a.last_day < b.last_day ? 1 : -1
  }
  return a.name.localeCompare(b.name)
}

/** Workouts screen (GP-62): every exercise as a card with its own line and numbers. */
export function WorkoutsPage() {
  const { user } = useAuth()
  const { t } = useLocale()
  const today = todayKey(user?.timezone ?? 'UTC')
  const [exercises, setExercises] = useState<Exercise[]>([])
  const [sets, setSets] = useState<WorkoutSet[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [range, setRange] = useState<BodyRange>('month')
  const [workoutTarget, setWorkoutTarget] = useState<(WorkoutTarget & { fromExercise: boolean }) | null>(null)
  const [exerciseId, setExerciseId] = useState<string | null>(null)

  const load = useCallback(async () => {
    const [nextExercises, nextSets] = await Promise.all([
      listExercises(),
      listWorkoutSets(shiftDateKey(today, -HISTORY_DAYS), today),
    ])
    setExercises(nextExercises)
    setSets(nextSets)
  }, [today])

  useEffect(() => {
    void load()
      .catch((err) => setError(formatApiError(err, t, 'errors.requestFailed')))
      .finally(() => setIsLoading(false))
  }, [load, t])

  const openExercise = exercises.find((exercise) => exercise.id === exerciseId) ?? null
  const sorted = [...exercises].sort(byRecent)

  return (
    <section className="page workouts-page">
      <header className="page-header">
        <h1>{t('body.workoutsTitle')}</h1>
        <button
          type="button"
          className="button"
          onClick={() => setWorkoutTarget({ day: today, exerciseId: null, fromExercise: false })}
        >
          {t('body.workoutRecord')}
        </button>
      </header>

      <PageErrorAlert error={error} />

      {!isLoading && exercises.length === 0 ? (
        <p className="my-empty">{t('body.workoutsEmpty')}</p>
      ) : null}

      {exercises.length > 0 ? (
        <>
          <div className="workouts-toolbar">
            <BodyRangeSwitch value={range} onChange={setRange} />
            <p className="my-level-hint">{t('body.workoutsHint')}</p>
          </div>
          {sorted.map((exercise) => (
            <ExerciseCard
              key={exercise.id}
              exercise={exercise}
              sets={sets}
              today={today}
              range={range}
              onOpen={() => setExerciseId(exercise.id)}
              onRecord={() => setWorkoutTarget({ day: today, exerciseId: exercise.id, fromExercise: false })}
            />
          ))}
        </>
      ) : null}

      <p className="my-gentle muted">{t('body.workoutGentle')}</p>

      <p className="muted page-back-link">
        <Link to="/me">{t('body.workoutsBack')}</Link>
      </p>

      <ExerciseDrawer
        exercise={workoutTarget ? null : openExercise}
        sets={sets}
        today={today}
        onClose={() => setExerciseId(null)}
        onRecord={(id, day) => setWorkoutTarget({ day, exerciseId: id, fromExercise: true })}
        onChanged={load}
      />
      <WorkoutDrawer
        target={workoutTarget}
        today={today}
        exercises={exercises}
        sets={sets}
        onClose={() => {
          // Back to the exercise it was opened from, if any.
          if (!workoutTarget?.fromExercise) setExerciseId(null)
          setWorkoutTarget(null)
        }}
        onChanged={load}
      />
    </section>
  )
}
