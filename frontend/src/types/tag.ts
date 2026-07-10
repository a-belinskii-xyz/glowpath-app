export type TagPublic = {
  id: string
  slug: string
  label: string
  group_id: string
}

export type TagGroupPublic = {
  id: string
  slug: string
  label: string
  sort_order: number
  tags: TagPublic[]
}

export type TagGroupListResponse = {
  items: TagGroupPublic[]
}
