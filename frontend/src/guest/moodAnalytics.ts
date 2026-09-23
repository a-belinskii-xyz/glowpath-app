import type { ApiLocale } from '../lib/locale'
import { defaultMoodScoreStyle, getMoodScoreStyle } from '../lib/moodScale'
import { dayKey } from '../lib/datetime'
import type { GoalPublic } from '../types/goal'
import type {
  CalendarDayPublic,
  CalendarDayScore,
  MoodEntryPublic,
  MoodEntryStatsResponse,
  MoodEntryStreakResponse,
} from '../types/mood'
import type { MoodScoreStylePublic } from '../types/moodPreferences'
import type { TagGroupPublic } from '../types/tag'

const MIN_MOOD_SCORE = 1
const MAX_MOOD_SCORE = 5

const INSUFFICIENT_DATA_MESSAGE: Record<ApiLocale, string> = {
  en: 'Not enough entries yet to compare with last month.',
  ru: 'Пока недостаточно записей, чтобы сравнить с прошлым месяцем.',
}

const SAME_SCORE_DECAY = 0.55

function entriesInRange(
  entries: MoodEntryPublic[],
  from: string,
  to: string,
): MoodEntryPublic[] {
  return entries.filter((entry) => entry.recorded_at >= from && entry.recorded_at <= to)
}

function groupByDay(entries: MoodEntryPublic[], timezone: string): Map<string, MoodEntryPublic[]> {
  const map = new Map<string, MoodEntryPublic[]>()
  for (const entry of entries) {
    const key = dayKey(entry.recorded_at, timezone)
    const bucket = map.get(key) ?? []
    bucket.push(entry)
    map.set(key, bucket)
  }
  for (const [key, bucket] of map) {
    bucket.sort((a, b) => a.recorded_at.localeCompare(b.recorded_at))
    map.set(key, bucket)
  }
  return map
}

function dayIndex(scores: number[]): number {
  const counters = new Map<number, number>()
  let weightedSum = 0
  let weightTotal = 0
  for (const score of scores) {
    const k = counters.get(score) ?? 0
    const weight = SAME_SCORE_DECAY ** k
    counters.set(score, k + 1)
    weightedSum += score * weight
    weightTotal += weight
  }
  return weightTotal > 0 ? weightedSum / weightTotal : 3
}

export function computeGuestCalendar(
  entries: MoodEntryPublic[],
  params: { recorded_from: string; recorded_to: string },
  timezone: string,
): CalendarDayPublic[] {
  const filtered = entriesInRange(entries, params.recorded_from, params.recorded_to)
  const byDay = groupByDay(filtered, timezone)
  const days: CalendarDayPublic[] = []
  for (const [date, dayEntries] of byDay) {
    const scores: CalendarDayScore[] = dayEntries.slice(0, 3).map((entry) => ({
      score: entry.score,
      score_emoji: entry.score_emoji,
      score_color: entry.score_color,
    }))
    days.push({ date, entry_count: dayEntries.length, scores })
  }
  days.sort((a, b) => a.date.localeCompare(b.date))
  return days
}

export function computeGuestStreak(entries: MoodEntryPublic[], timezone: string): MoodEntryStreakResponse {
  const daySet = new Set(entries.map((entry) => dayKey(entry.recorded_at, timezone)))
  const today = dayKey(new Date().toISOString(), timezone)
  let current = 0
  let cursor = today
  while (daySet.has(cursor)) {
    current += 1
    const date = new Date(`${cursor}T12:00:00`)
    date.setDate(date.getDate() - 1)
    cursor = dayKey(date.toISOString(), timezone)
  }
  return { current_days: current, logged_today: daySet.has(today) }
}

export function computeGuestStats(
  entries: MoodEntryPublic[],
  params: { recorded_from: string; recorded_to: string },
  timezone: string,
  locale: ApiLocale,
  tagGroups: TagGroupPublic[],
  _goals: GoalPublic[],
  moodPreferences?: Record<string, MoodScoreStylePublic> | null,
): MoodEntryStatsResponse {
  const filtered = entriesInRange(entries, params.recorded_from, params.recorded_to)
  const byDay = groupByDay(filtered, timezone)
  const dayIndices = [...byDay.values()].map((dayEntries) =>
    dayIndex(dayEntries.map((entry) => entry.score)),
  )
  const monthIndex =
    dayIndices.length > 0 ? dayIndices.reduce((sum, value) => sum + value, 0) / dayIndices.length : null

  const scoreCounts = new Map<number, number>()
  for (const entry of filtered) {
    scoreCounts.set(entry.score, (scoreCounts.get(entry.score) ?? 0) + 1)
  }
  const scores = []
  for (let score = MIN_MOOD_SCORE; score <= MAX_MOOD_SCORE; score += 1) {
    const count = scoreCounts.get(score) ?? 0
    const style = getMoodScoreStyle(score, moodPreferences, locale)
    scores.push({
      score,
      score_label: style.label ?? defaultMoodScoreStyle(score, locale).label ?? String(score),
      score_emoji: style.icon,
      count,
    })
  }

  const tagCounts = new Map<string, number>()
  for (const entry of filtered) {
    for (const tag of entry.tags) {
      tagCounts.set(tag.id, (tagCounts.get(tag.id) ?? 0) + 1)
    }
  }
  const tagsById = new Map(
    tagGroups.flatMap((group) => group.tags.map((tag) => [tag.id, tag] as const)),
  )
  const tags = [...tagCounts.entries()]
    .map(([id, count]) => {
      const tag = tagsById.get(id)
      if (!tag) return null
      return {
        id,
        kind: 'tag' as const,
        label: tag.label,
        color: tag.color,
        icon_type: tag.icon_type,
        icon: tag.icon,
        count,
      }
    })
    .filter(Boolean)
    .sort((a, b) => (b?.count ?? 0) - (a?.count ?? 0))
    .slice(0, 16)

  return {
    total_entries: filtered.length,
    scores,
    month_index: monthIndex,
    active_days: byDay.size,
    comparison: {
      verdict: 'insufficient_data',
      message: INSUFFICIENT_DATA_MESSAGE[locale] ?? INSUFFICIENT_DATA_MESSAGE.en,
      current_index: monthIndex,
      previous_index: null,
      delta: null,
      current_active_days: byDay.size,
      previous_active_days: 0,
    },
    favorite_count: filtered.filter((entry) => entry.is_favorite).length,
    tags: tags as MoodEntryStatsResponse['tags'],
    goals: [],
    weeks: [],
  }
}

export function guestInsightsUnavailable() {
  return {
    window_from: '',
    window_to: '',
    active_days: 0,
    entry_count: 0,
    baseline_index: null,
    items: [],
  }
}
