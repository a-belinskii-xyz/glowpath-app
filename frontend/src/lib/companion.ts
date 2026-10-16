/** Time-of-day bins for companion copy. Finer than insight analytics bins. */
export const COMPANION_DAYPARTS = [
  'lateNight',
  'morning',
  'midday',
  'afternoon',
  'evening',
  'night',
] as const

export type CompanionDaypart = (typeof COMPANION_DAYPARTS)[number]

export const COMPANION_SLOTS = [
  'greeting',
  'kicker',
  'howAreYou',
  'pickMoodHint',
  'whatsOnYourMind',
  'notePlaceholder',
  'whatHappened',
  'contextLead',
  'goals',
  'emptyMonth',
  'emptyPrompt',
] as const

export type CompanionSlot = (typeof COMPANION_SLOTS)[number]

export const COMPANION_VARIANT_COUNTS: Record<CompanionSlot, number> = {
  greeting: 3,
  kicker: 2,
  howAreYou: 3,
  pickMoodHint: 2,
  whatsOnYourMind: 2,
  notePlaceholder: 2,
  whatHappened: 2,
  contextLead: 2,
  goals: 2,
  emptyMonth: 2,
  emptyPrompt: 2,
}

const SLOT_FALLBACK: Record<CompanionSlot, string> = {
  greeting: 'home.lead',
  kicker: 'entries.pickMoodHint',
  howAreYou: 'entries.howAreYouFeeling',
  pickMoodHint: 'entries.pickMoodHint',
  whatsOnYourMind: 'entries.whatsOnYourMind',
  notePlaceholder: 'entries.notePlaceholder',
  whatHappened: 'entries.whatHappenedToday',
  contextLead: 'entries.contextLead',
  goals: 'entries.goalsToday',
  emptyMonth: 'entries.noEntriesThisMonth',
  emptyPrompt: 'emotionStats.emptyPrompt',
}

/** Map a local hour (0–23) to a companion daypart. */
export function companionDaypartForHour(hour: number): CompanionDaypart {
  const normalized = hour === 24 ? 0 : hour
  if (normalized < 5) {
    return 'lateNight'
  }
  if (normalized < 11) {
    return 'morning'
  }
  if (normalized < 14) {
    return 'midday'
  }
  if (normalized < 17) {
    return 'afternoon'
  }
  if (normalized < 21) {
    return 'evening'
  }
  return 'night'
}

export function pickCompanionVariant(seed: string, count: number): number {
  if (count <= 1) {
    return 0
  }
  let hash = 2166136261
  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0) % count
}

type Translate = (key: string, params?: Record<string, string | number>) => string

/** Slots with one extra phrasing that addresses the user by name (GP-57). */
const NAMED_SLOTS: ReadonlySet<CompanionSlot> = new Set(['greeting', 'howAreYou'])

export function companionLine(
  t: Translate,
  slot: CompanionSlot,
  daypart: CompanionDaypart,
  seed: string,
  name?: string | null,
): string {
  // With a name, the named phrasing joins the pool, so it shows up some days, not every day.
  const withName = Boolean(name) && NAMED_SLOTS.has(slot)
  const baseCount = COMPANION_VARIANT_COUNTS[slot]
  const count = baseCount + (withName ? 1 : 0)
  const variant = pickCompanionVariant(`${seed}:${slot}:${daypart}`, count)
  if (withName && variant === baseCount) {
    return t(`companion.${slot}Named.${daypart}`, { name: name ?? '' })
  }
  const key = `companion.${slot}.${daypart}.${variant}`
  const value = t(key)
  return value === key ? t(SLOT_FALLBACK[slot]) : value
}

export function companionMoodPhrase(
  t: Translate,
  daypart: CompanionDaypart,
  score: number,
): string {
  const key = `companion.moodPhrase.${daypart}.${score}`
  const value = t(key)
  return value === key ? t(`entries.moodPhrase.${score}`) : value
}
