import { useCallback, useEffect, useState } from 'react'

import { getNotificationStatus } from '../api/notificationSettings'
import type { NotificationSystemStatus } from '../types/notificationSettings'

export function useNotificationStatus() {
  const [status, setStatus] = useState<NotificationSystemStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)

  const reload = useCallback(async () => {
    setIsLoading(true)
    try {
      const next = await getNotificationStatus()
      setStatus(next)
      setError(null)
      return next
    } catch (err) {
      setError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    void getNotificationStatus()
      .then((next) => {
        if (!cancelled) {
          setStatus(next)
          setError(null)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  return { status, isLoading, error, reload }
}
