export type NoteTemplatePublic = {
  id: string
  slug: string
  label: string
  labels: Record<string, string>
  body: string
  bodies: Record<string, string>
  sort_order: number
}

export type NoteTemplateListResponse = {
  items: NoteTemplatePublic[]
}

export type NoteTemplateWrite = {
  labels: Record<string, string>
  bodies: Record<string, string>
  slug?: string
  sort_order?: number
}

export type NoteTemplatePatch = {
  slug?: string
  labels?: Record<string, string>
  bodies?: Record<string, string>
  sort_order?: number
}

export type NoteTemplateReorderRequest = {
  ordered_ids: string[]
}
