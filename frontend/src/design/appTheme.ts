import { applyTelegramTheme, isTelegramMiniApp } from '../platform/telegram'
import type { ColorScheme } from './colorScheme'
import { forcedColorScheme, subscribeThemePreference } from './themePreference'

const SYSTEM_DARK_QUERY = '(prefers-color-scheme: dark)'

let initialized = false

function systemColorScheme(): ColorScheme {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return 'light'
  }
  return window.matchMedia(SYSTEM_DARK_QUERY).matches ? 'dark' : 'light'
}

/**
 * Resolve the user's theme preference onto `<html data-color-scheme>`.
 * Inside Telegram "system" follows the Telegram client theme; on the web it
 * follows the OS setting. Dark chrome tokens live in index.css.
 */
export function applyAppTheme(): void {
  if (typeof document === 'undefined') {
    return
  }
  if (isTelegramMiniApp()) {
    applyTelegramTheme()
    return
  }
  const scheme = forcedColorScheme() ?? systemColorScheme()
  const root = document.documentElement
  if (root.dataset.colorScheme !== scheme) {
    root.dataset.colorScheme = scheme
  }
}

export function initAppTheme(): void {
  applyAppTheme()
  if (initialized) {
    return
  }
  initialized = true
  subscribeThemePreference(applyAppTheme)
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    window.matchMedia(SYSTEM_DARK_QUERY).addEventListener('change', applyAppTheme)
  }
}
