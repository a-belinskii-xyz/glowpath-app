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

export type TelegramMainButton = {
  text: string
  color: string
  textColor: string
  isVisible: boolean
  isActive: boolean
  isProgressVisible: boolean
  setText: (text: string) => void
  onClick: (callback: () => void) => void
  offClick: (callback: () => void) => void
  show: () => void
  hide: () => void
  enable: () => void
  disable: () => void
  showProgress: (leaveActive?: boolean) => void
  hideProgress: () => void
  setParams: (params: {
    text?: string
    color?: string
    text_color?: string
    is_active?: boolean
    is_visible?: boolean
  }) => void
}

export type TelegramBackButton = {
  isVisible: boolean
  show: () => void
  hide: () => void
  onClick: (callback: () => void) => void
  offClick: (callback: () => void) => void
}

export type TelegramSafeAreaInset = {
  top: number
  bottom: number
  left: number
  right: number
}

export type TelegramHapticFeedback = {
  impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void
  notificationOccurred: (type: 'error' | 'success' | 'warning') => void
  selectionChanged: () => void
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
  MainButton?: TelegramMainButton
  HapticFeedback?: TelegramHapticFeedback
  safeAreaInset?: TelegramSafeAreaInset
  contentSafeAreaInset?: TelegramSafeAreaInset
  ready: () => void
  expand: () => void
  close: () => void
  disableVerticalSwipes?: () => void
  requestFullscreen?: () => void
  onEvent: (eventType: string, callback: (...args: unknown[]) => void) => void
  offEvent: (eventType: string, callback: (...args: unknown[]) => void) => void
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
  section_bg_color: '--tg-theme-section-bg-color',
}

const DARK_FALLBACK = {
  bg: '#0e1621',
  text: '#f1f5f9',
  hint: '#94a3b8',
  surface: '#17212b',
  button: '#5288c1',
  buttonText: '#ffffff',
  inverse: '#0f172a',
} as const

const LIGHT_FALLBACK = {
  bg: '#eef1f6',
  text: '#1f2937',
  hint: '#6b7280',
  surface: '#ffffff',
  button: '#2563eb',
  buttonText: '#ffffff',
  inverse: '#ffffff',
} as const

const MIN_VIEWPORT_HEIGHT_PX = 120
const MAX_SAFE_AREA_PX = 160
const MIN_TEXT_CONTRAST = 3

let chromeReady = false
let lastLayoutKey = ''
let lastThemeKey = ''
let lastHeaderColor: string | null = null
let lastBackgroundColor: string | null = null

type Rgb = { r: number; g: number; b: number }

function parseHexColor(value: string | undefined): Rgb | null {
  if (!value) {
    return null
  }
  const hex = value.trim().replace(/^#/, '')
  if (/^[0-9a-fA-F]{3}$/.test(hex)) {
    return {
      r: Number.parseInt(hex[0] + hex[0], 16),
      g: Number.parseInt(hex[1] + hex[1], 16),
      b: Number.parseInt(hex[2] + hex[2], 16),
    }
  }
  if (/^[0-9a-fA-F]{6}$/.test(hex)) {
    return {
      r: Number.parseInt(hex.slice(0, 2), 16),
      g: Number.parseInt(hex.slice(2, 4), 16),
      b: Number.parseInt(hex.slice(4, 6), 16),
    }
  }
  return null
}

function hexFromRgb(rgb: Rgb): string {
  const toHex = (channel: number) =>
    Math.max(0, Math.min(255, Math.round(channel)))
      .toString(16)
      .padStart(2, '0')
  return `#${toHex(rgb.r)}${toHex(rgb.g)}${toHex(rgb.b)}`
}

function normalizeHex(value: string | undefined): string | null {
  const rgb = parseHexColor(value)
  return rgb ? hexFromRgb(rgb) : null
}

function relativeLuminance(value: string): number | null {
  const rgb = parseHexColor(value)
  if (!rgb) {
    return null
  }
  const toLinear = (channel: number) => {
    const scaled = channel / 255
    return scaled <= 0.03928 ? scaled / 12.92 : ((scaled + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * toLinear(rgb.r) + 0.7152 * toLinear(rgb.g) + 0.0722 * toLinear(rgb.b)
}

function isLightColor(value: string | undefined, fallback = true): boolean {
  const luminance = value ? relativeLuminance(value) : null
  if (luminance == null) {
    return fallback
  }
  return luminance > 0.45
}

function contrastRatio(foreground: string, background: string): number | null {
  const left = relativeLuminance(foreground)
  const right = relativeLuminance(background)
  if (left == null || right == null) {
    return null
  }
  const lighter = Math.max(left, right)
  const darker = Math.min(left, right)
  return (lighter + 0.05) / (darker + 0.05)
}

function hasUsableContrast(foreground: string, background: string): boolean {
  const ratio = contrastRatio(foreground, background)
  return ratio != null && ratio >= MIN_TEXT_CONTRAST
}

function mixHex(left: string, right: string, amount: number): string {
  const start = parseHexColor(left)
  const end = parseHexColor(right)
  if (!start || !end) {
    return left
  }
  return hexFromRgb({
    r: start.r + (end.r - start.r) * amount,
    g: start.g + (end.g - start.g) * amount,
    b: start.b + (end.b - start.b) * amount,
  })
}

function pickContrastingColor(
  candidate: string | undefined,
  background: string,
  fallback: string,
): string {
  const color = normalizeHex(candidate)
  if (color && hasUsableContrast(color, background)) {
    return color
  }
  return fallback
}

function pickSurfaceColor(
  candidate: string | undefined,
  text: string,
  background: string,
  dark: boolean,
): string {
  const color = normalizeHex(candidate)
  if (color && hasUsableContrast(text, color) && isLightColor(color, !dark) === !dark) {
    return color
  }
  const derived = dark ? mixHex(background, '#ffffff', 0.1) : LIGHT_FALLBACK.surface
  if (hasUsableContrast(text, derived)) {
    return derived
  }
  return dark ? DARK_FALLBACK.surface : LIGHT_FALLBACK.surface
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

function cssPx(value: number | undefined): string {
  if (!Number.isFinite(value)) {
    return '0px'
  }
  return `${Math.max(0, Math.min(MAX_SAFE_AREA_PX, value ?? 0))}px`
}

function applyTelegramSafeArea(webApp: TelegramWebApp): void {
  const root = document.documentElement
  const safe = webApp.safeAreaInset
  const content = webApp.contentSafeAreaInset
  if (safe) {
    root.style.setProperty('--tg-safe-top', cssPx(safe.top))
    root.style.setProperty('--tg-safe-bottom', cssPx(safe.bottom))
    root.style.setProperty('--tg-safe-left', cssPx(safe.left))
    root.style.setProperty('--tg-safe-right', cssPx(safe.right))
  }
  if (content) {
    root.style.setProperty('--tg-content-safe-top', cssPx(content.top))
    root.style.setProperty('--tg-content-safe-bottom', cssPx(content.bottom))
  }
}

function applyTelegramLayout(webApp: TelegramWebApp): void {
  const root = document.documentElement
  const height = webApp.viewportStableHeight
  const safe = webApp.safeAreaInset
  const content = webApp.contentSafeAreaInset
  const key = [
    height,
    safe?.top,
    safe?.bottom,
    safe?.left,
    safe?.right,
    content?.top,
    content?.bottom,
  ].join('|')
  if (key === lastLayoutKey) {
    return
  }
  lastLayoutKey = key
  if (Number.isFinite(height) && height >= MIN_VIEWPORT_HEIGHT_PX) {
    root.style.setProperty('--tg-viewport-stable-height', `${Math.round(height)}px`)
  }
  applyTelegramSafeArea(webApp)
}

function applyChromeTokens(root: HTMLElement, dark: boolean, tokens: {
  bg: string
  text: string
  hint: string
  surface: string
  elevated: string
  inset: string
  button: string
  buttonHover: string
  inverse: string
}): void {
  root.style.setProperty('--chrome-bg-app', tokens.bg)
  root.style.setProperty('--chrome-text-primary', tokens.text)
  root.style.setProperty('--chrome-text-secondary', tokens.hint)
  root.style.setProperty('--chrome-text-inverse', tokens.inverse)
  root.style.setProperty('--chrome-surface', tokens.surface)
  root.style.setProperty('--chrome-surface-elevated', tokens.elevated)
  root.style.setProperty('--chrome-surface-inset', tokens.inset)
  root.style.setProperty(
    '--chrome-surface-glass',
    `color-mix(in oklab, ${tokens.surface} 78%, transparent)`,
  )
  root.style.setProperty(
    '--chrome-border-subtle',
    `color-mix(in oklab, ${tokens.text} 10%, transparent)`,
  )
  root.style.setProperty(
    '--chrome-border-default',
    `color-mix(in oklab, ${tokens.text} 16%, transparent)`,
  )
  root.style.setProperty(
    '--chrome-border-strong',
    `color-mix(in oklab, ${tokens.text} 24%, transparent)`,
  )
  root.style.setProperty('--chrome-action-primary', tokens.button)
  root.style.setProperty('--chrome-action-primary-hover', tokens.buttonHover)
  root.style.setProperty(
    '--chrome-shadow-soft',
    dark ? '0 8px 28px rgb(0 0 0 / 32%)' : '0 8px 28px rgb(15 23 42 / 6%)',
  )
  root.style.colorScheme = dark ? 'dark' : 'light'
}

function applyNativeChrome(instance: TelegramWebApp, header: string, background: string): void {
  if (header !== lastHeaderColor) {
    lastHeaderColor = header
    try {
      instance.setHeaderColor(header)
    } catch {
      // Older clients reject some color tokens.
    }
  }
  if (background !== lastBackgroundColor) {
    lastBackgroundColor = background
    try {
      instance.setBackgroundColor(background)
    } catch {
      // ignore
    }
  }
}

export function applyTelegramChrome(): void {
  const webApp = getTelegramWebApp()
  if (!webApp) {
    return
  }
  if (!chromeReady) {
    webApp.ready()
    if (!webApp.isExpanded) {
      webApp.expand()
    }
    webApp.disableVerticalSwipes?.()
    chromeReady = true
  }
  applyTelegramTheme(webApp)
  document.documentElement.classList.add('is-telegram')
}

export function applyTelegramTheme(webApp?: TelegramWebApp | null): void {
  const instance = webApp ?? getTelegramWebApp()
  if (!instance) {
    return
  }
  const root = document.documentElement
  const theme = instance.themeParams
  const themeBg = normalizeHex(theme.bg_color)
  const dark =
    instance.colorScheme === 'dark' || (themeBg != null && !isLightColor(themeBg, false))
  const fallback = dark ? DARK_FALLBACK : LIGHT_FALLBACK
  const bg = themeBg ?? fallback.bg
  const text = pickContrastingColor(theme.text_color, bg, fallback.text)
  const surface = pickSurfaceColor(
    theme.secondary_bg_color || theme.section_bg_color,
    text,
    bg,
    dark,
  )
  const hint = pickContrastingColor(theme.hint_color, surface, fallback.hint)
  const elevated = pickSurfaceColor(
    theme.section_bg_color,
    text,
    mixHex(surface, dark ? '#ffffff' : '#0f172a', dark ? 0.06 : 0.04),
    dark,
  )
  const inset = dark ? mixHex(bg, surface, 0.45) : mixHex(surface, '#e5e7eb', 0.55)
  const button = normalizeHex(theme.button_color) ?? fallback.button
  const inverse = pickContrastingColor(theme.button_text_color, button, fallback.buttonText)
  const header = normalizeHex(theme.header_bg_color) ?? bg
  const themeKey = [dark, bg, text, hint, surface, elevated, inset, button, inverse, header].join('|')

  applyTelegramLayout(instance)
  if (themeKey === lastThemeKey) {
    return
  }
  lastThemeKey = themeKey

  root.dataset.tgColorScheme = dark ? 'dark' : 'light'
  for (const [key, cssVar] of Object.entries(THEME_VAR_MAP)) {
    const value = theme[key as keyof TelegramThemeParams]
    if (value) {
      root.style.setProperty(cssVar, value)
    }
  }
  applyChromeTokens(root, dark, {
    bg,
    text,
    hint,
    surface,
    elevated,
    inset,
    button,
    buttonHover: mixHex(button, dark ? '#ffffff' : '#0f172a', 0.12),
    inverse,
  })
  applyNativeChrome(instance, header, bg)
}

export function subscribeTelegramTheme(onChange: () => void): () => void {
  const webApp = getTelegramWebApp()
  if (!webApp) {
    return () => undefined
  }
  const onTheme = () => {
    applyTelegramTheme(webApp)
    onChange()
  }
  const onLayout = (...args: unknown[]) => {
    const event = args[0] as { isStateStable?: boolean } | undefined
    if (event && event.isStateStable === false) {
      return
    }
    applyTelegramLayout(webApp)
  }
  webApp.onEvent('themeChanged', onTheme)
  webApp.onEvent('viewportChanged', onLayout)
  webApp.onEvent('safeAreaChanged', onLayout)
  webApp.onEvent('contentSafeAreaChanged', onLayout)
  return () => {
    webApp.offEvent('themeChanged', onTheme)
    webApp.offEvent('viewportChanged', onLayout)
    webApp.offEvent('safeAreaChanged', onLayout)
    webApp.offEvent('contentSafeAreaChanged', onLayout)
  }
}

export function hapticSelection(): void {
  try {
    getTelegramWebApp()?.HapticFeedback?.selectionChanged()
  } catch {
    // Older clients omit haptic APIs.
  }
}

export function hapticNotification(type: 'error' | 'success' | 'warning'): void {
  try {
    getTelegramWebApp()?.HapticFeedback?.notificationOccurred(type)
  } catch {
    // Older clients omit haptic APIs.
  }
}

const MAIN_BUTTON_SPACE = '4.25rem'

export function setTelegramMainButton(options: {
  text: string
  visible: boolean
  enabled: boolean
  progress?: boolean
  onClick: () => void
}): () => void {
  const webApp = getTelegramWebApp()
  const button = webApp?.MainButton
  const root = document.documentElement
  if (!button) {
    root.classList.remove('has-tg-main-button')
    root.style.setProperty('--tg-main-button-space', '0px')
    return () => undefined
  }
  if (!options.visible) {
    button.hide()
    root.classList.remove('has-tg-main-button')
    root.style.setProperty('--tg-main-button-space', '0px')
    return () => undefined
  }
  button.setText(options.text)
  if (options.enabled) {
    button.enable()
  } else {
    button.disable()
  }
  if (options.progress) {
    button.showProgress(false)
  } else {
    button.hideProgress()
  }
  button.show()
  root.classList.add('has-tg-main-button')
  root.style.setProperty('--tg-main-button-space', MAIN_BUTTON_SPACE)
  const onClick = options.onClick
  button.onClick(onClick)
  return () => {
    button.offClick(onClick)
    button.hideProgress()
    button.hide()
    root.classList.remove('has-tg-main-button')
    root.style.setProperty('--tg-main-button-space', '0px')
  }
}
