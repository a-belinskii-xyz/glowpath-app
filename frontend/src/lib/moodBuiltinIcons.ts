import type { ApiLocale } from './locale'

export type BuiltinMoodIcon = {
  slug: string
  labels: Record<ApiLocale, string>
  assetPath: string
  /** Mood score this icon is suggested for in pickers. */
  suggestedScore?: number
}

export const MOOD_BUILTIN_ICONS: BuiltinMoodIcon[] = [
  {
    slug: 'face-awful-cry',
    labels: { en: 'Crying', ru: 'Плачу' },
    assetPath: '/mood-icons/face-awful-cry.svg',
    suggestedScore: 1,
  },
  {
    slug: 'face-awful-angry',
    labels: { en: 'Angry', ru: 'Злюсь' },
    assetPath: '/mood-icons/face-awful-angry.svg',
    suggestedScore: 1,
  },
  {
    slug: 'face-awful-storm',
    labels: { en: 'Overwhelmed', ru: 'Накрыло' },
    assetPath: '/mood-icons/face-awful-storm.svg',
    suggestedScore: 1,
  },
  {
    slug: 'face-bad-sad',
    labels: { en: 'Sad', ru: 'Грустно' },
    assetPath: '/mood-icons/face-bad-sad.svg',
    suggestedScore: 2,
  },
  {
    slug: 'face-bad-tired',
    labels: { en: 'Tired', ru: 'Без сил' },
    assetPath: '/mood-icons/face-bad-tired.svg',
    suggestedScore: 2,
  },
  {
    slug: 'face-bad-worried',
    labels: { en: 'Worried', ru: 'Тревожно' },
    assetPath: '/mood-icons/face-bad-worried.svg',
    suggestedScore: 2,
  },
  {
    slug: 'face-neutral-flat',
    labels: { en: 'Neutral', ru: 'Ровно' },
    assetPath: '/mood-icons/face-neutral-flat.svg',
    suggestedScore: 3,
  },
  {
    slug: 'face-neutral-side',
    labels: { en: 'Unsure', ru: 'Так себе' },
    assetPath: '/mood-icons/face-neutral-side.svg',
    suggestedScore: 3,
  },
  {
    slug: 'face-neutral-calm',
    labels: { en: 'Calm', ru: 'Спокойно' },
    assetPath: '/mood-icons/face-neutral-calm.svg',
    suggestedScore: 3,
  },
  {
    slug: 'face-good-smile',
    labels: { en: 'Smile', ru: 'Улыбка' },
    assetPath: '/mood-icons/face-good-smile.svg',
    suggestedScore: 4,
  },
  {
    slug: 'face-good-wink',
    labels: { en: 'Wink', ru: 'Подмигиваю' },
    assetPath: '/mood-icons/face-good-wink.svg',
    suggestedScore: 4,
  },
  {
    slug: 'face-good-blush',
    labels: { en: 'Pleased', ru: 'Приятно' },
    assetPath: '/mood-icons/face-good-blush.svg',
    suggestedScore: 4,
  },
  {
    slug: 'face-great-grin',
    labels: { en: 'Laughing', ru: 'Смеюсь' },
    assetPath: '/mood-icons/face-great-grin.svg',
    suggestedScore: 5,
  },
  {
    slug: 'face-great-stars',
    labels: { en: 'Starstruck', ru: 'В восторге' },
    assetPath: '/mood-icons/face-great-stars.svg',
    suggestedScore: 5,
  },
  {
    slug: 'face-great-love',
    labels: { en: 'In love', ru: 'Любовь' },
    assetPath: '/mood-icons/face-great-love.svg',
    suggestedScore: 5,
  },
  {
    slug: 'awful-cloud',
    labels: { en: 'Rain cloud', ru: 'Дождливая туча' },
    assetPath: '/mood-icons/awful-cloud.svg',
    suggestedScore: 1,
  },
  {
    slug: 'bad-droplet',
    labels: { en: 'Droplet', ru: 'Капля' },
    assetPath: '/mood-icons/bad-droplet.svg',
    suggestedScore: 2,
  },
  {
    slug: 'neutral-line',
    labels: { en: 'Flat line', ru: 'Ровная линия' },
    assetPath: '/mood-icons/neutral-line.svg',
    suggestedScore: 3,
  },
  {
    slug: 'good-sun',
    labels: { en: 'Sun', ru: 'Солнце' },
    assetPath: '/mood-icons/good-sun.svg',
    suggestedScore: 4,
  },
  {
    slug: 'great-star',
    labels: { en: 'Star', ru: 'Звезда' },
    assetPath: '/mood-icons/great-star.svg',
    suggestedScore: 5,
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

/** Full-color faces; the older line icons use `currentColor` and only suit tinted contexts. */
export const MOOD_FACE_ICONS = MOOD_BUILTIN_ICONS.filter((icon) => icon.slug.startsWith('face-'))

export function getBuiltinMoodIcon(slug: string): BuiltinMoodIcon | undefined {
  return BUILTIN_BY_SLUG.get(slug)
}

/** Default mood scale icons; keep in sync with backend DEFAULT_MOOD_SCORE_ICONS. */
export const DEFAULT_MOOD_SCORE_ICONS: Record<number, string> = {
  1: 'face-awful-cry',
  2: 'face-bad-sad',
  3: 'face-neutral-flat',
  4: 'face-good-smile',
  5: 'face-great-grin',
}

export function defaultBuiltinSlugForScore(score: number): string {
  return DEFAULT_MOOD_SCORE_ICONS[score] ?? 'face-neutral-flat'
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
