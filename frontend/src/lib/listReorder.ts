export type DropEdge = 'before' | 'after'

export function moveItem<T>(items: T[], fromIndex: number, toIndex: number): T[] {
  if (
    fromIndex < 0 ||
    toIndex < 0 ||
    fromIndex >= items.length ||
    toIndex >= items.length ||
    fromIndex === toIndex
  ) {
    return items
  }
  const next = [...items]
  const [item] = next.splice(fromIndex, 1)
  next.splice(toIndex, 0, item)
  return next
}

export function moveItemById<T extends { id: string }>(
  items: T[],
  id: string,
  direction: 'up' | 'down',
): T[] {
  const fromIndex = items.findIndex((item) => item.id === id)
  if (fromIndex < 0) {
    return items
  }
  const toIndex = direction === 'up' ? fromIndex - 1 : fromIndex + 1
  return moveItem(items, fromIndex, toIndex)
}

export function dropEdgeFromClientY(clientY: number, element: Element): DropEdge {
  const rect = element.getBoundingClientRect()
  return clientY < rect.top + rect.height / 2 ? 'before' : 'after'
}

/** Target index for moveItem after dropping relative to another item. */
export function dropIndexForEdge(
  fromIndex: number,
  targetIndex: number,
  edge: DropEdge,
): number {
  let toIndex = targetIndex + (edge === 'after' ? 1 : 0)
  if (fromIndex < toIndex) {
    toIndex -= 1
  }
  return toIndex
}
