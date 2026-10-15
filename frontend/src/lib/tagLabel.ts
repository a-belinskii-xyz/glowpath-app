import type { TagGroupPublic } from '../types/tag'

/** Comparison key for tag names, same rules as the API: «Дождь» = « ДОЖДЬ » = «дождь». */
export function tagLabelKey(text: string): string {
  return text.normalize('NFKC').toLowerCase().replace(/ё/g, 'е').replace(/\s+/g, ' ').trim()
}

/** Group that collects tags typed on the fly in an entry (GP-54). */
export const NEW_TAGS_GROUP_SLUG = '_new_tags'

/** Colour → shape emoji of the same colour, as on the API. */
export const NEW_TAG_STYLES: Record<string, readonly string[]> = {
  '#60a5fa': ['🔵', '🔷', '🟦'],
  '#2563eb': ['🔵', '🔷', '🟦'],
  '#0ea5e9': ['🔵', '🔹', '🟦'],
  '#14b8a6': ['🟢', '🟩'],
  '#34d399': ['🟢', '🟩'],
  '#84cc16': ['🟢', '🟩'],
  '#eab308': ['🟡', '🟨'],
  '#f59e0b': ['🟠', '🔶', '🟡'],
  '#f97316': ['🟠', '🔶', '🟧'],
  '#ef4444': ['🔴', '🟥', '🔺'],
  '#a78bfa': ['🟣', '🟪'],
}

function pick<T>(items: readonly T[]): T {
  return items[Math.floor(Math.random() * items.length)]
}

export function randomNewTagStyle(): { color: string; icon: string } {
  const color = pick(Object.keys(NEW_TAG_STYLES))
  return { color, icon: pick(NEW_TAG_STYLES[color]) }
}

export function isNewTagsGroup(group: Pick<TagGroupPublic, 'slug' | 'is_system'>): boolean {
  return Boolean(group.is_system) || group.slug === NEW_TAGS_GROUP_SLUG
}
