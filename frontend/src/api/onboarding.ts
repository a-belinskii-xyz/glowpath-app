import { apiRequest } from './client'
import type { UserPublic } from '../types/auth'
import type {
  OnboardingCatalog,
  OnboardingCompleteRequest,
  OnboardingSuggestions,
} from '../types/onboarding'

export function getOnboardingCatalog(): Promise<OnboardingCatalog> {
  return apiRequest<OnboardingCatalog>('/v1/onboarding/catalog', { auth: true })
}

export function getOnboardingSuggestions(optionKeys: string[]): Promise<OnboardingSuggestions> {
  return apiRequest<OnboardingSuggestions>('/v1/onboarding/suggestions', {
    method: 'POST',
    body: { option_keys: optionKeys },
    auth: true,
  })
}

export function completeOnboarding(body: OnboardingCompleteRequest): Promise<UserPublic> {
  return apiRequest<UserPublic>('/v1/onboarding/complete', {
    method: 'POST',
    body,
    auth: true,
  })
}
