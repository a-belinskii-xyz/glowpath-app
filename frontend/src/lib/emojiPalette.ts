export type EmojiGroup = {
  id: string
  emojis: readonly string[]
}

/**
 * Mood emoji grouped by emotion band (awful → great).
 * Labels come from i18n via `moodPreferences.emojiGroup{Id}`.
 */
export const MOOD_EMOJI_GROUPS: readonly EmojiGroup[] = [
  { id: 'Awful', emojis: ['😢', '😭', '😰', '🥺'] },
  { id: 'Bad', emojis: ['😞', '😤', '🫠', '🤯'] },
  { id: 'Neutral', emojis: ['😐', '😑', '😴', '🤒'] },
  { id: 'Good', emojis: ['🙂', '😌', '😊', '🤗'] },
  { id: 'Great', emojis: ['😄', '🤩', '🥳', '😎'] },
] as const

/** Flat list for lookups / legacy callers. */
export const MOOD_EMOJI_OPTIONS: readonly string[] = MOOD_EMOJI_GROUPS.flatMap(
  (group) => group.emojis,
)

/** Goal / habit–oriented emoji, grouped by theme. */
export const GOAL_EMOJI_GROUPS: readonly EmojiGroup[] = [
  { id: 'Focus', emojis: ['🎯', '⭐', '✅', '✍️'] },
  { id: 'Energy', emojis: ['💪', '🔥', '🏃', '🌅'] },
  { id: 'Care', emojis: ['🌱', '🧘', '💧', '🥗', '😴'] },
  { id: 'Life', emojis: ['📚', '🧠', '❤️', '🎵', '🧹', '📱', '🚫'] },
] as const

export const GOAL_EMOJI_OPTIONS: readonly string[] = GOAL_EMOJI_GROUPS.flatMap(
  (group) => group.emojis,
)

/** Tag / context–oriented emoji, grouped by theme. */
export const TAG_EMOJI_GROUPS: readonly EmojiGroup[] = [
  { id: 'Weather', emojis: ['☀️', '🌤', '☁️', '🌧', '⛈', '❄️', '💨'] },
  { id: 'Body', emojis: ['😴', '😑', '😩', '😮‍💨', '🤒', '💪', '🧘'] },
  { id: 'Feel', emojis: ['😊', '😌', '😰', '😢', '🤩', '😐', '🤗'] },
  { id: 'Life', emojis: ['💼', '🏃', '💬', '🛋', '📖', '🍳', '🏠', '👥', '🏷'] },
] as const

export const TAG_EMOJI_OPTIONS: readonly string[] = TAG_EMOJI_GROUPS.flatMap(
  (group) => group.emojis,
)
