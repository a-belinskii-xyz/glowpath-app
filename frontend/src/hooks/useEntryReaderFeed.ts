import { useCallback, useEffect, useRef, useState } from 'react'

import { getMoodEntry, listMoodEntries } from '../api/moodEntries'
import {
  getCurrentYearMonth,
  getMonthBounds,
  shiftYearMonth,
  yearMonthFromInstant,
} from '../lib/datetime'
import type { MoodEntryPublic } from '../types/mood'

const PAGE_SIZE = 40

function sortNewestFirst(items: MoodEntryPublic[]): MoodEntryPublic[] {
  return [...items].sort((a, b) => {
    const recorded = new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime()
    if (recorded !== 0) {
      return recorded
    }
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })
}

function mergeItems(
  current: MoodEntryPublic[],
  incoming: MoodEntryPublic[],
): MoodEntryPublic[] {
  const byId = new Map(current.map((entry) => [entry.id, entry]))
  for (const item of incoming) {
    byId.set(item.id, item)
  }
  return sortNewestFirst(Array.from(byId.values()))
}

async function listMonth(
  year: number,
  month: number,
  timeZone: string,
  offset: number,
  limit = PAGE_SIZE,
) {
  const bounds = getMonthBounds(year, month, timeZone)
  const response = await listMoodEntries({
    limit,
    offset,
    recorded_from: bounds.recorded_from,
    recorded_to: bounds.recorded_to,
  })
  return {
    items: response.items,
    complete: response.items.length < limit,
    bounds,
  }
}

async function listAllMonth(year: number, month: number, timeZone: string) {
  const items: MoodEntryPublic[] = []
  let offset = 0
  while (true) {
    const page = await listMonth(year, month, timeZone, offset)
    items.push(...page.items)
    offset += page.items.length
    if (page.complete) {
      break
    }
  }
  return items
}

type MonthCursor = {
  year: number
  month: number
  offset: number
  complete: boolean
}

export function useEntryReaderFeed(
  entryId: string | undefined,
  timeZone: string,
  locale?: string,
) {
  const [items, setItems] = useState<MoodEntryPublic[]>([])
  const [index, setIndex] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [hasMoreNewer, setHasMoreNewer] = useState(false)
  const [hasMoreOlder, setHasMoreOlder] = useState(false)

  const itemsRef = useRef(items)
  itemsRef.current = items
  const indexRef = useRef(index)
  indexRef.current = index
  const olderRef = useRef<MonthCursor | null>(null)
  const newerMonthRef = useRef<{ year: number; month: number } | null>(null)
  const loadingNewerRef = useRef(false)
  const loadingOlderRef = useRef(false)
  const loadGenRef = useRef(0)

  const active = items[index] ?? null

  const loadAround = useCallback(
    async (id: string) => {
      const generation = ++loadGenRef.current
      setIsLoading(true)
      setError(null)
      olderRef.current = null
      newerMonthRef.current = null
      loadingNewerRef.current = false
      loadingOlderRef.current = false
      void locale

      try {
        const center = await getMoodEntry(id)
        if (generation !== loadGenRef.current) {
          return
        }
        setItems([center])
        setIndex(0)
        setIsLoading(false)

        const month = yearMonthFromInstant(center.recorded_at, timeZone)
        const collected: MoodEntryPublic[] = []
        let offset = 0
        let foundAt = -1
        let monthComplete = false

        while (foundAt < 0 || collected.length - foundAt < PAGE_SIZE / 2) {
          const page = await listMonth(month.year, month.month, timeZone, offset)
          if (generation !== loadGenRef.current) {
            return
          }
          collected.push(...page.items)
          offset += page.items.length
          monthComplete = page.complete
          foundAt = collected.findIndex((item) => item.id === id)
          if (page.complete) {
            break
          }
        }

        const merged = mergeItems(collected, [center])
        const nextIndex = Math.max(0, merged.findIndex((item) => item.id === id))
        setItems(merged)
        setIndex(nextIndex)

        olderRef.current = {
          year: month.year,
          month: month.month,
          offset,
          complete: monthComplete,
        }
        newerMonthRef.current = month

        const monthBounds = getMonthBounds(month.year, month.month, timeZone)
        const newerProbe = await listMoodEntries({
          limit: 1,
          recorded_from: monthBounds.recorded_to,
        })
        const olderProbe = monthComplete
          ? await listMoodEntries({
              limit: 1,
              recorded_to: merged[merged.length - 1]?.recorded_at,
            })
          : { items: [{ id: 'pending' }] }

        if (generation !== loadGenRef.current) {
          return
        }
        setHasMoreNewer(
          newerProbe.items.some((item) => !merged.some((entry) => entry.id === item.id)),
        )
        setHasMoreOlder(
          !monthComplete ||
            olderProbe.items.some((item) => !merged.some((entry) => entry.id === item.id)),
        )
      } catch (err) {
        if (generation !== loadGenRef.current) {
          return
        }
        setError(err)
        setIsLoading(false)
      }
    },
    [timeZone, locale],
  )

  useEffect(() => {
    if (!entryId) {
      setItems([])
      setIndex(0)
      setIsLoading(false)
      return
    }
    const existing = itemsRef.current.findIndex((item) => item.id === entryId)
    if (existing >= 0) {
      setIndex(existing)
      setIsLoading(false)
      return
    }
    void loadAround(entryId)
  }, [entryId, loadAround])

  const loadNewer = useCallback(async () => {
    const from = newerMonthRef.current
    if (!from || loadingNewerRef.current || !hasMoreNewer) {
      return
    }
    loadingNewerRef.current = true
    try {
      let month = shiftYearMonth(from.year, from.month, 1)
      const now = getCurrentYearMonth(timeZone)
      for (let step = 0; step < 36; step += 1) {
        if (month.year > now.year || (month.year === now.year && month.month > now.month)) {
          newerMonthRef.current = now
          setHasMoreNewer(false)
          return
        }
        const incoming = await listAllMonth(month.year, month.month, timeZone)
        newerMonthRef.current = month
        if (incoming.length > 0) {
          const previous = itemsRef.current
          const focusedId = previous[indexRef.current]?.id
          const merged = mergeItems(incoming, previous)
          setItems(merged)
          if (focusedId) {
            const nextIndex = merged.findIndex((item) => item.id === focusedId)
            if (nextIndex >= 0) {
              setIndex(nextIndex)
            }
          }
          const bounds = getMonthBounds(month.year, month.month, timeZone)
          const probe = await listMoodEntries({
            limit: 1,
            recorded_from: bounds.recorded_to,
          })
          setHasMoreNewer(probe.items.length > 0)
          return
        }
        month = shiftYearMonth(month.year, month.month, 1)
      }
      setHasMoreNewer(false)
    } finally {
      loadingNewerRef.current = false
    }
  }, [hasMoreNewer, timeZone])

  const loadOlder = useCallback(async () => {
    const cursor = olderRef.current
    if (!cursor || loadingOlderRef.current || !hasMoreOlder) {
      return
    }
    loadingOlderRef.current = true
    try {
      if (!cursor.complete) {
        const page = await listMonth(cursor.year, cursor.month, timeZone, cursor.offset)
        olderRef.current = {
          ...cursor,
          offset: cursor.offset + page.items.length,
          complete: page.complete,
        }
        setItems((current) => mergeItems(current, page.items))
        if (!page.complete) {
          return
        }
      }

      const previous = shiftYearMonth(cursor.year, cursor.month, -1)
      const incoming = await listAllMonth(previous.year, previous.month, timeZone)
      olderRef.current = {
        year: previous.year,
        month: previous.month,
        offset: incoming.length,
        complete: true,
      }
      if (incoming.length > 0) {
        setItems((current) => mergeItems(current, incoming))
        setHasMoreOlder(true)
        return
      }
      const oldest = itemsRef.current[itemsRef.current.length - 1]
      const probe = oldest
        ? await listMoodEntries({ limit: 1, recorded_to: oldest.recorded_at })
        : { items: [] }
      const hasMore = probe.items.some(
        (item) => !itemsRef.current.some((entry) => entry.id === item.id),
      )
      setHasMoreOlder(hasMore)
    } finally {
      loadingOlderRef.current = false
    }
  }, [hasMoreOlder, timeZone])

  useEffect(() => {
    if (index <= 1 && hasMoreNewer) {
      void loadNewer()
    }
  }, [hasMoreNewer, index, loadNewer])

  useEffect(() => {
    if (index >= items.length - 2 && hasMoreOlder && items.length > 0) {
      void loadOlder()
    }
  }, [hasMoreOlder, index, items.length, loadOlder])

  const replaceEntry = useCallback((entry: MoodEntryPublic) => {
    setItems((current) => current.map((item) => (item.id === entry.id ? entry : item)))
  }, [])

  const removeActive = useCallback((): MoodEntryPublic | null => {
    const current = itemsRef.current
    const currentIndex = current.findIndex((item) => item.id === active?.id)
    if (currentIndex < 0) {
      return null
    }
    const remaining = current.filter((item) => item.id !== active?.id)
    const next = remaining[Math.min(currentIndex, remaining.length - 1)] ?? null
    setItems(remaining)
    if (next) {
      const nextIndex = remaining.findIndex((item) => item.id === next.id)
      setIndex(Math.max(0, nextIndex))
    } else {
      setIndex(0)
    }
    return next
  }, [active?.id])

  const canGoNewer = index > 0 || hasMoreNewer
  const canGoOlder = index < items.length - 1 || hasMoreOlder

  const goNewer = useCallback(() => {
    setIndex((current) => Math.max(0, current - 1))
  }, [])

  const goOlder = useCallback(() => {
    setIndex((current) => Math.min(Math.max(itemsRef.current.length - 1, 0), current + 1))
  }, [])

  return {
    items,
    index,
    setIndex,
    active,
    isLoading,
    error,
    canGoNewer,
    canGoOlder,
    goNewer,
    goOlder,
    replaceEntry,
    removeActive,
    reload: loadAround,
  }
}
