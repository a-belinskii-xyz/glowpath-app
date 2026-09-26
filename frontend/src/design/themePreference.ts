import type { ColorScheme } from './colorScheme'

export type ThemePreference = 'system' | 'light' | 'dark'

export const THEME_PREFERENCES: readonly ThemePreference[] = ['system', 'light', 'dark']

// Mirrored in index.html so the first paint already has the right scheme.
const STORAGE_KEY = 'mood_tracker_theme'

const listeners = new Set<() => void>()

function isThemePreference(value: unknown): value is ThemePreference {
  return value === 'system' || value === 'light' || value === 'dark'
}

function readStoredPreference(): ThemePreference {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return isThemePreference(stored) ? stored : 'system'
  } catch {
    return 'system'
  }
}

let preference: ThemePreference = readStoredPreference()

export function getThemePreference(): ThemePreference {
  return preference
}

export function setThemePreference(next: ThemePreference): void {
  try {
    localStorage.setItem(STORAGE_KEY, next)
  } catch {
    // Storage can be unavailable (private mode); the in-memory value still applies.
  }
  if (next === preference) {
    return
  }
  preference = next
  for (const listener of listeners) {
    listener()
  }
}

export function subscribeThemePreference(onChange: () => void): () => void {
  listeners.add(onChange)
  return () => {
    listeners.delete(onChange)
  }
}

/** Explicit scheme picked by the user, or null when the platform decides. */
export function forcedColorScheme(): ColorScheme | null {
  return preference === 'system' ? null : preference
}
