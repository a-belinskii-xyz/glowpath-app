import type { CalendarDayPublic, MoodEntryStatsResponse } from '../types/mood'

export const MIN_MOOD = 1
export const MAX_MOOD = 5

/** One logged day, reduced to a single mood value for the month picture. */
export type RecapDay = {
  date: string
  /** Day of month, 1-based. */
  day: number
  /** Monday = 0 … Sunday = 6. */
  weekday: number
  entryCount: number
  /** Mean of the day's scores (the calendar sends up to 3 latest), 1–5. */
  mood: number
  /** Score whose colour/icon represents the day (rounded mean). */
  score: number
}

export type RecapMoodShare = {
  score: number
  count: number
  share: number
}

export type RecapWeekdayMood = {
  weekday: number
  mood: number | null
  days: number
}

export type MonthRecapData = {
  daysInMonth: number
  days: RecapDay[]
  /** Share of each score across all entries, highest score first. */
  moodMix: RecapMoodShare[]
  /** Most frequent score (ties go to the brighter mood). */
  dominantScore: number | null
  /** Month mood on the 1–5 scale; backend index when present. */
  averageMood: number | null
  bestDay: RecapDay | null
  longestStreak: number
  weekdays: RecapWeekdayMood[]
  bestWeekday: RecapWeekdayMood | null
}

export function clampMood(value: number): number {
  return Math.min(MAX_MOOD, Math.max(MIN_MOOD, value))
}

function mean(values: number[]): number | null {
  if (values.length === 0) return null
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

function parseIsoDate(value: string): { year: number; month: number; day: number } | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return null
  return { year: Number(match[1]), month: Number(match[2]) - 1, day: Number(match[3]) }
}

function toRecapDays(calendar: CalendarDayPublic[], year: number, month: number): RecapDay[] {
  const days: RecapDay[] = []
  for (const item of calendar) {
    const parsed = parseIsoDate(item.date)
    if (!parsed || parsed.year !== year || parsed.month !== month) continue
    if (item.entry_count <= 0 || item.scores.length === 0) continue
    const mood = mean(item.scores.map((score) => score.score)) ?? MIN_MOOD
    const weekday = (new Date(Date.UTC(year, month, parsed.day)).getUTCDay() + 6) % 7
    days.push({
      date: item.date,
      day: parsed.day,
      weekday,
      entryCount: item.entry_count,
      mood,
      score: Math.round(clampMood(mood)),
    })
  }
  return days.sort((left, right) => left.day - right.day)
}

function longestRun(days: RecapDay[]): number {
  let best = 0
  let run = 0
  let previous = -1
  for (const day of days) {
    run = day.day === previous + 1 ? run + 1 : 1
    best = Math.max(best, run)
    previous = day.day
  }
  return best
}

export function buildMonthRecap(
  stats: MoodEntryStatsResponse,
  calendar: CalendarDayPublic[],
  year: number,
  month: number,
): MonthRecapData {
  const daysInMonth = new Date(Date.UTC(year, month + 1, 0)).getUTCDate()
  const days = toRecapDays(calendar, year, month)

  const counted = stats.scores.filter((item) => item.count > 0)
  const total = counted.reduce((sum, item) => sum + item.count, 0)
  const moodMix = [...counted]
    .sort((left, right) => right.score - left.score)
    .map((item) => ({
      score: item.score,
      count: item.count,
      share: total > 0 ? item.count / total : 0,
    }))
  const dominant = [...counted].sort(
    (left, right) => right.count - left.count || right.score - left.score,
  )[0]

  const averageMood =
    stats.month_index ?? stats.comparison.current_index ?? mean(days.map((day) => day.mood))

  const bestDay = days.reduce<RecapDay | null>(
    (best, day) =>
      best === null ||
      day.mood > best.mood ||
      (day.mood === best.mood && day.entryCount > best.entryCount)
        ? day
        : best,
    null,
  )

  const weekdays: RecapWeekdayMood[] = Array.from({ length: 7 }, (_, weekday) => {
    const moods = days.filter((day) => day.weekday === weekday).map((day) => day.mood)
    return { weekday, mood: mean(moods), days: moods.length }
  })
  const ranked = weekdays
    .filter((item) => item.mood !== null)
    .sort((left, right) => (right.mood ?? 0) - (left.mood ?? 0) || right.days - left.days)
  // A "best weekday" only means something when there is something to compare it with.
  const bestWeekday =
    ranked.length >= 3 && (ranked[0].mood ?? 0) > (ranked[ranked.length - 1].mood ?? 0)
      ? ranked[0]
      : null

  return {
    daysInMonth,
    days,
    moodMix,
    dominantScore: dominant?.score ?? null,
    averageMood: averageMood === null ? null : clampMood(averageMood),
    bestDay,
    longestStreak: longestRun(days),
    weekdays,
    bestWeekday,
  }
}

/** Short weekday names starting on Monday, in the UI locale. */
export function weekdayNames(intlLocale: string, style: 'narrow' | 'short' | 'long'): string[] {
  const format = new Intl.DateTimeFormat(intlLocale, { weekday: style, timeZone: 'UTC' })
  // 2024-01-01 was a Monday.
  return Array.from({ length: 7 }, (_, index) =>
    format.format(new Date(Date.UTC(2024, 0, 1 + index))),
  )
}

export function formatRecapDate(date: string, intlLocale: string): string {
  const parsed = parseIsoDate(date)
  if (!parsed) return date
  return new Intl.DateTimeFormat(intlLocale, {
    day: 'numeric',
    month: 'long',
    timeZone: 'UTC',
  }).format(new Date(Date.UTC(parsed.year, parsed.month, parsed.day)))
}
