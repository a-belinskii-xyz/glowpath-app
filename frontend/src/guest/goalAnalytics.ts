import { dayKey } from '../lib/datetime'
import type {
  GoalCalendarDayPublic,
  GoalPeriodStatPublic,
  GoalPublic,
  GoalStatsResponse,
} from '../types/goal'
import type { MoodEntryPublic } from '../types/mood'

function periodDays(periodStart: string, periodEndExclusive: string): number {
  const [sy, sm, sd] = periodStart.split('-').map(Number)
  const [ey, em, ed] = periodEndExclusive.split('-').map(Number)
  const startMs = Date.UTC(sy, sm - 1, sd)
  const endMs = Date.UTC(ey, em - 1, ed)
  return Math.max(0, Math.round((endMs - startMs) / 86_400_000))
}

function periodTarget(timesPerWeek: number, days: number): number {
  if (days <= 0) {
    return timesPerWeek
  }
  return Math.max(1, Math.round((timesPerWeek * days) / 7))
}

function localPeriodFromBounds(
  recordedFrom: string,
  recordedTo: string,
  timezone: string,
): { periodStart: string; periodEnd: string; periodDayCount: number } {
  const periodStart = dayKey(recordedFrom, timezone)
  const periodEnd = dayKey(recordedTo, timezone)
  return { periodStart, periodEnd, periodDayCount: periodDays(periodStart, periodEnd) }
}

type GoalPeriodProgress = {
  completedDays: number
  amountInPeriod: number
  dayAmount: number
}

function computeGoalPeriodProgress(
  entries: MoodEntryPublic[],
  goals: GoalPublic[],
  periodStart: string,
  periodEnd: string,
  timezone: string,
  progressDay?: string,
): Map<string, GoalPeriodProgress> {
  const goalsById = new Map(goals.map((goal) => [goal.id, goal]))
  const daily = new Map<string, Map<string, number>>()

  for (const entry of entries) {
    const localDay = dayKey(entry.recorded_at, timezone)
    if (localDay < periodStart || localDay >= periodEnd) {
      continue
    }
    for (const goalRef of entry.goals) {
      const goal = goalsById.get(goalRef.id)
      if (!goal) {
        continue
      }
      const byDay = daily.get(goal.id) ?? new Map<string, number>()
      if (goal.tracking_kind === 'quantity') {
        byDay.set(localDay, (byDay.get(localDay) ?? 0) + (goalRef.amount ?? 0))
      } else {
        byDay.set(localDay, 1)
      }
      daily.set(goal.id, byDay)
    }
  }

  const result = new Map<string, GoalPeriodProgress>()
  for (const goal of goals) {
    const amounts = daily.get(goal.id) ?? new Map<string, number>()
    let completedDays = 0
    let amountInPeriod = 0
    if (goal.tracking_kind === 'quantity') {
      const threshold = goal.target_amount ?? 0
      for (const value of amounts.values()) {
        amountInPeriod += value
        if (value >= threshold) {
          completedDays += 1
        }
      }
    } else {
      completedDays = amounts.size
      amountInPeriod = completedDays
    }
    result.set(goal.id, {
      completedDays,
      amountInPeriod,
      dayAmount: progressDay ? (amounts.get(progressDay) ?? 0) : 0,
    })
  }
  return result
}

export function enrichGuestGoalsWithProgress(
  goals: GoalPublic[],
  entries: MoodEntryPublic[],
  progressOn: string,
  timezone: string,
): GoalPublic[] {
  const weekBounds = (() => {
    const [year, month, day] = progressOn.split('-').map(Number)
    const utcDay = new Date(Date.UTC(year, month - 1, day))
    const mondayOffset = (utcDay.getUTCDay() + 6) % 7
    const weekStartUtc = new Date(Date.UTC(year, month - 1, day - mondayOffset))
    const weekEndUtc = new Date(Date.UTC(year, month - 1, day - mondayOffset + 7))
    const pad = (value: number) => String(value).padStart(2, '0')
    return {
      periodStart: `${weekStartUtc.getUTCFullYear()}-${pad(weekStartUtc.getUTCMonth() + 1)}-${pad(weekStartUtc.getUTCDate())}`,
      periodEnd: `${weekEndUtc.getUTCFullYear()}-${pad(weekEndUtc.getUTCMonth() + 1)}-${pad(weekEndUtc.getUTCDate())}`,
    }
  })()

  const progress = computeGoalPeriodProgress(
    entries,
    goals,
    weekBounds.periodStart,
    weekBounds.periodEnd,
    timezone,
    progressOn,
  )

  return goals.map((goal) => {
    const stats = progress.get(goal.id)
    return {
      ...goal,
      completed_this_week: stats?.completedDays ?? 0,
      day_amount: stats?.dayAmount ?? 0,
    }
  })
}

export function computeGuestGoalCalendar(
  entries: MoodEntryPublic[],
  goals: GoalPublic[],
  params: { recorded_from: string; recorded_to: string },
  timezone: string,
  cap: number,
): GoalCalendarDayPublic[] {
  const statsGoalIds = new Set(goals.filter((goal) => goal.show_in_stats).map((goal) => goal.id))
  const goalsById = new Map(goals.map((goal) => [goal.id, goal]))
  const byDay = new Map<string, Array<{ goalId: string; recordedAt: string }>>()

  for (const entry of entries) {
    if (entry.recorded_at < params.recorded_from || entry.recorded_at >= params.recorded_to) {
      continue
    }
    const date = dayKey(entry.recorded_at, timezone)
    for (const goal of entry.goals) {
      if (!statsGoalIds.has(goal.id)) {
        continue
      }
      const bucket = byDay.get(date) ?? []
      bucket.push({ goalId: goal.id, recordedAt: entry.recorded_at })
      byDay.set(date, bucket)
    }
  }

  const days: GoalCalendarDayPublic[] = []
  for (const [date, marks] of byDay) {
    marks.sort((left, right) => right.recordedAt.localeCompare(left.recordedAt))
    const unique: string[] = []
    const seen = new Set<string>()
    for (const mark of marks) {
      if (seen.has(mark.goalId)) {
        continue
      }
      seen.add(mark.goalId)
      unique.push(mark.goalId)
    }
    unique.sort(
      (left, right) =>
        (goalsById.get(left)?.sort_order ?? 0) - (goalsById.get(right)?.sort_order ?? 0),
    )
    days.push({
      date,
      entry_count: unique.length,
      goals: unique.slice(0, cap).map((goalId) => ({ goal_id: goalId })),
    })
  }
  days.sort((left, right) => left.date.localeCompare(right.date))
  return days
}

export function computeGuestGoalStats(
  entries: MoodEntryPublic[],
  goals: GoalPublic[],
  params: { recorded_from: string; recorded_to: string },
  timezone: string,
): GoalStatsResponse {
  const { periodStart, periodEnd, periodDayCount } = localPeriodFromBounds(
    params.recorded_from,
    params.recorded_to,
    timezone,
  )
  const progress = computeGoalPeriodProgress(entries, goals, periodStart, periodEnd, timezone)
  const overlapping = goals.filter(
    (goal) =>
      goal.show_in_stats &&
      goal.starts_on < periodEnd &&
      (goal.ends_on == null || goal.ends_on >= periodStart),
  )

  const items: GoalPeriodStatPublic[] = overlapping.map((goal) => {
    const stats = progress.get(goal.id)
    return {
      ...goal,
      completed_in_period: stats?.completedDays ?? 0,
      period_target: periodTarget(goal.times_per_week, periodDayCount),
      amount_in_period: stats?.amountInPeriod ?? 0,
    }
  })

  return {
    period_start: periodStart,
    period_end: periodEnd,
    period_days: periodDayCount,
    items,
  }
}
