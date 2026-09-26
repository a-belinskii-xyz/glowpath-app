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
