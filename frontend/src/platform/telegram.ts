export type TelegramThemeParams = {
  bg_color?: string
  text_color?: string
  hint_color?: string
  link_color?: string
  button_color?: string
  button_text_color?: string
  secondary_bg_color?: string
  header_bg_color?: string
  accent_text_color?: string
  section_bg_color?: string
  section_header_text_color?: string
  subtitle_text_color?: string
  destructive_text_color?: string
}

export type TelegramWebAppUser = {
  id: number
  first_name: string
  last_name?: string
  username?: string
  language_code?: string
  is_premium?: boolean
  photo_url?: string
}

export type TelegramBackButton = {
  isVisible: boolean
  show: () => void
  hide: () => void
  onClick: (callback: () => void) => void
  offClick: (callback: () => void) => void
}

export type TelegramWebApp = {
  initData: string
  initDataUnsafe: {
    query_id?: string
    user?: TelegramWebAppUser
    auth_date?: number
    hash?: string
    start_param?: string
  }
  version: string
  platform: string
  colorScheme: 'light' | 'dark'
  themeParams: TelegramThemeParams
  isExpanded: boolean
  viewportHeight: number
  viewportStableHeight: number
  headerColor: string
  backgroundColor: string
  isClosingConfirmationEnabled: boolean
  BackButton: TelegramBackButton
  ready: () => void
  expand: () => void
  close: () => void
  disableVerticalSwipes?: () => void
  requestFullscreen?: () => void
  onEvent: (eventType: string, callback: () => void) => void
  offEvent: (eventType: string, callback: () => void) => void
  setHeaderColor: (color: string) => void
  setBackgroundColor: (color: string) => void
}

declare global {
  interface Window {
    Telegram?: {
      WebApp?: TelegramWebApp
    }
  }
}

const THEME_VAR_MAP: Record<string, string> = {
  bg_color: '--tg-theme-bg-color',
  text_color: '--tg-theme-text-color',
  hint_color: '--tg-theme-hint-color',
  link_color: '--tg-theme-link-color',
  button_color: '--tg-theme-button-color',
  button_text_color: '--tg-theme-button-text-color',
  secondary_bg_color: '--tg-theme-secondary-bg-color',
  header_bg_color: '--tg-theme-header-bg-color',
  accent_text_color: '--tg-theme-accent-text-color',
}

export function getTelegramWebApp(): TelegramWebApp | null {
  const webApp = window.Telegram?.WebApp
  if (!webApp || typeof webApp.initData !== 'string' || webApp.initData.length === 0) {
    return null
  }
  return webApp
}

export function isTelegramMiniApp(): boolean {
  return getTelegramWebApp() !== null
}

export function getTelegramStartParam(): string | null {
  const webApp = getTelegramWebApp()
  if (!webApp) {
    return null
  }
  const fromInit = webApp.initDataUnsafe.start_param?.trim()
  if (fromInit) {
    return fromInit
  }
  const fromQuery = new URLSearchParams(window.location.search).get('tgWebAppStartParam')
  return fromQuery?.trim() || null
}

export function applyTelegramChrome(): void {
  const webApp = getTelegramWebApp()
  if (!webApp) {
    return
  }
  webApp.ready()
  webApp.expand()
  webApp.disableVerticalSwipes?.()
  document.documentElement.classList.add('is-telegram')
  applyTelegramTheme(webApp)
}

export function applyTelegramTheme(webApp?: TelegramWebApp | null): void {
  const instance = webApp ?? getTelegramWebApp()
  if (!instance) {
    return
  }
  const root = document.documentElement
  root.dataset.tgColorScheme = instance.colorScheme
  root.style.setProperty('--tg-viewport-stable-height', `${instance.viewportStableHeight}px`)
  for (const [key, cssVar] of Object.entries(THEME_VAR_MAP)) {
    const value = instance.themeParams[key as keyof TelegramThemeParams]
    if (value) {
      root.style.setProperty(cssVar, value)
    }
  }
  const bg = instance.themeParams.bg_color
  const header = instance.themeParams.header_bg_color || bg
  if (header) {
    try {
      instance.setHeaderColor(header)
    } catch {
      // Older clients reject some color tokens.
    }
  }
  if (bg) {
    try {
      instance.setBackgroundColor(bg)
    } catch {
      // ignore
    }
  }
}

export function subscribeTelegramTheme(onChange: () => void): () => void {
  const webApp = getTelegramWebApp()
  if (!webApp) {
    return () => undefined
  }
  const handler = () => {
    applyTelegramTheme(webApp)
    onChange()
  }
  webApp.onEvent('themeChanged', handler)
  webApp.onEvent('viewportChanged', handler)
  return () => {
    webApp.offEvent('themeChanged', handler)
    webApp.offEvent('viewportChanged', handler)
  }
}
