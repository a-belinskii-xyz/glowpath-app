import type { ApiLocale } from './locale'

export type BuiltinMoodIcon = {
  slug: string
  labels: Record<ApiLocale, string>
  assetPath: string
  defaultScore?: number
}

export const MOOD_BUILTIN_ICONS: BuiltinMoodIcon[] = [
  {
    slug: 'awful-cloud',
    labels: { en: 'Rain cloud', ru: 'Дождливая туча' },
    assetPath: '/mood-icons/awful-cloud.svg',
    defaultScore: 1,
  },
  {
    slug: 'bad-droplet',
    labels: { en: 'Droplet', ru: 'Капля' },
    assetPath: '/mood-icons/bad-droplet.svg',
    defaultScore: 2,
  },
  {
    slug: 'neutral-line',
    labels: { en: 'Flat line', ru: 'Ровная линия' },
    assetPath: '/mood-icons/neutral-line.svg',
    defaultScore: 3,
  },
  {
    slug: 'good-sun',
    labels: { en: 'Sun', ru: 'Солнце' },
    assetPath: '/mood-icons/good-sun.svg',
    defaultScore: 4,
  },
  {
    slug: 'great-star',
    labels: { en: 'Star', ru: 'Звезда' },
    assetPath: '/mood-icons/great-star.svg',
    defaultScore: 5,
  },
  {
    slug: 'heart',
    labels: { en: 'Heart', ru: 'Сердце' },
    assetPath: '/mood-icons/heart.svg',
  },
  {
    slug: 'leaf',
    labels: { en: 'Leaf', ru: 'Лист' },
    assetPath: '/mood-icons/leaf.svg',
  },
  {
    slug: 'fire',
    labels: { en: 'Fire', ru: 'Огонь' },
    assetPath: '/mood-icons/fire.svg',
  },
  {
    slug: 'moon',
    labels: { en: 'Moon', ru: 'Луна' },
    assetPath: '/mood-icons/moon.svg',
  },
  {
    slug: 'sparkles',
    labels: { en: 'Sparkles', ru: 'Искры' },
    assetPath: '/mood-icons/sparkles.svg',
  },
]

const BUILTIN_BY_SLUG = new Map(MOOD_BUILTIN_ICONS.map((icon) => [icon.slug, icon]))

export function getBuiltinMoodIcon(slug: string): BuiltinMoodIcon | undefined {
  return BUILTIN_BY_SLUG.get(slug)
}

export function defaultBuiltinSlugForScore(score: number): string {
  return MOOD_BUILTIN_ICONS.find((icon) => icon.defaultScore === score)?.slug ?? 'neutral-line'
}

export function getBuiltinMoodIconLabel(slug: string, locale: ApiLocale): string {
  const icon = getBuiltinMoodIcon(slug)
  if (!icon) {
    return slug
  }
  return icon.labels[locale] ?? icon.labels.en
}

export function getBuiltinMoodIconPath(slug: string): string {
  return getBuiltinMoodIcon(slug)?.assetPath ?? `/mood-icons/${slug}.svg`
}
