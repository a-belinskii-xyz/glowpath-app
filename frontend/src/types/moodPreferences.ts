export type MoodScoreIconType = 'emoji' | 'builtin' | 'upload'

export type MoodScoreStylePublic = {
  color: string
  icon_type: MoodScoreIconType
  icon: string
}

export type MoodPreferencesPublic = {
  scores: Record<string, MoodScoreStylePublic>
}

export type MoodScoreStyleUpdate = {
  color?: string
  icon_type?: MoodScoreIconType
  icon?: string
}

export type MoodPreferencesUpdate = {
  scores: Record<string, MoodScoreStyleUpdate>
}
