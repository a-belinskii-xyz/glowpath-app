export const SUPPORTED_LOCALES = ['en', 'ru'] as const

export type ApiLocale = (typeof SUPPORTED_LOCALES)[number]

export const DEFAULT_LOCALE: ApiLocale = 'en'

const LOCALE_STORAGE_KEY = 'mood_tracker_locale'

export const LOCALE_OPTIONS: { value: ApiLocale; label: string }[] = [
  { value: 'en', label: 'English' },
  { value: 'ru', label: 'Русский' },
]

export function isApiLocale(value: string): value is ApiLocale {
  return (SUPPORTED_LOCALES as readonly string[]).includes(value)
}

export function normalizeLocale(value: string): ApiLocale {
  const primary = value.split(',')[0]?.split(';')[0]?.trim().toLowerCase() ?? ''
  const language = primary.includes('-') ? (primary.split('-')[0] ?? primary) : primary
  return isApiLocale(language) ? language : DEFAULT_LOCALE
}

export function detectBrowserLocale(): ApiLocale {
  if (typeof navigator === 'undefined') {
    return DEFAULT_LOCALE
  }
  const candidates = navigator.languages?.length ? navigator.languages : [navigator.language]
  for (const candidate of candidates) {
    if (!candidate) continue
    const primary = candidate.split(',')[0]?.split(';')[0]?.trim().toLowerCase() ?? ''
    const subtag = primary.includes('-') ? (primary.split('-')[0] ?? primary) : primary
    if (isApiLocale(subtag)) {
      return subtag
    }
  }
  return DEFAULT_LOCALE
}

function readStoredLocale(): ApiLocale | null {
  const stored = localStorage.getItem(LOCALE_STORAGE_KEY)
  if (stored && isApiLocale(stored)) {
    return stored
  }
  return null
}

function detectTelegramLocale(): ApiLocale | null {
  if (typeof window === 'undefined') {
    return null
  }
  const webApp = window.Telegram?.WebApp
  if (!webApp?.initData) {
    return null
  }
  const code = webApp.initDataUnsafe.user?.language_code
  if (!code) {
    return null
  }
  return normalizeLocale(code)
}

/** Current API/UI content locale. Persisted preference, else Telegram, else browser. */
export function getApiLocale(): ApiLocale {
  return readStoredLocale() ?? detectTelegramLocale() ?? detectBrowserLocale()
}

export function setApiLocale(locale: ApiLocale): void {
  localStorage.setItem(LOCALE_STORAGE_KEY, locale)
}

export function apiLocaleHeaders(): Record<string, string> {
  return { 'Accept-Language': getApiLocale() }
}
