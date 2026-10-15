import type { CatalogIconPublic, IconUsage } from '../types/marketplace'
import type { GoalCalendarDayPublic, GoalPublic } from '../types/goal'
import type { CalendarDayPublic, MoodEntryGoal, MoodEntryPublic, MoodEntryTag } from '../types/mood'
import type { MoodScoreStylePublic } from '../types/moodPreferences'

const SCORES = [1, 2, 3, 4, 5] as const
const FALLBACK_COLOR = '#94a3b8'
/** One month of made-up moods; repeats past day 31. Mostly good days, a few dips. */
const DAY_SCORES = [4, 3, 5, 4, 2, 4, 5, 3, 4, 1, 3, 4, 5, 4, 3, 2, 4, 5, 5, 3, 4, 4, 2, 3, 5, 4, 3, 4, 5, 3, 4]
const SECOND_ENTRY_EVERY = 4
const PREVIEW_ENTRY_DAYS = 3

/**
 * Icons the pack recommends for `usage`. A pack without any hints still styles the mood
 * scale, but tags and goals only take icons recommended for them.
 */
export function iconsForUsage(icons: CatalogIconPublic[], usage: IconUsage): CatalogIconPublic[] {
  const hasHints = icons.some((icon) => icon.suggested_usage.length > 0)
  if (!hasHints) return usage === 'mood' ? icons : []
  return icons.filter((icon) => icon.suggested_usage.includes(usage))
}

/** Icons for made-up tags and goals when neither the pack nor the viewer has any. */
const DEFAULT_TAG_EMOJI = ['💼', '🏃', '👫', '😴', '🏡', '🌴']
const DEFAULT_GOAL_EMOJI = ['🚶', '📖', '💧', '🧘']
const DEFAULT_TAG_COLOR = '#60a5fa'
const DEFAULT_GOAL_COLOR = '#34d399'

function iconColor(icon: CatalogIconPublic, fallback = FALLBACK_COLOR): string {
  return icon.suggested_colors[0] ?? fallback
}

/** Mood scale with the pack's icons: score hints first, then the remaining mood icons in order. */
export function previewMoodScale(
  icons: CatalogIconPublic[],
  base: Record<string, MoodScoreStylePublic>,
): Record<string, MoodScoreStylePublic> {
  const moodIcons = iconsForUsage(icons, 'mood')
  if (moodIcons.length === 0) return base
  const used = new Set<string>()
  const scale: Record<string, MoodScoreStylePublic> = { ...base }
  for (const score of SCORES) {
    const hinted = moodIcons.find(
      (icon) => icon.suggested_mood_scores.includes(score) && !used.has(icon.id),
    )
    const icon =
      hinted ??
      moodIcons.find((candidate) => !used.has(candidate.id)) ??
      moodIcons[(score - 1) % moodIcons.length]
    used.add(icon.id)
    const current = base[String(score)]
    scale[String(score)] = {
      ...current,
      icon_type: 'catalog',
      icon: icon.id,
      color: iconColor(icon, current?.color),
    }
  }
  return scale
}

export type PreviewData = {
  year: number
  month: number
  tags: MoodEntryTag[]
  goals: GoalPublic[]
  moodDays: CalendarDayPublic[]
  goalDays: GoalCalendarDayPublic[]
  entries: MoodEntryPublic[]
}

const pad = (value: number) => String(value).padStart(2, '0')

/** Made-up month of diary data (the previous calendar month) styled with the pack's icons. */
export function buildPreviewData(options: {
  icons: CatalogIconPublic[]
  scale: Record<string, MoodScoreStylePublic>
  tagLabels: string[]
  goalLabels: string[]
  /** One note per mood score, from awful to great. */
  notes: string[]
  /** The viewer's own tags and goals, shown when the pack has no icons for them. */
  ownTags?: MoodEntryTag[]
  ownGoals?: GoalPublic[]
  now?: Date
}): PreviewData {
  const { icons, scale, tagLabels, goalLabels, notes } = options
  const now = options.now ?? new Date()
  const first = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - 1, 1))
  const year = first.getUTCFullYear()
  const month = first.getUTCMonth()
  const daysInMonth = new Date(Date.UTC(year, month + 1, 0)).getUTCDate()

  const tagIcons = iconsForUsage(icons, 'tag')
  const goalIcons = iconsForUsage(icons, 'goal')
  const mockTag = (index: number, style: Pick<MoodEntryTag, 'color' | 'icon_type' | 'icon'>) => ({
    id: `preview-tag-${index}`,
    slug: `preview-tag-${index}`,
    label: tagLabels[index],
    group_id: 'preview',
    ...style,
  })
  const mockGoal = (
    index: number,
    style: Pick<GoalPublic, 'color' | 'icon_type' | 'icon'>,
  ): GoalPublic => ({
    id: `preview-goal-${index}`,
    slug: `preview-goal-${index}`,
    label: goalLabels[index],
    labels: {},
    times_per_week: 3,
    tracking_kind: 'binary',
    target_amount: null,
    unit: null,
    partial_label: null,
    min_amount: null,
    starts_on: `${year}-01-01`,
    ends_on: null,
    sort_order: index,
    show_on_entry: true,
    show_in_stats: true,
    completed_this_week: 0,
    day_amount: 0,
    week_marks: [],
    ...style,
  })

  const ownTags = (options.ownTags ?? []).slice(0, tagLabels.length)
  const ownGoals = (options.ownGoals ?? []).slice(0, goalLabels.length)
  const tags: MoodEntryTag[] =
    tagIcons.length > 0
      ? tagIcons.slice(0, tagLabels.length).map((icon, index) =>
          mockTag(index, { color: iconColor(icon), icon_type: 'catalog', icon: icon.id }),
        )
      : ownTags.length > 0
        ? ownTags
        : tagLabels.map((_, index) =>
            mockTag(index, {
              color: DEFAULT_TAG_COLOR,
              icon_type: 'emoji',
              icon: DEFAULT_TAG_EMOJI[index % DEFAULT_TAG_EMOJI.length],
            }),
          )
  const goals: GoalPublic[] =
    goalIcons.length > 0
      ? goalIcons.slice(0, goalLabels.length).map((icon, index) =>
          mockGoal(index, { color: iconColor(icon), icon_type: 'catalog', icon: icon.id }),
        )
      : ownGoals.length > 0
        ? ownGoals
        : goalLabels.map((_, index) =>
            mockGoal(index, {
              color: DEFAULT_GOAL_COLOR,
              icon_type: 'emoji',
              icon: DEFAULT_GOAL_EMOJI[index % DEFAULT_GOAL_EMOJI.length],
            }),
          )
  const entryGoals: MoodEntryGoal[] = goals.map((goal) => ({
    id: goal.id,
    slug: goal.slug,
    label: goal.label,
    color: goal.color,
    icon_type: goal.icon_type,
    icon: goal.icon,
  }))

  const moodDays: CalendarDayPublic[] = []
  const goalDays: GoalCalendarDayPublic[] = []
  const entries: MoodEntryPublic[] = []

  for (let day = 1; day <= daysInMonth; day += 1) {
    const date = `${year}-${pad(month + 1)}-${pad(day)}`
    const dayScores = [DAY_SCORES[(day - 1) % DAY_SCORES.length]]
    if (day % SECOND_ENTRY_EVERY === 0) dayScores.push(DAY_SCORES[day % DAY_SCORES.length])

    moodDays.push({
      date,
      entry_count: dayScores.length,
      scores: dayScores.map((score) => ({
        score,
        score_emoji: '',
        score_color: scale[String(score)]?.color ?? FALLBACK_COLOR,
      })),
    })
    const dayGoals = goals.filter((_, index) => (day + index) % (index + 2) === 0)
    goalDays.push({
      date,
      entry_count: dayGoals.length,
      goals: dayGoals.map((goal) => ({ goal_id: goal.id })),
    })

    if (day <= daysInMonth - PREVIEW_ENTRY_DAYS) continue
    dayScores.forEach((score, index) => {
      const seed = day + index
      const recordedAt = `${date}T${pad(20 - index * 9)}:15:00Z`
      entries.push({
        id: `preview-entry-${day}-${index}`,
        recorded_at: recordedAt,
        score,
        score_label: scale[String(score)]?.label ?? String(score),
        score_emoji: '',
        score_color: scale[String(score)]?.color ?? FALLBACK_COLOR,
        note: notes[score - 1] ?? null,
        is_favorite: seed % 3 === 0,
        tags: tags.length > 0 ? [tags[seed % tags.length], tags[(seed + 1) % tags.length]] : [],
        goals: entryGoals.length > 0 ? [entryGoals[seed % entryGoals.length]] : [],
        attachments: [],
        created_at: recordedAt,
        updated_at: recordedAt,
      })
    })
  }

  // Dedupe tags when the pack recommends a single tag icon.
  for (const entry of entries) {
    entry.tags = entry.tags.filter(
      (tag, index, list) => list.findIndex((other) => other.id === tag.id) === index,
    )
  }
  entries.sort((a, b) => b.recorded_at.localeCompare(a.recorded_at))
  return { year, month, tags, goals, moodDays, goalDays, entries }
}
