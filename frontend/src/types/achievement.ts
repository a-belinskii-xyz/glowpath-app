export type AchievementRewardPublic = {
  kind: string
  amount?: number | null
  pack_id?: string | null
  pack_slug?: string | null
  pack_name?: string | null
  cover_icon_id?: string | null
  preview_icon_ids?: string[]
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

// --- Staff editor ---

export type AchievementCategory = 'getting_started' | 'streaks' | 'collection' | 'secrets'
export type AchievementVisibility = 'visible' | 'secret'
export type AchievementStatus = 'draft' | 'published' | 'archived'
export type AchievementRewardKind = 'tokens' | 'icon_pack' | 'catalog_icon'

export type AchievementCriteria = { type: string } & Record<string, string | number>

export type AchievementText = { en: string; ru?: string | null }

export type AchievementRewardInput = {
  kind: AchievementRewardKind
  amount?: number | null
  pack_id?: string | null
  catalog_icon_id?: string | null
}

export type StaffAchievementReward = AchievementRewardInput & {
  icon_pack_id?: string | null
  label?: string | null
}

export type StaffAchievementPublic = {
  id: string
  slug: string
  category: AchievementCategory
  visibility: AchievementVisibility
  status: AchievementStatus
  labels: Record<string, string>
  descriptions: Record<string, string>
  name: string
  icon_type: 'emoji' | 'image'
  icon: string
  criteria: AchievementCriteria
  sort_order: number
  rewards: StaffAchievementReward[]
  unlocked_count: number
  updated_at: string
}

export type StaffAchievementCreate = {
  labels: AchievementText
  descriptions: AchievementText
  category: AchievementCategory
  visibility: AchievementVisibility
  criteria: AchievementCriteria
  rewards: AchievementRewardInput[]
  emoji?: string | null
  slug?: string | null
  sort_order?: number | null
}

export type StaffAchievementPatch = Partial<StaffAchievementCreate> & {
  status?: AchievementStatus
}

export type CriteriaParamSpec = {
  name: string
  kind: 'int' | 'choice'
  required: boolean
  minimum: number | null
  maximum: number | null
  choices: (string | number)[]
  default: string | number | null
}

export type CriteriaSpec = {
  type: string
  require_any_of: string[]
  params: CriteriaParamSpec[]
}
