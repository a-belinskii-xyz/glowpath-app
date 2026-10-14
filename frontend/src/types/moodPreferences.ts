export type MoodScoreIconType = 'emoji' | 'builtin' | 'upload' | 'catalog'

export type MoodScoreStylePublic = {
  color: string
  icon_type: MoodScoreIconType
  icon: string
  label: string
}

export type ComposerBlockPreference = {
  id: string
  enabled: boolean
}

export type MoodPreferencesPublic = {
  scores: Record<string, MoodScoreStylePublic>
  use_historical_colors: boolean
  show_streak: boolean
  /** GP-45: fold the calendar weeks before the user's own start. */
  calendar_from_start: boolean
  /** null = start from the first entry. */
  calendar_start_on: string | null
  /** Local date of the first entry. */
  first_entry_on: string | null
  /** null = user never customized layout; frontend resolves registry defaults. */
  composer_blocks: ComposerBlockPreference[] | null
}

export type MoodScoreStyleUpdate = {
  color?: string
  icon_type?: MoodScoreIconType
  icon?: string
  /** Empty string clears a custom label and restores the locale default. */
  label?: string
}

export type MoodPreferencesUpdate = {
  scores?: Record<string, MoodScoreStyleUpdate>
  use_historical_colors?: boolean
  show_streak?: boolean
  calendar_from_start?: boolean
  calendar_start_on?: string | null
  composer_blocks?: ComposerBlockPreference[] | null
}
