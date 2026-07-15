import { apiRequest } from './client'
import { apiLocaleHeaders } from '../lib/locale'
import type {
  GoalListResponse,
  GoalPatch,
  GoalPublic,
  GoalReorderRequest,
  GoalWrite,
} from '../types/goal'

export function listGoals(): Promise<GoalListResponse> {
  return apiRequest<GoalListResponse>('/v1/goals', {
    auth: true,
    headers: apiLocaleHeaders(),
  })
}

export function createGoal(body: GoalWrite): Promise<GoalPublic> {
  return apiRequest<GoalPublic>('/v1/goals', {
    method: 'POST',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function patchGoal(goalId: string, body: GoalPatch): Promise<GoalPublic> {
  return apiRequest<GoalPublic>(`/v1/goals/${goalId}`, {
    method: 'PATCH',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}

export function deleteGoal(goalId: string): Promise<void> {
  return apiRequest<void>(`/v1/goals/${goalId}`, {
    method: 'DELETE',
    auth: true,
  })
}

export function reorderGoals(body: GoalReorderRequest): Promise<GoalListResponse> {
  return apiRequest<GoalListResponse>('/v1/goals/reorder', {
    method: 'PUT',
    auth: true,
    headers: apiLocaleHeaders(),
    body,
  })
}
