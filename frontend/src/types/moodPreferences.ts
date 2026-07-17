export type MoodScoreIconType = 'emoji' | 'builtin' | 'upload'

export type MoodScoreStylePublic = {
  color: string
  icon_type: MoodScoreIconType
  icon: string
  label: string
}

export type MoodPreferencesPublic = {
  scores: Record<string, MoodScoreStylePublic>
}

export type MoodScoreStyleUpdate = {
  color?: string
  icon_type?: MoodScoreIconType
  icon?: string
  /** Empty string clears a custom label and restores the locale default. */
  label?: string
}

export type MoodPreferencesUpdate = {
  scores: Record<string, MoodScoreStyleUpdate>
}
