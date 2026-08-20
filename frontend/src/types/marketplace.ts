export type PackStatus =
  | 'draft'
  | 'pending_review'
  | 'rejected'
  | 'published'
  | 'archived'

export type SearchTagPublic = {
  id: string
  slug: string
  label: string
  labels: Record<string, string>
  sort_order: number
  is_active: boolean
}

export type SearchTagListResponse = {
  items: SearchTagPublic[]
}

export type CatalogIconPublic = {
  id: string
  pack_id: string
  slug: string
  label: string
  labels: Record<string, string>
  mime_type: string
  size_bytes: number
  suggested_colors: string[]
  suggested_mood_scores: number[]
  sort_order: number
  search_tags: SearchTagPublic[]
}

export type PackCardPublic = {
  id: string
  slug: string
  name: string
  description: string
  labels: {
    name?: Record<string, string>
    description?: Record<string, string>
  } & Record<string, unknown>
  is_official: boolean
  status: PackStatus | string
  price_tokens: number
  unlocked: boolean
  icon_count: number
  cover_icon_id: string | null
  search_tags: string[]
  sort_order: number
  published_at: string | null
  author_id: string | null
  moderation_note: string | null
}

export type PackDetailPublic = PackCardPublic & {
  icons: CatalogIconPublic[]
}

export type PackListResponse = {
  items: PackCardPublic[]
}

export type CatalogIconWithPackPublic = CatalogIconPublic & {
  pack: PackCardPublic
}

export type IconListResponse = {
  items: CatalogIconWithPackPublic[]
}

export type PackUnlockPublic = {
  pack_id: string
  unlocked_at: string
  pack: PackCardPublic | null
}

export type PackUnlockListResponse = {
  items: PackUnlockPublic[]
}

export type PackLabels = {
  name: Record<string, string>
  description?: Record<string, string> | null
}

export type StudioPackCreate = {
  labels: PackLabels
  slug?: string | null
  price_tokens?: number
}

export type StudioPackPatch = {
  labels?: PackLabels | null
  price_tokens?: number | null
  cover_icon_id?: string | null
  clear_cover?: boolean
}

export type StudioIconPatch = {
  labels?: Record<string, string> | null
  suggested_colors?: string[] | null
  suggested_mood_scores?: number[] | null
  search_tag_slugs?: string[] | null
  sort_order?: number | null
}

export type SearchTagCreate = {
  slug: string
  labels: Record<string, string>
  sort_order?: number
  is_active?: boolean
}

export type SearchTagPatch = {
  labels?: Record<string, string> | null
  sort_order?: number | null
  is_active?: boolean | null
}

export type RejectPackBody = {
  note?: string | null
}

export type WalletPublic = {
  balance: number
}

export type WalletLedgerEntryPublic = {
  id: string
  delta: number
  balance_after: number
  kind: string
  pack_id: string | null
  note: string | null
  created_at: string
}

export type WalletLedgerListResponse = {
  items: WalletLedgerEntryPublic[]
}

export type WalletGrantBody = {
  user_id: string
  amount: number
  note?: string | null
}

export type ListPacksParams = {
  q?: string
  tag?: string
  official?: boolean
  unlocked?: boolean
  limit?: number
  offset?: number
}

export type ListIconsParams = {
  q?: string
  tag?: string | string[]
  pack_id?: string
  suggested_mood?: number
  limit?: number
  offset?: number
}

export type UploadStudioIconFields = {
  labels: Record<string, string>
  suggested_colors: string[]
  suggested_mood_scores?: number[]
  search_tag_slugs?: string[]
  slug?: string
}
