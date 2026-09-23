export type GuestFingerprintSignals = {
  timezone: string
  screen_width: number
  screen_height: number
  screen_dpr: number
  platform: string
  max_touch_points: number
}

export function collectGuestFingerprint(): GuestFingerprintSignals {
  return {
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
    screen_width: window.screen.width,
    screen_height: window.screen.height,
    screen_dpr: window.devicePixelRatio || 1,
    platform: navigator.platform || '',
    max_touch_points: navigator.maxTouchPoints ?? 0,
  }
}
