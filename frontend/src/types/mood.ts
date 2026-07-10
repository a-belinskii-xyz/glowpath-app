export type MoodEntryTag = {
  id: string
  slug: string
  label: string
  group_id: string
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
  tags: MoodEntryTag[]
  attachments: AttachmentPublic[]
  created_at: string
  updated_at: string
}

export type MoodEntryListResponse = {
  items: MoodEntryPublic[]
  limit: number
  offset: number
}

export type MoodEntryCreate = {
  score: number
  recorded_at: string
  note?: string | null
  tag_ids: string[]
}

export type MoodEntryPatch = {
  score?: number
  recorded_at?: string
  note?: string | null
  tag_ids?: string[]
}

export type ListMoodEntriesParams = {
  limit?: number
  offset?: number
  recorded_from?: string
  recorded_to?: string
}
