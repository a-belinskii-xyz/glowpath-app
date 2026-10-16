import { apiRequest } from './client'
import { getThemePreference } from '../design/themePreference'
import { isGuestDiaryMode } from '../lib/guestMode'
import { getApiLocale } from '../lib/locale'
import { completeGuestOnboarding } from '../guest/store'
import type { UserPublic } from '../types/auth'
import type {
  OnboardingCatalog,
  OnboardingCompleteRequest,
  OnboardingSuggestions,
} from '../types/onboarding'

export function getOnboardingCatalog(): Promise<OnboardingCatalog> {
  return apiRequest<OnboardingCatalog>('/v1/onboarding/catalog')
}

export function getOnboardingSuggestions(optionKeys: string[]): Promise<OnboardingSuggestions> {
  return apiRequest<OnboardingSuggestions>('/v1/onboarding/suggestions', {
    method: 'POST',
    body: { option_keys: optionKeys },
  })
}

export async function completeOnboarding(body: OnboardingCompleteRequest): Promise<UserPublic> {
  if (isGuestDiaryMode()) {
    await completeGuestOnboarding({
      skip: Boolean(body.skip),
      suggestions: body.skip
        ? null
        : await getOnboardingSuggestions(body.option_keys ?? []),
      selectedGroupSlugs: body.tag_group_slugs,
      selectedTemplateSlugs: body.note_template_slugs,
    })
    return {
      id: 'guest',
      email: '',
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      email_verified: false,
      email_verified_at: null,
      onboarding_completed: true,
      onboarding_completed_at: new Date().toISOString(),
      has_password: false,
      theme_preference: getThemePreference(),
      time_format: 'auto',
      display_name: null,
      locale: getApiLocale(),
      telegram_linked: false,
      can_unlink_telegram: false,
      features: {},
      plan: 'free',
      entitlements: [],
    }
  }
  return apiRequest<UserPublic>('/v1/onboarding/complete', {
    method: 'POST',
    body,
    auth: true,
  })
}
