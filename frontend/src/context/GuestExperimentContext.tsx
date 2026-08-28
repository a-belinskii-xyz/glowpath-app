import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { bootstrapFeatures } from '../api/features'
import { collectGuestFingerprint } from '../lib/guestFingerprint'
import { setGuestExperimentState } from '../lib/guestMode'
import { getAccessToken } from '../lib/storage'
import { ensureGuestMeta, getGuestMeta, guestHeartbeatSync } from '../guest/store'

type GuestExperimentContextValue = {
  isBootstrapLoading: boolean
  guestLocalDiary: boolean
  visitorId: string | null
  cohort: string | null
  guestOnboardingCompleted: boolean
  refreshGuestMeta: () => Promise<void>
}

const GuestExperimentContext = createContext<GuestExperimentContextValue | null>(null)

export function GuestExperimentProvider({ children }: { children: ReactNode }) {
  const [isBootstrapLoading, setIsBootstrapLoading] = useState(true)
  const [guestLocalDiary, setGuestLocalDiary] = useState(false)
  const [visitorId, setVisitorId] = useState<string | null>(null)
  const [cohort, setCohort] = useState<string | null>(null)
  const [guestOnboardingCompleted, setGuestOnboardingCompleted] = useState(false)

  const refreshGuestMeta = useCallback(async () => {
    const meta = await getGuestMeta()
    setGuestOnboardingCompleted(meta?.onboarding_completed ?? false)
  }, [])

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      if (getAccessToken()) {
        setGuestExperimentState(false, null)
        if (!cancelled) {
          setGuestLocalDiary(false)
          setVisitorId(null)
          setCohort(null)
          setIsBootstrapLoading(false)
        }
        return
      }
      try {
        const response = await bootstrapFeatures(collectGuestFingerprint())
        if (cancelled) return
        setGuestExperimentState(response.guest_local_diary, response.visitor_id)
        setGuestLocalDiary(response.guest_local_diary)
        setVisitorId(response.visitor_id)
        setCohort(response.cohort)
        if (response.guest_local_diary) {
          await ensureGuestMeta(response.visitor_id)
          await guestHeartbeatSync()
          await refreshGuestMeta()
        }
      } catch {
        if (!cancelled) {
          setGuestExperimentState(false, null)
          setGuestLocalDiary(false)
        }
      } finally {
        if (!cancelled) {
          setIsBootstrapLoading(false)
        }
      }
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [refreshGuestMeta])

  const value = useMemo(
    () => ({
      isBootstrapLoading,
      guestLocalDiary,
      visitorId,
      cohort,
      guestOnboardingCompleted,
      refreshGuestMeta,
    }),
    [
      isBootstrapLoading,
      guestLocalDiary,
      visitorId,
      cohort,
      guestOnboardingCompleted,
      refreshGuestMeta,
    ],
  )

  return <GuestExperimentContext.Provider value={value}>{children}</GuestExperimentContext.Provider>
}

export function useGuestExperiment(): GuestExperimentContextValue {
  const context = useContext(GuestExperimentContext)
  if (!context) {
    throw new Error('useGuestExperiment must be used within GuestExperimentProvider')
  }
  return context
}
