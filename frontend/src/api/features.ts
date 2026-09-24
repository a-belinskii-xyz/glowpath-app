import { apiRequest } from './client'
import type { GuestFingerprintSignals } from '../lib/guestFingerprint'

export type FeatureBootstrapResponse = {
  visitor_id: string
  guest_local_diary: boolean
  cohort: string
  features?: {
    notifications?: boolean
  }
}

export function bootstrapFeatures(fingerprint: GuestFingerprintSignals): Promise<FeatureBootstrapResponse> {
  return apiRequest<FeatureBootstrapResponse>('/v1/features/bootstrap', {
    method: 'POST',
    body: { fingerprint },
  })
}
