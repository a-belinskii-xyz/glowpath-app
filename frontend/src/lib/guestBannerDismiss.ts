const DISMISSED_AT_KEY = 'mt_guest_banner_dismissed_at'
const DISMISSED_ENTRY_COUNT_KEY = 'mt_guest_banner_dismissed_entry_count'

/** How long the banner stays hidden after the user dismisses it. */
export const GUEST_BANNER_SNOOZE_MS = 24 * 60 * 60 * 1000

type GuestBannerDismiss = {
  dismissedAt: number
  entryCount: number
}

export function readGuestBannerDismiss(): GuestBannerDismiss | null {
  const dismissedAtRaw = localStorage.getItem(DISMISSED_AT_KEY)
  if (!dismissedAtRaw) {
    return null
  }
  const dismissedAt = Number(dismissedAtRaw)
  if (!Number.isFinite(dismissedAt)) {
    return null
  }
  const entryCount = Number(localStorage.getItem(DISMISSED_ENTRY_COUNT_KEY) ?? '0')
  return { dismissedAt, entryCount: Number.isFinite(entryCount) ? entryCount : 0 }
}

export function dismissGuestBanner(entryCount: number): void {
  localStorage.setItem(DISMISSED_AT_KEY, String(Date.now()))
  localStorage.setItem(DISMISSED_ENTRY_COUNT_KEY, String(entryCount))
}

export function isGuestBannerVisible(entryCount: number, now = Date.now()): boolean {
  const dismiss = readGuestBannerDismiss()
  if (!dismiss) {
    return true
  }
  if (entryCount > dismiss.entryCount) {
    return true
  }
  return now - dismiss.dismissedAt >= GUEST_BANNER_SNOOZE_MS
}

export function guestBannerSnoozeRemainingMs(now = Date.now()): number | null {
  const dismiss = readGuestBannerDismiss()
  if (!dismiss) {
    return null
  }
  const remaining = GUEST_BANNER_SNOOZE_MS - (now - dismiss.dismissedAt)
  return remaining > 0 ? remaining : 0
}
