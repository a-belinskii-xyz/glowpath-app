import type { ApiLocale } from '../lib/locale'
import type { GoalPublic } from '../types/goal'
import type { OnboardingSuggestions } from '../types/onboarding'
import type { TagGroupPublic, TagPublic } from '../types/tag'
import { guestDbGet, guestDbSet } from './db'

function newId(): string {
  return crypto.randomUUID()
}

function labelFor(labels: Record<string, string>, locale: ApiLocale): string {
  return labels[locale] ?? labels.en ?? Object.values(labels)[0] ?? ''
}

const BASE_TAG_GROUPS: Array<{
  slug: string
  labels: Record<string, string>
  show_on_entry: boolean
  sort_order: number
  tags: Array<{ slug: string; labels: Record<string, string>; color: string; icon: string; sort_order: number }>
}> = [
  {
    slug: 'weather',
    labels: { en: 'Weather', ru: 'Погода' },
    show_on_entry: true,
    sort_order: 0,
    tags: [
      { slug: 'sunny', labels: { en: 'Sunny', ru: 'Солнечно' }, color: '#f59e0b', icon: '☀️', sort_order: 0 },
      { slug: 'cloudy', labels: { en: 'Cloudy', ru: 'Облачно' }, color: '#94a3b8', icon: '☁️', sort_order: 1 },
      { slug: 'rain', labels: { en: 'Rain', ru: 'Дождь' }, color: '#60a5fa', icon: '🌧️', sort_order: 2 },
    ],
  },
  {
    slug: 'sleep_quality',
    labels: { en: 'Sleep Quality', ru: 'Качество сна' },
    show_on_entry: true,
    sort_order: 1,
    tags: [
      { slug: 'slept_well', labels: { en: 'Slept well', ru: 'Хорошо поспал' }, color: '#34d399', icon: '😴', sort_order: 0 },
      { slug: 'average_sleep', labels: { en: 'Average sleep', ru: 'Средний сон' }, color: '#94a3b8', icon: '😑', sort_order: 1 },
      { slug: 'slept_poorly', labels: { en: 'Slept poorly', ru: 'Плохо спал' }, color: '#f87171', icon: '😩', sort_order: 2 },
    ],
  },
  {
    slug: 'mood',
    labels: { en: 'Mood', ru: 'Настроение' },
    show_on_entry: true,
    sort_order: 2,
    tags: [
      { slug: 'joy', labels: { en: 'Joy', ru: 'Радость' }, color: '#f59e0b', icon: '😊', sort_order: 0 },
      { slug: 'anxiety', labels: { en: 'Anxiety', ru: 'Тревога' }, color: '#a78bfa', icon: '😰', sort_order: 1 },
      { slug: 'calm', labels: { en: 'Calm', ru: 'Спокойствие' }, color: '#34d399', icon: '😌', sort_order: 2 },
    ],
  },
  {
    slug: 'activity',
    labels: { en: 'Activity', ru: 'Активность' },
    show_on_entry: true,
    sort_order: 3,
    tags: [
      { slug: 'work', labels: { en: 'Work', ru: 'Работа' }, color: '#60a5fa', icon: '💼', sort_order: 0 },
      { slug: 'sport', labels: { en: 'Sport', ru: 'Спорт' }, color: '#34d399', icon: '🏃', sort_order: 1 },
      { slug: 'rest', labels: { en: 'Rest', ru: 'Отдых' }, color: '#94a3b8', icon: '🛋️', sort_order: 2 },
    ],
  },
]

const BASE_GOALS = [
  {
    slug: 'early_rise',
    labels: { en: 'Early rise', ru: 'Ранний подъём' },
    times_per_week: 7,
    icon: '🌅',
  },
  {
    slug: 'min_screen_time',
    labels: { en: 'Less screen time', ru: 'Меньше экрана' },
    times_per_week: 5,
    icon: '📵',
  },
  {
    slug: 'exercise',
    labels: { en: 'Exercise', ru: 'Спорт' },
    times_per_week: 3,
    icon: '🏃',
  },
] as const

function buildTagGroups(locale: ApiLocale): TagGroupPublic[] {
  return BASE_TAG_GROUPS.map((group) => {
    const groupId = newId()
    const tags: TagPublic[] = group.tags.map((tag) => ({
      id: newId(),
      slug: tag.slug,
      label: labelFor(tag.labels, locale),
      labels: tag.labels,
      group_id: groupId,
      sort_order: tag.sort_order,
      color: tag.color,
      icon_type: 'emoji',
      icon: tag.icon,
    }))
    return {
      id: groupId,
      slug: group.slug,
      label: labelFor(group.labels, locale),
      labels: group.labels,
      sort_order: group.sort_order,
      show_on_entry: group.show_on_entry,
      tags,
    }
  })
}

function buildGoals(locale: ApiLocale): GoalPublic[] {
  const today = new Date().toISOString().slice(0, 10)
  return BASE_GOALS.map((goal, index) => ({
    id: newId(),
    slug: goal.slug,
    label: labelFor(goal.labels, locale),
    labels: goal.labels,
    times_per_week: goal.times_per_week,
    tracking_kind: 'binary',
    target_amount: null,
    unit: null,
    starts_on: today,
    ends_on: null,
    sort_order: index,
    show_on_entry: index < 3,
    show_in_stats: index < 3,
    color: '#60a5fa',
    icon_type: 'emoji',
    icon: goal.icon,
    completed_this_week: 0,
    day_amount: 0,
  }))
}

export async function seedBaseDefaults(locale: ApiLocale): Promise<void> {
  await guestDbSet('tag_groups', buildTagGroups(locale))
  await guestDbSet('goals', buildGoals(locale))
  await guestDbSet('note_templates', [])
}

export async function seedFromSuggestions(
  suggestions: OnboardingSuggestions,
  selectedGroupSlugs: string[],
  selectedTemplateSlugs: string[],
  _locale: ApiLocale,
): Promise<void> {
  const existingGroups = (await guestDbGet<TagGroupPublic[]>('tag_groups')) ?? []
  const existingSlugs = new Set(existingGroups.map((group) => group.slug))
  const mergedGroups = [...existingGroups]

  for (const group of suggestions.tag_groups) {
    if (!selectedGroupSlugs.includes(group.slug) || existingSlugs.has(group.slug)) {
      continue
    }
    const groupId = newId()
    mergedGroups.push({
      id: groupId,
      slug: group.slug,
      label: group.label,
      labels: { en: group.label, ru: group.label },
      sort_order: mergedGroups.length,
      show_on_entry: mergedGroups.length < 4,
      tags: group.tags.map((tag, index) => ({
        id: newId(),
        slug: tag.slug,
        label: tag.label,
        labels: { en: tag.label, ru: tag.label },
        group_id: groupId,
        sort_order: index,
        color: tag.color,
        icon_type: 'emoji' as const,
        icon: tag.icon,
      })),
    })
  }
  await guestDbSet('tag_groups', mergedGroups)

  const templates = (await guestDbGet<unknown[]>('note_templates')) ?? []
  const templateSlugs = new Set(
    templates.map((item) => (item as { slug?: string }).slug).filter(Boolean),
  )
  const mergedTemplates = [...templates]
  for (const template of suggestions.note_templates) {
    if (!selectedTemplateSlugs.includes(template.slug) || templateSlugs.has(template.slug)) {
      continue
    }
    mergedTemplates.push({
      id: newId(),
      slug: template.slug,
      label: template.label,
      labels: { en: template.label, ru: template.label },
      bodies: { en: template.body, ru: template.body },
      sort_order: mergedTemplates.length,
    })
  }
  await guestDbSet('note_templates', mergedTemplates)
}
