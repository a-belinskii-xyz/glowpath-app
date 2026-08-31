import type { ApiLocale } from '../lib/locale'
import { defaultMoodScoreStyle, resolveMoodPreferences } from '../lib/moodScale'
import type { GoalPublic } from '../types/goal'
import type {
  CalendarDayPublic,
  ListMoodEntriesParams,
  MoodEntryCreate,
  MoodEntryListResponse,
  MoodEntryPatch,
  MoodEntryPublic,
  MoodEntryStatsResponse,
  MoodEntryStreakResponse,
  SearchMoodEntriesParams,
} from '../types/mood'
import type { MoodPreferencesPublic } from '../types/moodPreferences'
import type { OnboardingSuggestions } from '../types/onboarding'
import type { NoteTemplateListResponse, NoteTemplatePublic } from '../types/noteTemplate'
import type { TagGroupPublic, TagPublic } from '../types/tag'
import type { GoalCalendarResponse, GoalStatsResponse } from '../types/goal'
import { computeGuestGoalCalendar, computeGuestGoalStats, enrichGuestGoalsWithProgress } from './goalAnalytics'
import { guestDbGet, guestDbSet } from './db'
import { computeGuestCalendar, computeGuestStats, computeGuestStreak } from './moodAnalytics'
import { seedBaseDefaults, seedFromSuggestions } from './provision'

export type GuestMeta = {
  visitor_id: string
  timezone: string
  onboarding_completed: boolean
  locale: ApiLocale
}

const KEYS = {
  meta: 'meta',
  tagGroups: 'tag_groups',
  goals: 'goals',
  noteTemplates: 'note_templates',
  moodPreferences: 'mood_preferences',
  entries: 'entries',
} as const

function newId(): string {
  return crypto.randomUUID()
}

function nowIso(): string {
  return new Date().toISOString()
}

export async function getGuestMeta(): Promise<GuestMeta | null> {
  return guestDbGet<GuestMeta>(KEYS.meta)
}

export async function ensureGuestMeta(visitorId: string): Promise<GuestMeta> {
  const existing = await getGuestMeta()
  if (existing) {
    return existing
  }
  const meta: GuestMeta = {
    visitor_id: visitorId,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
    onboarding_completed: false,
    locale: 'en',
  }
  await guestDbSet(KEYS.meta, meta)
  return meta
}

export async function setGuestLocale(locale: ApiLocale): Promise<void> {
  const meta = await getGuestMeta()
  if (!meta) return
  await guestDbSet(KEYS.meta, { ...meta, locale })
}

export async function getGuestEntryCount(): Promise<number> {
  const entries = (await guestDbGet<MoodEntryPublic[]>(KEYS.entries)) ?? []
  return entries.length
}

const guestEntryCountListeners = new Set<(count: number) => void>()

export function subscribeGuestEntryCount(listener: (count: number) => void): () => void {
  guestEntryCountListeners.add(listener)
  return () => {
    guestEntryCountListeners.delete(listener)
  }
}

async function notifyGuestEntryCountListeners(): Promise<void> {
  const count = await getGuestEntryCount()
  for (const listener of guestEntryCountListeners) {
    listener(count)
  }
}

export async function guestHeartbeatSync(): Promise<void> {
  const meta = await getGuestMeta()
  if (!meta) return
  const { sendGuestHeartbeat } = await import('../api/guest')
  const entryCount = await getGuestEntryCount()
  try {
    await sendGuestHeartbeat({
      visitor_id: meta.visitor_id,
      timezone: meta.timezone,
      locale: meta.locale,
      entry_count: entryCount,
      onboarding_completed: meta.onboarding_completed,
    })
  } catch {
    // telemetry is best-effort
  }
  await notifyGuestEntryCountListeners()
}

export async function completeGuestOnboarding(params: {
  skip: boolean
  suggestions?: OnboardingSuggestions | null
  selectedGroupSlugs?: string[]
  selectedTemplateSlugs?: string[]
}): Promise<void> {
  const meta = await getGuestMeta()
  if (!meta) {
    throw new Error('Guest meta missing')
  }
  await seedBaseDefaults(meta.locale)
  if (!params.skip && params.suggestions) {
    await seedFromSuggestions(
      params.suggestions,
      params.selectedGroupSlugs ?? [],
      params.selectedTemplateSlugs ?? [],
      meta.locale,
    )
  }
  await guestDbSet(KEYS.meta, { ...meta, onboarding_completed: true })
  await guestHeartbeatSync()
}

export async function listGuestTagGroups() {
  const items = (await guestDbGet<TagGroupPublic[]>(KEYS.tagGroups)) ?? []
  return {
    items,
    entry_visible_tag_group_limit: 4,
    frequent_tags_enabled: false,
    frequent_tags: [] as TagPublic[],
  }
}

export async function listGuestGoals(params?: { progressOn?: string }): Promise<{ items: GoalPublic[]; entry_visible_goal_limit: number; stats_visible_goal_limit: number }> {
  const items = (await guestDbGet<GoalPublic[]>(KEYS.goals)) ?? []
  const meta = await getGuestMeta()
  const timezone = meta?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC'
  const entries = (await guestDbGet<MoodEntryPublic[]>(KEYS.entries)) ?? []
  const enriched = params?.progressOn
    ? enrichGuestGoalsWithProgress(items, entries, params.progressOn, timezone)
    : items
  return { items: enriched, entry_visible_goal_limit: 3, stats_visible_goal_limit: 5 }
}

export async function listGuestNoteTemplates(): Promise<NoteTemplateListResponse> {
  const raw = (await guestDbGet<NoteTemplatePublic[]>(KEYS.noteTemplates)) ?? []
  const items = raw
    .map((template) => ({
      ...template,
      body: template.body ?? template.bodies?.en ?? template.bodies?.ru ?? '',
    }))
    .sort((left, right) => left.sort_order - right.sort_order)
  return { items }
}

export async function getGuestGoalCalendar(
  params: { recorded_from: string; recorded_to: string },
): Promise<GoalCalendarResponse> {
  const meta = await getGuestMeta()
  const timezone = meta?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC'
  const { goals, entries } = await loadContext(meta?.locale ?? 'en')
  const days = computeGuestGoalCalendar(entries, goals, params, timezone, 5)
  return { days }
}

export async function getGuestGoalStats(
  params: { recorded_from: string; recorded_to: string },
): Promise<GoalStatsResponse> {
  const meta = await getGuestMeta()
  const timezone = meta?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC'
  const { goals, entries } = await loadContext(meta?.locale ?? 'en')
  return computeGuestGoalStats(entries, goals, params, timezone)
}

export async function getGuestMoodPreferences(locale: ApiLocale): Promise<MoodPreferencesPublic> {
  const stored = await guestDbGet<MoodPreferencesPublic>(KEYS.moodPreferences)
  if (stored) {
    return stored
  }
  const scores = resolveMoodPreferences(null, locale)
  return {
    scores,
    use_historical_colors: true,
    show_streak: true,
  }
}

function buildEntryPublic(
  entry: MoodEntryPublic,
  tagGroups: TagGroupPublic[],
  goals: GoalPublic[],
  locale: ApiLocale,
): MoodEntryPublic {
  const tagsById = new Map<string, TagPublic>()
  for (const group of tagGroups) {
    for (const tag of group.tags) {
      tagsById.set(tag.id, tag)
    }
  }
  const goalsById = new Map(goals.map((goal) => [goal.id, goal]))
  const style = defaultMoodScoreStyle(entry.score, locale)
  return {
    ...entry,
    score_label: style.label ?? String(entry.score),
    score_emoji: style.icon,
    score_color: entry.score_color || style.color,
    tags: entry.tags.map((tag) => tagsById.get(tag.id) ?? tag),
    goals: entry.goals.map((goal) => {
      const full = goalsById.get(goal.id)
      return full
        ? {
            id: full.id,
            slug: full.slug,
            label: full.label,
            color: full.color,
            icon_type: full.icon_type,
            icon: full.icon,
            tracking_kind: full.tracking_kind,
            target_amount: full.target_amount,
            unit: full.unit,
            amount: goal.amount ?? null,
          }
        : goal
    }),
    attachments: [],
  }
}

async function loadContext(locale: ApiLocale) {
  const tagGroups = (await guestDbGet<TagGroupPublic[]>(KEYS.tagGroups)) ?? []
  const goals = (await guestDbGet<GoalPublic[]>(KEYS.goals)) ?? []
  const entries = (await guestDbGet<MoodEntryPublic[]>(KEYS.entries)) ?? []
  return { tagGroups, goals, entries, locale }
}

export async function listGuestMoodEntries(
  params: ListMoodEntriesParams = {},
  locale: ApiLocale = 'en',
): Promise<MoodEntryListResponse> {
  const { tagGroups, goals, entries } = await loadContext(locale)
  let filtered = [...entries]
  if (params.recorded_from) {
    filtered = filtered.filter((e) => e.recorded_at >= params.recorded_from!)
  }
  if (params.recorded_to) {
    filtered = filtered.filter((e) => e.recorded_at <= params.recorded_to!)
  }
  if (params.is_favorite !== undefined) {
    filtered = filtered.filter((e) => e.is_favorite === params.is_favorite)
  }
  filtered.sort((a, b) => b.recorded_at.localeCompare(a.recorded_at))
  const offset = params.offset ?? 0
  const limit = params.limit ?? 20
  const slice = filtered.slice(offset, offset + limit).map((entry) =>
    buildEntryPublic(entry, tagGroups, goals, locale),
  )
  return { items: slice, limit, offset }
}

export async function searchGuestMoodEntries(
  params: SearchMoodEntriesParams,
  locale: ApiLocale = 'en',
): Promise<MoodEntryListResponse> {
  const q = params.q.trim().toLowerCase()
  const response = await listGuestMoodEntries({ limit: 500, offset: 0 }, locale)
  const items = response.items.filter(
    (entry) => entry.note?.toLowerCase().includes(q) || entry.score_label.toLowerCase().includes(q),
  )
  return {
    items: items.slice(0, params.limit ?? 40),
    limit: params.limit ?? 40,
    offset: 0,
  }
}

export async function getGuestMoodEntry(entryId: string, locale: ApiLocale = 'en'): Promise<MoodEntryPublic> {
  const { tagGroups, goals, entries } = await loadContext(locale)
  const entry = entries.find((item) => item.id === entryId)
  if (!entry) {
    throw new Error('Entry not found')
  }
  return buildEntryPublic(entry, tagGroups, goals, locale)
}

export async function createGuestMoodEntry(body: MoodEntryCreate, locale: ApiLocale = 'en'): Promise<MoodEntryPublic> {
  const { tagGroups, goals, entries } = await loadContext(locale)
  const style = defaultMoodScoreStyle(body.score, locale)
  const tagsById = new Map<string, TagPublic>()
  for (const group of tagGroups) {
    for (const tag of group.tags) {
      tagsById.set(tag.id, tag)
    }
  }
  const goalsById = new Map(goals.map((goal) => [goal.id, goal]))
  const entry: MoodEntryPublic = {
    id: newId(),
    recorded_at: body.recorded_at,
    score: body.score,
    score_label: style.label ?? String(body.score),
    score_emoji: style.icon,
    score_color: style.color,
    note: body.note ?? null,
    is_favorite: false,
    tags: body.tag_ids.map((id) => tagsById.get(id)).filter(Boolean) as TagPublic[],
    goals: body.goal_ids
      .map((id) => {
        const goal = goalsById.get(id)
        if (!goal) return null
        const progress = body.goal_progress?.find((item) => item.goal_id === id)
        return {
          id: goal.id,
          slug: goal.slug,
          label: goal.label,
          color: goal.color,
          icon_type: goal.icon_type,
          icon: goal.icon,
          tracking_kind: goal.tracking_kind,
          target_amount: goal.target_amount,
          unit: goal.unit,
          amount: progress?.amount ?? null,
        }
      })
      .filter(Boolean) as MoodEntryPublic['goals'],
    attachments: [],
    created_at: nowIso(),
    updated_at: nowIso(),
  }
  entries.push(entry)
  await guestDbSet(KEYS.entries, entries)
  await guestHeartbeatSync()
  return buildEntryPublic(entry, tagGroups, goals, locale)
}

export async function patchGuestMoodEntry(
  entryId: string,
  body: MoodEntryPatch,
  locale: ApiLocale = 'en',
): Promise<MoodEntryPublic> {
  const { tagGroups, goals, entries } = await loadContext(locale)
  const index = entries.findIndex((item) => item.id === entryId)
  if (index < 0) {
    throw new Error('Entry not found')
  }
  const current = entries[index]
  const style = defaultMoodScoreStyle(body.score ?? current.score, locale)
  const tagsById = new Map<string, TagPublic>()
  for (const group of tagGroups) {
    for (const tag of group.tags) {
      tagsById.set(tag.id, tag)
    }
  }
  const goalsById = new Map(goals.map((goal) => [goal.id, goal]))
  const next: MoodEntryPublic = {
    ...current,
    score: body.score ?? current.score,
    score_label: style.label ?? String(body.score ?? current.score),
    score_emoji: style.icon,
    score_color: style.color,
    recorded_at: body.recorded_at ?? current.recorded_at,
    note: body.note === undefined ? current.note : body.note,
    is_favorite: body.is_favorite ?? current.is_favorite,
    tags:
      body.tag_ids === undefined
        ? current.tags
        : (body.tag_ids.map((id) => tagsById.get(id)).filter(Boolean) as TagPublic[]),
    goals:
      body.goal_ids === undefined
        ? current.goals
        : (body.goal_ids
            .map((id) => {
              const goal = goalsById.get(id)
              if (!goal) return null
              const progress = body.goal_progress?.find((item) => item.goal_id === id)
              return {
                id: goal.id,
                slug: goal.slug,
                label: goal.label,
                color: goal.color,
                icon_type: goal.icon_type,
                icon: goal.icon,
                tracking_kind: goal.tracking_kind,
                target_amount: goal.target_amount,
                unit: goal.unit,
                amount: progress?.amount ?? null,
              }
            })
            .filter(Boolean) as MoodEntryPublic['goals']),
    updated_at: nowIso(),
  }
  entries[index] = next
  await guestDbSet(KEYS.entries, entries)
  await guestHeartbeatSync()
  return buildEntryPublic(next, tagGroups, goals, locale)
}

export async function deleteGuestMoodEntry(entryId: string): Promise<void> {
  const entries = (await guestDbGet<MoodEntryPublic[]>(KEYS.entries)) ?? []
  await guestDbSet(
    KEYS.entries,
    entries.filter((entry) => entry.id !== entryId),
  )
  await guestHeartbeatSync()
}

export async function getGuestMoodEntryCalendar(
  params: { recorded_from: string; recorded_to: string },
  timezone: string,
  locale: ApiLocale = 'en',
): Promise<{ days: CalendarDayPublic[] }> {
  const { entries } = await loadContext(locale)
  return { days: computeGuestCalendar(entries, params, timezone) }
}

export async function getGuestMoodEntryStreak(timezone: string, locale: ApiLocale = 'en'): Promise<MoodEntryStreakResponse> {
  const { entries } = await loadContext(locale)
  return computeGuestStreak(entries, timezone)
}

export async function getGuestMoodEntryStats(
  params: { recorded_from: string; recorded_to: string },
  timezone: string,
  locale: ApiLocale = 'en',
): Promise<MoodEntryStatsResponse> {
  const { entries, tagGroups, goals } = await loadContext(locale)
  const preferences = await getGuestMoodPreferences(locale)
  return computeGuestStats(entries, params, timezone, locale, tagGroups, goals, preferences.scores)
}

export async function buildGuestImportPayload(): Promise<Record<string, unknown>> {
  const meta = await getGuestMeta()
  const tagGroups = (await guestDbGet<TagGroupPublic[]>(KEYS.tagGroups)) ?? []
  const goals = (await guestDbGet<GoalPublic[]>(KEYS.goals)) ?? []
  const noteTemplates = (await guestDbGet<unknown[]>(KEYS.noteTemplates)) ?? []
  const moodPreferences = await guestDbGet<MoodPreferencesPublic>(KEYS.moodPreferences)
  const entries = (await guestDbGet<MoodEntryPublic[]>(KEYS.entries)) ?? []

  const tags = tagGroups.flatMap((group) =>
    group.tags.map((tag) => ({
      local_id: tag.id,
      slug: tag.slug,
      group_slug: group.slug,
      labels: tag.labels,
      sort_order: tag.sort_order,
      color: tag.color,
      icon_type: tag.icon_type,
      icon: tag.icon,
    })),
  )

  return {
    meta: {
      onboarding_completed: meta?.onboarding_completed ?? false,
    },
    tag_groups: tagGroups.map((group) => ({
      slug: group.slug,
      labels: group.labels,
      sort_order: group.sort_order,
      show_on_entry: group.show_on_entry,
    })),
    tags,
    goals: goals.map((goal) => ({
      local_id: goal.id,
      slug: goal.slug,
      labels: goal.labels,
      times_per_week: goal.times_per_week,
      tracking_kind: goal.tracking_kind,
      target_amount: goal.target_amount,
      unit: goal.unit,
      starts_on: goal.starts_on,
      ends_on: goal.ends_on,
      sort_order: goal.sort_order,
      show_on_entry: goal.show_on_entry,
      show_in_stats: goal.show_in_stats,
      color: goal.color,
      icon_type: goal.icon_type,
      icon: goal.icon,
    })),
    note_templates: noteTemplates,
    mood_preferences: moodPreferences,
    entries: entries.map((entry) => ({
      score: entry.score,
      recorded_at: entry.recorded_at,
      note: entry.note,
      is_favorite: entry.is_favorite,
      tag_ids: entry.tags.map((tag) => tag.id),
      goal_ids: entry.goals.map((goal) => goal.id),
      goal_progress: entry.goals
        .filter((goal) => goal.amount != null)
        .map((goal) => ({ goal_id: goal.id, amount: goal.amount as number })),
    })),
  }
}

export async function clearGuestDiary(): Promise<void> {
  const { guestDbDeleteDatabase } = await import('./db')
  await guestDbDeleteDatabase()
  for (const listener of guestEntryCountListeners) {
    listener(0)
  }
}
