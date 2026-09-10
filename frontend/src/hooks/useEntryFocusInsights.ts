import { useCallback, useEffect, useRef, useState } from 'react'

import { getMoodInsights } from '../api/moodEntries'
import type { MoodInsightsResponse } from '../types/mood'

const EMPTY_INSIGHTS: MoodInsightsResponse = {
  window_from: '',
  window_to: '',
  active_days: 0,
  entry_count: 0,
  baseline_index: null,
  items: [],
}

export function useEntryFocusInsights(entryIds: string[], enabled: boolean, locale?: string) {
  const cacheRef = useRef<Map<string, MoodInsightsResponse>>(new Map())
  const inFlightRef = useRef<Set<string>>(new Set())
  const [, setVersion] = useState(0)

  useEffect(() => {
    cacheRef.current.clear()
    inFlightRef.current.clear()
    setVersion((v) => v + 1)
  }, [locale])

  const entryIdsKey = entryIds.join('\0')

  useEffect(() => {
    if (!enabled) {
      return
    }
    const unique = [...new Set(entryIdsKey.split('\0').filter(Boolean))]
    const toFetch = unique.filter(
      (id) => !cacheRef.current.has(id) && !inFlightRef.current.has(id),
    )
    if (toFetch.length === 0) {
      return
    }

    for (const id of toFetch) {
      inFlightRef.current.add(id)
      void getMoodInsights({ limit: 1, focus_entry_id: id })
        .then((response) => {
          cacheRef.current.set(id, response)
          setVersion((v) => v + 1)
        })
        .catch(() => {
          cacheRef.current.set(id, EMPTY_INSIGHTS)
          setVersion((v) => v + 1)
        })
        .finally(() => {
          inFlightRef.current.delete(id)
        })
    }
  }, [enabled, entryIdsKey])

  const isReady = useCallback(
    (entryId: string | undefined) => {
      if (!enabled || !entryId) {
        return true
      }
      return cacheRef.current.has(entryId)
    },
    [enabled],
  )

  const getInsights = useCallback((entryId: string | undefined): MoodInsightsResponse | null => {
    if (!entryId) {
      return null
    }
    return cacheRef.current.get(entryId) ?? null
  }, [])

  return { isReady, getInsights }
}
