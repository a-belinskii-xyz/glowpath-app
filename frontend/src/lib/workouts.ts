/** Workout sets grouped into sessions, and the numbers the progress chart draws (GP-58). */

import type { Exercise, WorkoutSet } from '../types/body'

export type Session = { day: string; sets: WorkoutSet[] }
export type ProgressMetric = 'best' | 'volume'

/** One exercise's sets grouped by day, oldest first, each day in set order. */
export function sessionsOf(sets: WorkoutSet[], exerciseId: string): Session[] {
  const byDay = new Map<string, WorkoutSet[]>()
  for (const set of sets) {
    if (set.exercise_id !== exerciseId) continue
    byDay.set(set.day, [...(byDay.get(set.day) ?? []), set])
  }
  return [...byDay.entries()]
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([day, daySets]) => ({ day, sets: [...daySets].sort((a, b) => a.position - b.position) }))
}

/** The heaviest set (most reps among equals); for bodyweight, the set with the most reps. */
export function bestSet(sets: WorkoutSet[]): WorkoutSet | null {
  let best: WorkoutSet | null = null
  for (const set of sets) {
    const weight = set.weight_kg ?? 0
    const bestWeight = best?.weight_kg ?? 0
    if (best === null || weight > bestWeight || (weight === bestWeight && set.reps > best.reps)) best = set
  }
  return best
}

/** The number one session adds to the chart. */
export function sessionValue(session: Session, exercise: Exercise, metric: ProgressMetric): number {
  if (metric === 'volume') {
    return session.sets.reduce((sum, set) => sum + (exercise.with_weight ? (set.weight_kg ?? 0) : 1) * set.reps, 0)
  }
  const best = bestSet(session.sets)
  if (!best) return 0
  return exercise.with_weight ? (best.weight_kg ?? 0) : best.reps
}

type Words = {
  kg: string
  /** Formats a list of reps for bodyweight work, e.g. "7, 6, 5 reps". */
  reps: (list: string) => string
}

/** "60 kg × 8, 8, 6" with runs of the same weight joined; "7, 6, 5 reps" without weight. */
export function formatSets(sets: WorkoutSet[], withWeight: boolean, numbers: Intl.NumberFormat, words: Words): string {
  if (sets.length === 0) return ''
  if (!withWeight) return words.reps(sets.map((set) => set.reps).join(', '))
  const runs: { weight: number | null; reps: number[] }[] = []
  for (const set of sets) {
    const last = runs[runs.length - 1]
    if (last && last.weight === set.weight_kg) last.reps.push(set.reps)
    else runs.push({ weight: set.weight_kg, reps: [set.reps] })
  }
  return runs
    .map((run) =>
      run.weight === null ? run.reps.join(', ') : `${numbers.format(run.weight)} ${words.kg} × ${run.reps.join(', ')}`,
    )
    .join(' · ')
}

/** Parses "62,5" or "62.5" into kilograms, to the nearest 0.01; empty or invalid gives null. */
export function parseSetWeight(raw: string): number | null {
  const value = Number.parseFloat(raw.replace(',', '.'))
  if (!Number.isFinite(value) || value < 0 || value > 999) return null
  return Math.round(value * 100) / 100
}

export function parseReps(raw: string): number | null {
  const value = Number.parseInt(raw, 10)
  if (!Number.isFinite(value) || value < 1 || value > 1000) return null
  return value
}
