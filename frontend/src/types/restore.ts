export type RestoreStatus = 'preview' | 'applied' | 'cancelled'

export type RestoreSummary = {
  entries_total: number
  entries_new: number
  entries_existing: number
  first_recorded_at: string | null
  last_recorded_at: string | null
  tag_groups_new: number
  tags_new: number
  goals_new: number
  note_templates_new: number
  attachments_total: number
  attachments_ready: number
  attachments_lost: number
  parts_total: number
  missing_parts: number[]
}

export type RestoreWarning = {
  code: 'ambiguous_tag' | 'unknown_tag' | 'unknown_goal' | 'invalid_attachment' | string
  slug: string | null
  file: string | null
}

export type DiaryRestore = {
  id: string
  status: RestoreStatus
  format_version: number
  exported_at: string | null
  created_at: string
  applied_at: string | null
  summary: RestoreSummary
  warnings: RestoreWarning[]
}
