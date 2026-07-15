export type MoodEntryTag = {
  id: string
  slug: string
  label: string
  group_id: string
}

export type MoodEntryGoal = {
  id: string
  slug: string
  label: string
}

export type AttachmentKind = 'photo' | 'audio'

export type AttachmentPublic = {
  id: string
  kind: AttachmentKind
  mime_type: string
  size_bytes: number
  original_name: string
  position: number | null
}

export type MoodEntryPublic = {
  id: string
  recorded_at: string
  score: number
  score_label: string
  score_emoji: string
  note: string | null
  is_favorite: boolean
  tags: MoodEntryTag[]
  goals: MoodEntryGoal[]
  attachments: AttachmentPublic[]
  created_at: string
  updated_at: string
}

export type MoodEntryListResponse = {
  items: MoodEntryPublic[]
  limit: number
  offset: number
}

export type CalendarDayScore = {
  score: number
  score_emoji: string
}

export type CalendarDayPublic = {
  date: string
  entry_count: number
  scores: CalendarDayScore[]
}

export type MoodEntryCalendarResponse = {
  days: CalendarDayPublic[]
}

export type MoodScoreStatPublic = {
  score: number
  score_label: string
  score_emoji: string
  count: number
}

export type MoodComparisonVerdict =
  | 'much_better'
  | 'better'
  | 'similar'
  | 'worse'
  | 'much_worse'
  | 'insufficient_data'

export type MoodMonthComparisonPublic = {
  verdict: MoodComparisonVerdict
  message: string
  current_index: number | null
  previous_index: number | null
  delta: number | null
  current_active_days: number
  previous_active_days: number
}

export type MoodEntryStatsResponse = {
  total_entries: number
  scores: MoodScoreStatPublic[]
  month_index: number | null
  active_days: number
  comparison: MoodMonthComparisonPublic
}

export type MoodEntryCreate = {
  score: number
  recorded_at: string
  note?: string | null
  tag_ids: string[]
  goal_ids: string[]
}

export type MoodEntryPatch = {
  score?: number
  recorded_at?: string
  note?: string | null
  tag_ids?: string[]
  goal_ids?: string[]
  is_favorite?: boolean
}

export type ListMoodEntriesParams = {
  limit?: number
  offset?: number
  recorded_from?: string
  recorded_to?: string
  is_favorite?: boolean
}
