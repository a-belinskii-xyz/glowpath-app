import type { MoodScoreIconType } from './moodPreferences'

export type GoalPublic = {
  id: string
  slug: string
  label: string
  labels: Record<string, string>
  times_per_week: number
  starts_on: string
  sort_order: number
  show_on_entry: boolean
  color: string
  icon_type: MoodScoreIconType
  icon: string
  completed_this_week: number
}

export type GoalListResponse = {
  items: GoalPublic[]
  entry_visible_goal_limit: number
}

export type GoalWrite = {
  labels: Record<string, string>
  times_per_week: number
  starts_on: string
  slug?: string
  sort_order?: number
  show_on_entry?: boolean
  color?: string
  icon_type?: MoodScoreIconType
  icon?: string
}

export type GoalPatch = {
  slug?: string
  labels?: Record<string, string>
  times_per_week?: number
  starts_on?: string
  sort_order?: number
  show_on_entry?: boolean
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

export type GoalIconMeta = {
  id: string
  goal_id: string
  mime_type: string
  size_bytes: number
  original_name: string
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
