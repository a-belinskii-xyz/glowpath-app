import { apiRequest } from './client'

export function sendGuestHeartbeat(body: {
  visitor_id: string
  timezone?: string
  locale?: string
  entry_count: number
  onboarding_completed: boolean
}): Promise<{ ok: boolean }> {
  return apiRequest<{ ok: boolean }>('/v1/guest/heartbeat', {
    method: 'POST',
    body,
  })
}

export function importGuestDiary(body: {
  visitor_id: string
  payload: Record<string, unknown>
}): Promise<{ imported_entries: number; skipped: boolean }> {
  return apiRequest<{ imported_entries: number; skipped: boolean }>('/v1/guest/import', {
    method: 'POST',
    body,
    auth: true,
  })
}

export function getGuestExperimentSummary(): Promise<Record<string, number | null>> {
  return apiRequest<Record<string, number | null>>('/v1/guest/experiment/summary', {
    auth: true,
  })
}
