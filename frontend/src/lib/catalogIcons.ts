import type { CatalogIconWithPackPublic, PackCardPublic } from '../types/marketplace'

export function isCatalogIconAssignable(
  icon: CatalogIconWithPackPublic,
  userId?: string | null,
): boolean {
  if (icon.pack.unlocked || icon.pack.price_tokens <= 0) {
    return true
  }
  return Boolean(userId && icon.pack.author_id === userId)
}

export type CatalogIconPackGroup = {
  pack: PackCardPublic
  icons: CatalogIconWithPackPublic[]
}

export function groupCatalogIconsByPack(
  icons: readonly CatalogIconWithPackPublic[],
): CatalogIconPackGroup[] {
  const groups = new Map<string, CatalogIconPackGroup>()
  const order: string[] = []
  for (const icon of icons) {
    let group = groups.get(icon.pack.id)
    if (!group) {
      group = { pack: icon.pack, icons: [] }
      groups.set(icon.pack.id, group)
      order.push(icon.pack.id)
    }
    group.icons.push(icon)
  }
  return order.map((id) => groups.get(id)).filter((group): group is CatalogIconPackGroup => Boolean(group))
}

export function catalogIconMatchesQuery(
  icon: CatalogIconWithPackPublic,
  query: string,
): boolean {
  const needle = query.trim().toLowerCase()
  if (!needle) {
    return true
  }
  if (icon.label.toLowerCase().includes(needle) || icon.slug.toLowerCase().includes(needle)) {
    return true
  }
  if (icon.pack.name.toLowerCase().includes(needle)) {
    return true
  }
  return icon.search_tags.some(
    (tag) => tag.label.toLowerCase().includes(needle) || tag.slug.toLowerCase().includes(needle),
  )
}

export function buildCollapsedCatalogIcons(
  icons: readonly CatalogIconWithPackPublic[],
  selectedId: string | null | undefined,
  count: number,
): CatalogIconWithPackPublic[] {
  if (icons.length <= count) {
    return [...icons]
  }
  const result: CatalogIconWithPackPublic[] = []
  const selected = selectedId ? icons.find((icon) => icon.id === selectedId) : undefined
  if (selected) {
    result.push(selected)
  }
  for (const icon of icons) {
    if (result.length >= count) {
      break
    }
    if (!result.some((item) => item.id === icon.id)) {
      result.push(icon)
    }
  }
  return result
}

export function pickRandomSample<T>(items: readonly T[], count: number): T[] {
  if (count <= 0 || items.length === 0) {
    return []
  }
  const copy = [...items]
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy.slice(0, Math.min(count, copy.length))
}
