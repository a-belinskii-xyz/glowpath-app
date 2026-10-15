import type { MoodScoreIconType } from './moodPreferences'

export type GoalTrackingKind = 'binary' | 'quantity'

/** How a goal was done on a day: "a little" or fully. */
export type GoalCheckinLevel = 'partial' | 'full'

/** "started": a quantity day with some progress below the amount that counts. */
export type GoalDayLevel = GoalCheckinLevel | 'started'

export type GoalDayMark = {
  date: string
  level: GoalDayLevel
  /** Quantity goals: how much was done that day. */
  amount: number | null
}

/** Binary goals send a level; quantity goals send the amount done that day. */
export type GoalCheckinWrite = { level: GoalCheckinLevel } | { amount: number }

export type GoalPublic = {
  id: string
  slug: string
  label: string
  labels: Record<string, string>
  times_per_week: number
  tracking_kind: GoalTrackingKind
  target_amount: number | null
  unit: string | null
  /** What counts as "a little" for this goal, e.g. "at least a snack". */
  partial_label: string | null
  /** Quantity goals: a day counts from this amount; null = only the full target. */
  min_amount: number | null
  starts_on: string
  ends_on: string | null
  sort_order: number
  show_on_entry: boolean
  show_in_stats: boolean
  color: string
  icon_type: MoodScoreIconType
  icon: string
  completed_this_week: number
  day_amount: number
  /** Completed days of the week asked for (`progress_on`), from entries or check-ins. */
  week_marks: GoalDayMark[]
}

export type GoalListResponse = {
  items: GoalPublic[]
  entry_visible_goal_limit: number
  stats_visible_goal_limit: number
}

export type GoalWrite = {
  labels: Record<string, string>
  times_per_week: number
  tracking_kind?: GoalTrackingKind
  target_amount?: number | null
  unit?: string | null
  partial_label?: string | null
  min_amount?: number | null
  starts_on: string
  ends_on?: string | null
  slug?: string
  sort_order?: number
  show_on_entry?: boolean
  show_in_stats?: boolean
  color?: string
  icon_type?: MoodScoreIconType
  icon?: string
}

export type GoalPatch = {
  slug?: string
  labels?: Record<string, string>
  times_per_week?: number
  tracking_kind?: GoalTrackingKind
  target_amount?: number | null
  unit?: string | null
  partial_label?: string | null
  min_amount?: number | null
  starts_on?: string
  ends_on?: string | null
  sort_order?: number
  show_on_entry?: boolean
  show_in_stats?: boolean
  color?: string
  icon_type?: MoodScoreIconType
  icon?: string
}

export type GoalReorderRequest = {
  ordered_ids: string[]
}

export type CalendarDayGoal = {
  goal_id: string
}

export type GoalCalendarDayPublic = {
  date: string
  entry_count: number
  goals: CalendarDayGoal[]
}

export type GoalCalendarResponse = {
  days: GoalCalendarDayPublic[]
}

export type GoalPeriodStatPublic = {
  id: string
  slug: string
  label: string
  labels: Record<string, string>
  times_per_week: number
  tracking_kind: GoalTrackingKind
  target_amount: number | null
  unit: string | null
  starts_on: string
  ends_on: string | null
  sort_order: number
  show_on_entry: boolean
  show_in_stats: boolean
  color: string
  icon_type: MoodScoreIconType
  icon: string
  completed_in_period: number
  period_target: number
  amount_in_period: number
}

export type GoalStatsResponse = {
  period_start: string
  period_end: string
  period_days: number
  items: GoalPeriodStatPublic[]
}

export type GoalIconMeta = {
  id: string
  goal_id: string
  mime_type: string
  size_bytes: number
  original_name: string
  has_source: boolean
}

export type GoalIconListResponse = {
  items: GoalIconMeta[]
  max_per_goal: number
}

export type GoalIconPublic = {
  id: string
  goal_id: string
  mime_type: string
  size_bytes: number
  original_name: string
  has_source: boolean
  goal: GoalPublic
}

export type GoalStyle = {
  color: string
  icon_type: MoodScoreIconType
  icon: string
}

export const DEFAULT_GOAL_STYLE: GoalStyle = {
  color: '#60a5fa',
  icon_type: 'emoji',
  icon: '🎯',
}
