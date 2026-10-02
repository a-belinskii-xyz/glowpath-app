import type { IconUsage } from '../../types/marketplace'

export const MOOD_SCORES = [1, 2, 3, 4, 5] as const
export const ICON_USAGES: IconUsage[] = ['mood', 'tag', 'goal']
export const ACCEPTED_ICON_TYPES = 'image/svg+xml,image/png,image/jpeg,image/webp,image/gif'
export const MAX_ICON_COLORS = 8

export function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value]
}
