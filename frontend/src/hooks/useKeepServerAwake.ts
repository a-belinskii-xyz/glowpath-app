import { useEffect } from 'react'

import { getApiBaseUrl } from '../api/client'

// Render's free plan sleeps a service after 15 minutes without requests.
const PING_EVERY_MS = 10 * 60 * 1000
// A tab left open with nobody using it should not keep the server up.
const IDLE_AFTER_MS = 30 * 60 * 1000
const CHECK_EVERY_MS = 60 * 1000
const ACTIVITY_EVENTS = ['pointerdown', 'keydown', 'touchstart', 'scroll'] as const

/**
 * While someone is using the app, ping /v1/health so the API (and the nginx front
 * that proxies it) does not fall asleep. The endpoint never touches the database.
 */
export function useKeepServerAwake(): void {
  useEffect(() => {
    let lastActivity = Date.now()
    let lastPing = Date.now()

    const ping = () => {
      lastPing = Date.now()
      void fetch(`${getApiBaseUrl()}/v1/health`, { cache: 'no-store' }).catch(() => undefined)
    }
    const maybePing = () => {
      const now = Date.now()
      if (
        document.visibilityState === 'visible' &&
        now - lastActivity < IDLE_AFTER_MS &&
        now - lastPing >= PING_EVERY_MS
      ) {
        ping()
      }
    }
    const onActivity = () => {
      lastActivity = Date.now()
    }
    const onVisible = () => {
      if (document.visibilityState === 'visible') {
        onActivity()
        maybePing()
      }
    }

    ACTIVITY_EVENTS.forEach((name) =>
      window.addEventListener(name, onActivity, { passive: true, capture: true }),
    )
    document.addEventListener('visibilitychange', onVisible)
    const timer = window.setInterval(maybePing, CHECK_EVERY_MS)
    return () => {
      ACTIVITY_EVENTS.forEach((name) =>
        window.removeEventListener(name, onActivity, { capture: true }),
      )
      document.removeEventListener('visibilitychange', onVisible)
      window.clearInterval(timer)
    }
  }, [])
}
