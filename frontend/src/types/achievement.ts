export type AchievementRewardPublic = {
  kind: string
  amount?: number | null
  pack_id?: string | null
  pack_slug?: string | null
  pack_name?: string | null
  cover_icon_id?: string | null
  catalog_icon_id?: string | null
  icon_slug?: string | null
  icon_name?: string | null
}

export type AchievementPublic = {
  id: string
  visibility: 'visible' | 'secret' | string
  category: string
  unlocked: boolean
  is_new?: boolean
  progress_current: number
  progress_target: number
  sort_order: number
  slug?: string | null
  name?: string | null
  description?: string | null
  icon_type?: string | null
  icon?: string | null
  criteria?: Record<string, unknown> | null
  rewards?: AchievementRewardPublic[]
  unlocked_at?: string | null
  unlocked_by_entry_id?: string | null
  unlock_percent?: number | null
}

export type AchievementListResponse = {
  items: AchievementPublic[]
}

export type AchievementSummaryResponse = {
  unlocked: number
  total_visible: number
  secret_unlocked: number
  secret_total: number
}
