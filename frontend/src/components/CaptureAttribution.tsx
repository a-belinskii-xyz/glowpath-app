import { useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'

import { parseMoodEntrySource, setStoredMoodEntrySource } from '../lib/moodEntrySource'

/**
 * Captures ``?from=`` attribution into sessionStorage on any route, then strips
 * the query param so navigation / login redirects cannot drop the trail.
 */
export function CaptureAttribution() {
  const [searchParams, setSearchParams] = useSearchParams()
  const lastCaptured = useRef<string | null>(null)
  const rawFrom = searchParams.get('from')

  // Capture synchronously so an auth redirect in the same paint cannot race us.
  if (rawFrom != null && rawFrom !== lastCaptured.current) {
    lastCaptured.current = rawFrom
    const source = parseMoodEntrySource(rawFrom)
    if (source) {
      setStoredMoodEntrySource(source)
    }
  }

  useEffect(() => {
    if (!searchParams.has('from')) {
      return
    }
    const next = new URLSearchParams(searchParams)
    next.delete('from')
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams])

  return null
}
