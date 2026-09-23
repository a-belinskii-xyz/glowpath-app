import { apiRequest } from './client'
import { apiLocaleHeaders } from '../lib/locale'
import type {
  AchievementListResponse,
  AchievementPublic,
  AchievementSummaryResponse,
} from '../types/achievement'

export function listAchievements(): Promise<AchievementListResponse> {
  return apiRequest<AchievementListResponse>('/v1/achievements', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function getAchievementsSummary(): Promise<AchievementSummaryResponse> {
  return apiRequest<AchievementSummaryResponse>('/v1/achievements/summary', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function markAchievementSeen(achievementId: string): Promise<AchievementPublic> {
  return apiRequest<AchievementPublic>(`/v1/achievements/${achievementId}/seen`, {
    method: 'POST',
    auth: true,
    headers: apiLocaleHeaders(),
  })
}
