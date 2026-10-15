import { apiRequest } from './client'
import { isGuestDiaryMode } from '../lib/guestMode'
import type { BodySettings, FoodLog, Meal, WeightPoint } from '../types/body'

const DEFAULT_SETTINGS: BodySettings = {
  show_weight: false,
  show_food: false,
  hide_weight: false,
  food_goal_ids: [],
}

/** Weight and food live on the server only; the guest diary never shows them. */
export function getBodySettings(): Promise<BodySettings> {
  if (isGuestDiaryMode()) return Promise.resolve(DEFAULT_SETTINGS)
  return apiRequest<BodySettings>('/v1/body/settings', { auth: true })
}

export function updateBodySettings(body: Partial<BodySettings>): Promise<BodySettings> {
  return apiRequest<BodySettings>('/v1/body/settings', { method: 'PATCH', auth: true, body })
}

export async function listWeights(from: string, to: string): Promise<WeightPoint[]> {
  const query = new URLSearchParams({ from, to })
  const response = await apiRequest<{ items: WeightPoint[] }>(`/v1/body/weight?${query}`, {
    auth: true,
  })
  return response.items
}

export function setWeight(day: string, value: number): Promise<WeightPoint> {
  return apiRequest<WeightPoint>(`/v1/body/weight/${day}`, {
    method: 'PUT',
    auth: true,
    body: { value },
  })
}

export function deleteWeight(day: string): Promise<void> {
  return apiRequest<void>(`/v1/body/weight/${day}`, { method: 'DELETE', auth: true })
}

export async function listFood(from: string, to: string): Promise<FoodLog[]> {
  const query = new URLSearchParams({ from, to })
  const response = await apiRequest<{ items: FoodLog[] }>(`/v1/body/food?${query}`, { auth: true })
  return response.items
}

export function createFood(body: { day: string; meal: Meal | null; text: string }): Promise<FoodLog> {
  return apiRequest<FoodLog>('/v1/body/food', { method: 'POST', auth: true, body })
}

export function updateFood(id: string, body: { meal: Meal | null; text: string }): Promise<FoodLog> {
  return apiRequest<FoodLog>(`/v1/body/food/${id}`, { method: 'PATCH', auth: true, body })
}

export function deleteFood(id: string): Promise<void> {
  return apiRequest<void>(`/v1/body/food/${id}`, { method: 'DELETE', auth: true })
}
