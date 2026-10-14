import { getApiLocale, type ApiLocale } from '../lib/locale'
import {
  defaultMoodScoreEmoji,
  defaultMoodScoreLabel,
  defaultMoodScoreStyle,
  resolveMoodPreferences,
} from '../lib/moodScale'
import type {
  GoalCalendarResponse,
  GoalCheckinLevel,
  GoalListResponse,
  GoalPatch,
  GoalPublic,
  GoalStatsResponse,
  GoalWrite,
} from '../types/goal'
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
import type { MoodPreferencesPublic, MoodPreferencesUpdate } from '../types/moodPreferences'
import type { OnboardingSuggestions } from '../types/onboarding'
import type {
  NoteTemplateListResponse,
  NoteTemplatePatch,
  NoteTemplatePublic,
  NoteTemplateWrite,
} from '../types/noteTemplate'
import type { TagGroupListResponse, TagGroupPublic, TagGroupPatch, TagGroupWrite, TagPatch, TagPublic, TagWrite } from '../types/tag'
import {
  computeGuestGoalCalendar,
  computeGuestGoalStats,
  enrichGuestGoalsWithProgress,
  toPublicGoal,
  type GuestGoal,
} from './goalAnalytics'
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
    locale: getApiLocale(),
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
  const items = (await guestDbGet<GuestGoal[]>(KEYS.goals)) ?? []
  const meta = await getGuestMeta()
  const timezone = meta?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC'
  const entries = (await guestDbGet<MoodEntryPublic[]>(KEYS.entries)) ?? []
  const enriched = params?.progressOn
    ? enrichGuestGoalsWithProgress(items, entries, params.progressOn, timezone)
    : items.map(toPublicGoal)
  return { items: enriched, entry_visible_goal_limit: 3, stats_visible_goal_limit: 5 }
}

function guestSlug(prefix = 'item'): string {
  return `${prefix}_${newId().slice(0, 8)}`
}

function labelFrom(labels: Record<string, string>, locale: ApiLocale = 'en'): string {
  return labels[locale] ?? labels.en ?? Object.values(labels)[0] ?? ''
}

async function saveGuestTagGroups(groups: TagGroupPublic[]): Promise<void> {
  await guestDbSet(KEYS.tagGroups, groups)
  await guestHeartbeatSync()
}

async function saveGuestGoals(goals: GoalPublic[]): Promise<void> {
  await guestDbSet(KEYS.goals, goals)
  await guestHeartbeatSync()
}

async function saveGuestNoteTemplates(templates: NoteTemplatePublic[]): Promise<void> {
  await guestDbSet(KEYS.noteTemplates, templates)
  await guestHeartbeatSync()
}

export async function createGuestTagGroup(body: TagGroupWrite, locale: ApiLocale = 'en'): Promise<TagGroupPublic> {
  const groups = (await guestDbGet<TagGroupPublic[]>(KEYS.tagGroups)) ?? []
  const group: TagGroupPublic = {
    id: newId(),
    slug: body.slug ?? guestSlug('group'),
    label: labelFrom(body.labels, locale),
    labels: body.labels,
    sort_order: body.sort_order ?? groups.length,
    show_on_entry: body.show_on_entry ?? true,
    tags: [],
  }
  groups.push(group)
  await saveGuestTagGroups(groups)
  return group
}

export async function patchGuestTagGroup(
  groupId: string,
  body: TagGroupPatch,
  locale: ApiLocale = 'en',
): Promise<TagGroupPublic> {
  const groups = (await guestDbGet<TagGroupPublic[]>(KEYS.tagGroups)) ?? []
  const index = groups.findIndex((group) => group.id === groupId)
  if (index < 0) {
    throw new Error('Tag group not found')
  }
  const current = groups[index]
  const next: TagGroupPublic = {
    ...current,
    slug: body.slug ?? current.slug,
    labels: body.labels ?? current.labels,
    label: body.labels ? labelFrom(body.labels, locale) : current.label,
    sort_order: body.sort_order ?? current.sort_order,
    show_on_entry: body.show_on_entry ?? current.show_on_entry,
  }
  groups[index] = next
  await saveGuestTagGroups(groups)
  return next
}

export async function deleteGuestTagGroup(groupId: string): Promise<void> {
  const groups = (await guestDbGet<TagGroupPublic[]>(KEYS.tagGroups)) ?? []
  await saveGuestTagGroups(groups.filter((group) => group.id !== groupId))
}

export async function reorderGuestTagGroups(orderedIds: string[]): Promise<TagGroupListResponse> {
  const groups = (await guestDbGet<TagGroupPublic[]>(KEYS.tagGroups)) ?? []
  const byId = new Map(groups.map((group) => [group.id, group]))
  const reordered = orderedIds
    .map((id, sortOrder) => {
      const group = byId.get(id)
      return group ? { ...group, sort_order: sortOrder } : null
    })
    .filter(Boolean) as TagGroupPublic[]
  await saveGuestTagGroups(reordered)
  return listGuestTagGroups()
}

export async function createGuestTag(
  groupId: string,
  body: TagWrite,
  locale: ApiLocale = 'en',
): Promise<TagPublic> {
  const groups = (await guestDbGet<TagGroupPublic[]>(KEYS.tagGroups)) ?? []
  const index = groups.findIndex((group) => group.id === groupId)
  if (index < 0) {
    throw new Error('Tag group not found')
  }
  const group = groups[index]
  const tag: TagPublic = {
    id: newId(),
    slug: body.slug ?? guestSlug('tag'),
    label: labelFrom(body.labels, locale),
    labels: body.labels,
    group_id: groupId,
    sort_order: body.sort_order ?? group.tags.length,
    color: body.color ?? '#94a3b8',
    icon_type: body.icon_type ?? 'emoji',
    icon: body.icon ?? '🏷',
  }
  groups[index] = { ...group, tags: [...group.tags, tag] }
  await saveGuestTagGroups(groups)
  return tag
}

export async function patchGuestTag(
  groupId: string,
  tagId: string,
  body: TagPatch,
  locale: ApiLocale = 'en',
): Promise<TagPublic> {
  const groups = (await guestDbGet<TagGroupPublic[]>(KEYS.tagGroups)) ?? []
  const groupIndex = groups.findIndex((group) => group.id === groupId)
  if (groupIndex < 0) {
    throw new Error('Tag group not found')
  }
  const group = groups[groupIndex]
  const tagIndex = group.tags.findIndex((tag) => tag.id === tagId)
  if (tagIndex < 0) {
    throw new Error('Tag not found')
  }
  const current = group.tags[tagIndex]
  const next: TagPublic = {
    ...current,
    slug: body.slug ?? current.slug,
    labels: body.labels ?? current.labels,
    label: body.labels ? labelFrom(body.labels, locale) : current.label,
    sort_order: body.sort_order ?? current.sort_order,
    color: body.color ?? current.color,
    icon_type: body.icon_type ?? current.icon_type,
    icon: body.icon ?? current.icon,
  }
  const tags = [...group.tags]
  tags[tagIndex] = next
  groups[groupIndex] = { ...group, tags }
  await saveGuestTagGroups(groups)
  return next
}

export async function deleteGuestTag(groupId: string, tagId: string): Promise<void> {
  const groups = (await guestDbGet<TagGroupPublic[]>(KEYS.tagGroups)) ?? []
  const groupIndex = groups.findIndex((group) => group.id === groupId)
  if (groupIndex < 0) {
    throw new Error('Tag group not found')
  }
  const group = groups[groupIndex]
  groups[groupIndex] = { ...group, tags: group.tags.filter((tag) => tag.id !== tagId) }
  await saveGuestTagGroups(groups)
}

export async function reorderGuestTags(groupId: string, orderedIds: string[]): Promise<TagGroupPublic> {
  const groups = (await guestDbGet<TagGroupPublic[]>(KEYS.tagGroups)) ?? []
  const groupIndex = groups.findIndex((group) => group.id === groupId)
  if (groupIndex < 0) {
    throw new Error('Tag group not found')
  }
  const group = groups[groupIndex]
  const byId = new Map(group.tags.map((tag) => [tag.id, tag]))
  const tags = orderedIds
    .map((id, sortOrder) => {
      const tag = byId.get(id)
      return tag ? { ...tag, sort_order: sortOrder } : null
    })
    .filter(Boolean) as TagPublic[]
  const next = { ...group, tags }
  groups[groupIndex] = next
  await saveGuestTagGroups(groups)
  return next
}

export async function createGuestGoal(body: GoalWrite, locale: ApiLocale = 'en'): Promise<GoalPublic> {
  const goals = (await guestDbGet<GoalPublic[]>(KEYS.goals)) ?? []
  const goal: GoalPublic = {
    id: newId(),
    slug: body.slug ?? guestSlug('goal'),
    label: labelFrom(body.labels, locale),
    labels: body.labels,
    times_per_week: body.times_per_week,
    tracking_kind: body.tracking_kind ?? 'binary',
    target_amount: body.target_amount ?? null,
    unit: body.unit ?? null,
    partial_label: body.partial_label?.trim() || null,
    starts_on: body.starts_on,
    ends_on: body.ends_on ?? null,
    sort_order: body.sort_order ?? goals.length,
    show_on_entry: body.show_on_entry ?? true,
    show_in_stats: body.show_in_stats ?? true,
    color: body.color ?? '#60a5fa',
    icon_type: body.icon_type ?? 'emoji',
    icon: body.icon ?? '🎯',
    completed_this_week: 0,
    day_amount: 0,
    week_marks: [],
  }
  goals.push(goal)
  await saveGuestGoals(goals)
  return goal
}

export async function patchGuestGoal(
  goalId: string,
  body: GoalPatch,
  locale: ApiLocale = 'en',
): Promise<GoalPublic> {
  const goals = (await guestDbGet<GoalPublic[]>(KEYS.goals)) ?? []
  const index = goals.findIndex((goal) => goal.id === goalId)
  if (index < 0) {
    throw new Error('Goal not found')
  }
  const current = goals[index]
  const next: GoalPublic = {
    ...current,
    slug: body.slug ?? current.slug,
    labels: body.labels ?? current.labels,
    label: body.labels ? labelFrom(body.labels, locale) : current.label,
    times_per_week: body.times_per_week ?? current.times_per_week,
    tracking_kind: body.tracking_kind ?? current.tracking_kind,
    target_amount: body.target_amount === undefined ? current.target_amount : body.target_amount,
    unit: body.unit === undefined ? current.unit : body.unit,
    partial_label:
      body.partial_label === undefined ? current.partial_label : body.partial_label?.trim() || null,
    starts_on: body.starts_on ?? current.starts_on,
    ends_on: body.ends_on === undefined ? current.ends_on : body.ends_on,
    sort_order: body.sort_order ?? current.sort_order,
    show_on_entry: body.show_on_entry ?? current.show_on_entry,
    show_in_stats: body.show_in_stats ?? current.show_in_stats,
    color: body.color ?? current.color,
    icon_type: body.icon_type ?? current.icon_type,
    icon: body.icon ?? current.icon,
  }
  goals[index] = next
  await saveGuestGoals(goals)
  return next
}

async function updateGuestGoalCheckins(
  goalId: string,
  day: string,
  update: (checkins: Record<string, GoalCheckinLevel>) => void,
): Promise<GoalPublic> {
  const goals = (await guestDbGet<GuestGoal[]>(KEYS.goals)) ?? []
  const index = goals.findIndex((goal) => goal.id === goalId)
  if (index < 0) {
    throw new Error('Goal not found')
  }
  const checkins = { ...(goals[index].checkins ?? {}) }
  update(checkins)
  goals[index] = { ...goals[index], checkins }
  await saveGuestGoals(goals)
  const { items } = await listGuestGoals({ progressOn: day })
  return items.find((goal) => goal.id === goalId) ?? goals[index]
}

export function setGuestGoalCheckin(
  goalId: string,
  day: string,
  level: GoalCheckinLevel,
): Promise<GoalPublic> {
  return updateGuestGoalCheckins(goalId, day, (checkins) => {
    checkins[day] = level
  })
}

export function deleteGuestGoalCheckin(goalId: string, day: string): Promise<GoalPublic> {
  return updateGuestGoalCheckins(goalId, day, (checkins) => {
    delete checkins[day]
  })
}

export async function deleteGuestGoal(goalId: string): Promise<void> {
  const goals = (await guestDbGet<GoalPublic[]>(KEYS.goals)) ?? []
  await saveGuestGoals(goals.filter((goal) => goal.id !== goalId))
}

export async function reorderGuestGoals(orderedIds: string[]): Promise<GoalListResponse> {
  const goals = (await guestDbGet<GoalPublic[]>(KEYS.goals)) ?? []
  const byId = new Map(goals.map((goal) => [goal.id, goal]))
  const reordered = orderedIds
    .map((id, sortOrder) => {
      const goal = byId.get(id)
      return goal ? { ...goal, sort_order: sortOrder } : null
    })
    .filter(Boolean) as GoalPublic[]
  await saveGuestGoals(reordered)
  return listGuestGoals()
}

export async function patchGuestMoodPreferences(
  body: MoodPreferencesUpdate,
  locale: ApiLocale = 'en',
): Promise<MoodPreferencesPublic> {
  const current = await getGuestMoodPreferences(locale)
  const next: MoodPreferencesPublic = {
    ...current,
    use_historical_colors: body.use_historical_colors ?? current.use_historical_colors,
    show_streak: body.show_streak ?? current.show_streak,
    scores: { ...current.scores },
  }
  if ('composer_blocks' in body) {
    next.composer_blocks = body.composer_blocks ?? null
  }
  if (body.scores) {
    for (const [scoreKey, update] of Object.entries(body.scores)) {
      const existing = next.scores[scoreKey]
      if (!existing) continue
      next.scores[scoreKey] = {
        ...existing,
        ...(update.color !== undefined ? { color: update.color } : {}),
        ...(update.icon_type !== undefined ? { icon_type: update.icon_type } : {}),
        ...(update.icon !== undefined ? { icon: update.icon } : {}),
        ...(update.label !== undefined
          ? {
              label:
                update.label === ''
                  ? defaultMoodScoreLabel(Number(scoreKey), locale)
                  : update.label,
            }
          : {}),
      }
    }
  }
  await guestDbSet(KEYS.moodPreferences, next)
  await guestHeartbeatSync()
  return next
}

export async function createGuestNoteTemplate(
  body: NoteTemplateWrite,
  locale: ApiLocale = 'en',
): Promise<NoteTemplatePublic> {
  const templates = (await guestDbGet<NoteTemplatePublic[]>(KEYS.noteTemplates)) ?? []
  const template: NoteTemplatePublic = {
    id: newId(),
    slug: body.slug ?? guestSlug('template'),
    label: labelFrom(body.labels, locale),
    labels: body.labels,
    bodies: body.bodies,
    body: body.bodies[locale] ?? body.bodies.en ?? Object.values(body.bodies)[0] ?? '',
    sort_order: body.sort_order ?? templates.length,
  }
  templates.push(template)
  await saveGuestNoteTemplates(templates)
  return template
}

export async function patchGuestNoteTemplate(
  templateId: string,
  body: NoteTemplatePatch,
  locale: ApiLocale = 'en',
): Promise<NoteTemplatePublic> {
  const templates = (await guestDbGet<NoteTemplatePublic[]>(KEYS.noteTemplates)) ?? []
  const index = templates.findIndex((template) => template.id === templateId)
  if (index < 0) {
    throw new Error('Template not found')
  }
  const current = templates[index]
  const bodies = body.bodies ?? current.bodies
  const next: NoteTemplatePublic = {
    ...current,
    slug: body.slug ?? current.slug,
    labels: body.labels ?? current.labels,
    label: body.labels ? labelFrom(body.labels, locale) : current.label,
    bodies,
    body: bodies[locale] ?? bodies.en ?? Object.values(bodies)[0] ?? '',
    sort_order: body.sort_order ?? current.sort_order,
  }
  templates[index] = next
  await saveGuestNoteTemplates(templates)
  return next
}

export async function deleteGuestNoteTemplate(templateId: string): Promise<void> {
  const templates = (await guestDbGet<NoteTemplatePublic[]>(KEYS.noteTemplates)) ?? []
  await saveGuestNoteTemplates(templates.filter((template) => template.id !== templateId))
}

export async function reorderGuestNoteTemplates(
  orderedIds: string[],
): Promise<NoteTemplateListResponse> {
  const templates = (await guestDbGet<NoteTemplatePublic[]>(KEYS.noteTemplates)) ?? []
  const byId = new Map(templates.map((template) => [template.id, template]))
  const reordered = orderedIds
    .map((id, sortOrder) => {
      const template = byId.get(id)
      return template ? { ...template, sort_order: sortOrder } : null
    })
    .filter(Boolean) as NoteTemplatePublic[]
  await saveGuestNoteTemplates(reordered)
  return listGuestNoteTemplates()
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
    return {
      ...stored,
      composer_blocks: stored.composer_blocks ?? null,
      show_streak: stored.show_streak ?? true,
      use_historical_colors: stored.use_historical_colors ?? true,
    }
  }
  const scores = resolveMoodPreferences(null, locale)
  return {
    scores,
    use_historical_colors: true,
    show_streak: true,
    composer_blocks: null,
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
    score_emoji: defaultMoodScoreEmoji(entry.score),
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
    score_emoji: defaultMoodScoreEmoji(body.score),
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
  const contentChanged =
    body.score !== undefined ||
    body.recorded_at !== undefined ||
    body.note !== undefined ||
    body.tag_ids !== undefined ||
    body.goal_ids !== undefined ||
    body.goal_progress !== undefined
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
    score_emoji: defaultMoodScoreEmoji(body.score ?? current.score),
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
    updated_at: contentChanged ? nowIso() : current.updated_at,
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
  const goals = (await guestDbGet<GuestGoal[]>(KEYS.goals)) ?? []
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
      partial_label: goal.partial_label ?? null,
      starts_on: goal.starts_on,
      ends_on: goal.ends_on,
      sort_order: goal.sort_order,
      show_on_entry: goal.show_on_entry,
      show_in_stats: goal.show_in_stats,
      color: goal.color,
      icon_type: goal.icon_type,
      icon: goal.icon,
      checkins: goal.checkins ?? {},
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
