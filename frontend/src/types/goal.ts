export type GoalPublic = {
  id: string
  slug: string
  label: string
  labels: Record<string, string>
  times_per_week: number
  starts_on: string
  sort_order: number
  show_on_entry: boolean
  completed_this_week: number
}

export type GoalListResponse = {
  items: GoalPublic[]
  entry_visible_goal_limit: number
}

export type GoalWrite = {
  labels: Record<string, string>
  times_per_week: number
  starts_on: string
  slug?: string
  sort_order?: number
  show_on_entry?: boolean
}

export type GoalPatch = {
  slug?: string
  labels?: Record<string, string>
  times_per_week?: number
  starts_on?: string
  sort_order?: number
  show_on_entry?: boolean
}

export type GoalReorderRequest = {
  ordered_ids: string[]
}
