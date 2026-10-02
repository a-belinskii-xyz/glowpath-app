import type { PackLabels } from './marketplace'

export type StaffUserPublic = {
  id: string
  email: string | null
  telegram_linked: boolean
  is_staff: boolean
  balance: number
  created_at: string
}

export type StaffUserListResponse = {
  items: StaffUserPublic[]
}

export type StaffPackCreate = {
  labels: PackLabels
  slug?: string | null
  price_tokens?: number
  sort_order?: number
}

export type PresetExportParams = {
  packIds: string[]
  includeAchievements: boolean
}

export type PresetImportResponse = {
  search_tags: number
  packs: string[]
  icons: number
  achievements: string[]
}

export type StaffSignupSource = {
  source: string
  last_7_days: number
  last_30_days: number
  total: number
}

export type StaffWeekMetrics = {
  starts_at: string
  ends_at: string
  signups: number
  active: number
  regular: number
}

export type StaffMetricsResponse = {
  generated_at: string
  regular_min_days: number
  sources: StaffSignupSource[]
  weeks: StaffWeekMetrics[]
}
