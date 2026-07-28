import type { MoodScoreIconType } from './moodPreferences'

export type TagStyle = {
  color: string
  icon_type: MoodScoreIconType
  icon: string
}

export const DEFAULT_TAG_STYLE: TagStyle = {
  color: '#94a3b8',
  icon_type: 'emoji',
  icon: '🏷',
}

export type TagPublic = {
  id: string
  slug: string
  label: string
  labels: Record<string, string>
  group_id: string
  sort_order: number
  color: string
  icon_type: MoodScoreIconType
  icon: string
}

export type TagGroupPublic = {
  id: string
  slug: string
  label: string
  labels: Record<string, string>
  sort_order: number
  show_on_entry: boolean
  tags: TagPublic[]
}

export type TagGroupListResponse = {
  items: TagGroupPublic[]
  entry_visible_tag_group_limit: number
}

export type TagGroupWrite = {
  labels: Record<string, string>
  slug?: string
  sort_order?: number
  show_on_entry?: boolean
}

export type TagGroupPatch = {
  slug?: string
  labels?: Record<string, string>
  sort_order?: number
  show_on_entry?: boolean
}

export type TagWrite = {
  labels: Record<string, string>
  slug?: string
  sort_order?: number
  color?: string
  icon_type?: MoodScoreIconType
  icon?: string
}

export type TagPatch = {
  slug?: string
  labels?: Record<string, string>
  sort_order?: number
  color?: string
  icon_type?: MoodScoreIconType
  icon?: string
}

export type ReorderRequest = {
  ordered_ids: string[]
}

export type TagIconMeta = {
  id: string
  tag_id: string
  mime_type: string
  size_bytes: number
  original_name: string
  has_source: boolean
}

export type TagIconListResponse = {
  items: TagIconMeta[]
  max_per_tag: number
}

export type TagIconPublic = {
  id: string
  tag_id: string
  mime_type: string
  size_bytes: number
  original_name: string
  has_source: boolean
  tag: TagPublic
}
