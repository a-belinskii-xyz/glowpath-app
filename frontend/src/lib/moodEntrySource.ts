/** Attribution ``{channel}:{kind}`` matching backend (analytics only). */
export const MOOD_ENTRY_SOURCE_CHANNELS = ['email', 'telegram'] as const
export const MOOD_ENTRY_ATTRIBUTION_KINDS = ['daily_mood_reminder', 'goal_reminder'] as const

export type MoodEntrySourceChannel = (typeof MOOD_ENTRY_SOURCE_CHANNELS)[number]
export type MoodEntryAttributionKind = (typeof MOOD_ENTRY_ATTRIBUTION_KINDS)[number]
/** e.g. ``email:daily_mood_reminder`` */
export type MoodEntrySource = `${MoodEntrySourceChannel}:${MoodEntryAttributionKind}`

const SESSION_SOURCE_KEY = 'mood_tracker_entry_source'

export function parseMoodEntrySource(raw: string | null): MoodEntrySource | undefined {
  if (raw == null) {
    return undefined
  }
  const sep = raw.indexOf(':')
  if (sep <= 0 || sep !== raw.lastIndexOf(':')) {
    return undefined
  }
  const channel = raw.slice(0, sep)
  const kind = raw.slice(sep + 1)
  if (
    !(MOOD_ENTRY_SOURCE_CHANNELS as readonly string[]).includes(channel) ||
    !(MOOD_ENTRY_ATTRIBUTION_KINDS as readonly string[]).includes(kind)
  ) {
    return undefined
  }
  return raw as MoodEntrySource
}

/** Persist attribution for the browser tab session (survives in-app navigation). */
export function setStoredMoodEntrySource(source: MoodEntrySource): void {
  sessionStorage.setItem(SESSION_SOURCE_KEY, source)
}

export function getStoredMoodEntrySource(): MoodEntrySource | undefined {
  return parseMoodEntrySource(sessionStorage.getItem(SESSION_SOURCE_KEY))
}

export function clearStoredMoodEntrySource(): void {
  sessionStorage.removeItem(SESSION_SOURCE_KEY)
}
