import { apiRequest } from './client'
import { apiLocaleHeaders } from '../lib/locale'
import type { MoodPreferencesPublic, MoodPreferencesUpdate } from '../types/moodPreferences'

export function getMoodPreferences(): Promise<MoodPreferencesPublic> {
  return apiRequest<MoodPreferencesPublic>('/v1/mood-preferences', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function patchMoodPreferences(
  body: MoodPreferencesUpdate,
): Promise<MoodPreferencesPublic> {
  return apiRequest<MoodPreferencesPublic>('/v1/mood-preferences', {
    method: 'PATCH',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}
