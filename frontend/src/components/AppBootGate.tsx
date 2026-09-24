import { useEffect, useRef, useState, type ReactNode } from 'react'

import { useAuth } from '../context/AuthContext'
import { useGuestExperiment } from '../context/GuestExperimentContext'
import { BOOT_FADE_MS } from '../lib/bootProgress'
import { hapticNotification } from '../platform/telegram'
import { AppBootLoader } from './AppBootLoader'

export function AppBootGate({ children }: { children: ReactNode }) {
  const { isLoading, telegramAuthError, retryBootstrap: retryAuth } = useAuth()
  const { isBootstrapLoading, retryBootstrap: retryGuest } = useGuestExperiment()
  const booting = isLoading || isBootstrapLoading
  const [overlay, setOverlay] = useState(true)
  const [session, setSession] = useState(0)
  const celebrated = useRef(false)

  useEffect(() => {
    if (booting) {
      setOverlay(true)
      return
    }
    if (!telegramAuthError && !celebrated.current) {
      celebrated.current = true
      hapticNotification('success')
    }
    const timer = window.setTimeout(() => setOverlay(false), BOOT_FADE_MS)
    return () => window.clearTimeout(timer)
  }, [booting, telegramAuthError])

  return (
    <>
      {booting ? null : children}
      {overlay ? (
        <AppBootLoader
          key={session}
          pending={booting}
          exiting={!booting}
          onRetry={() => {
            setSession((current) => current + 1)
            retryAuth()
            retryGuest()
          }}
        />
      ) : null}
    </>
  )
}
