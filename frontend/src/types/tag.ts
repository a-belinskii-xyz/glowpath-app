export type TagPublic = {
  id: string
  slug: string
  label: string
  labels: Record<string, string>
  group_id: string
  sort_order: number
}

export type TagGroupPublic = {
  id: string
  slug: string
  label: string
  labels: Record<string, string>
  sort_order: number
  tags: TagPublic[]
}

export type TagGroupListResponse = {
  items: TagGroupPublic[]
}

export type TagGroupWrite = {
  labels: Record<string, string>
  slug?: string
  sort_order?: number
}

export type TagGroupPatch = {
  slug?: string
  labels?: Record<string, string>
  sort_order?: number
}

export type TagWrite = {
  labels: Record<string, string>
  slug?: string
  sort_order?: number
}

export type TagPatch = {
  slug?: string
  labels?: Record<string, string>
  sort_order?: number
}

export type ReorderRequest = {
  ordered_ids: string[]
}
