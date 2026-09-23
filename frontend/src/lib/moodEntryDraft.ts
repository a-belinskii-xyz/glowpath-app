/** Client-only draft for an unfinished mood entry (localStorage for now). */

export type MoodEntryDraft = {
  score: number
  moodPicked: boolean
  recordedAtLocal: string
  note: string
  selectedTagIds: string[]
  selectedGoalIds: string[]
  selectedGoalAmounts: Record<string, number>
  updatedAt: number
}

const DRAFT_KEY_PREFIX = 'mood_tracker_entry_draft'

function draftStorageKey(userId: string, dateKey: string): string {
  return `${DRAFT_KEY_PREFIX}:${userId}:${dateKey}`
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string')
}

function isNumberRecord(value: unknown): value is Record<string, number> {
  return (
    isRecord(value) && Object.values(value).every((item) => typeof item === 'number' && Number.isFinite(item))
  )
}

function parseDraft(raw: string | null): MoodEntryDraft | null {
  if (raw == null) {
    return null
  }
  try {
    const parsed: unknown = JSON.parse(raw)
    if (!isRecord(parsed)) {
      return null
    }
    if (
      typeof parsed.score !== 'number' ||
      typeof parsed.moodPicked !== 'boolean' ||
      typeof parsed.recordedAtLocal !== 'string' ||
      typeof parsed.note !== 'string' ||
      !isStringArray(parsed.selectedTagIds) ||
      !isStringArray(parsed.selectedGoalIds) ||
      typeof parsed.updatedAt !== 'number'
    ) {
      return null
    }
    return {
      score: parsed.score,
      moodPicked: parsed.moodPicked,
      recordedAtLocal: parsed.recordedAtLocal,
      note: parsed.note,
      selectedTagIds: parsed.selectedTagIds,
      selectedGoalIds: parsed.selectedGoalIds,
      selectedGoalAmounts: isNumberRecord(parsed.selectedGoalAmounts)
        ? parsed.selectedGoalAmounts
        : {},
      updatedAt: parsed.updatedAt,
    }
  } catch {
    return null
  }
}

export function isMoodEntryDraftEmpty(draft: Omit<MoodEntryDraft, 'updatedAt'>): boolean {
  return (
    !draft.moodPicked &&
    draft.note.trim() === '' &&
    draft.selectedTagIds.length === 0 &&
    draft.selectedGoalIds.length === 0
  )
}

export function getMoodEntryDraft(userId: string, dateKey: string): MoodEntryDraft | null {
  return parseDraft(localStorage.getItem(draftStorageKey(userId, dateKey)))
}

export function setMoodEntryDraft(
  userId: string,
  dateKey: string,
  draft: Omit<MoodEntryDraft, 'updatedAt'>,
): void {
  const payload: MoodEntryDraft = { ...draft, updatedAt: Date.now() }
  localStorage.setItem(draftStorageKey(userId, dateKey), JSON.stringify(payload))
}

export function clearMoodEntryDraft(userId: string, dateKey: string): void {
  localStorage.removeItem(draftStorageKey(userId, dateKey))
}
