/** Known default / seed group slugs → emoji for section legends on the entry form. */
const GROUP_EMOJI_BY_SLUG: Record<string, string> = {
  weather: '🌤',
  sleep_quality: '😴',
  mood: '💭',
  activity: '⚡️',
  hobbies: '🎨',
  people: '👥',
  location: '📍',
  energy: '🔋',
  focus: '🎯',
  food: '🍽',
  health: '💚',
  media: '🎬',
  travel: '✈️',
  projects: '🧩',
  nature: '🌿',
}

export function emojiForGroupSlug(slug: string): string | null {
  return GROUP_EMOJI_BY_SLUG[slug] ?? null
}
