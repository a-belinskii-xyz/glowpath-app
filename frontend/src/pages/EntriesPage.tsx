import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'

import { deleteMoodEntry, getMoodEntryCalendar, getMoodEntryStats, getMoodEntryStreak, getMoodInsights, listMoodEntries, patchMoodEntry, searchMoodEntries } from '../api/moodEntries'
import { getGoalCalendar, getGoalStats, listGoals } from '../api/goals'
import { Alert } from '../components/Alert'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { EmotionStatsBarChart } from '../components/EmotionStatsBarChart'
import { PatternInsights } from '../components/PatternInsights'
import { GoalPeriodStats, type GoalStatsPeriod } from '../components/GoalPeriodStats'
import { EntryRow } from '../components/EntryRow'
import { HeartIcon } from '../components/HeartIcon'
import { IconButton, IconLinkButton } from '../components/IconButton'
import { PlusIcon, SearchIcon, SparkleIcon } from '../components/icons'
import { MonthCalendar, type CalendarMode } from '../components/MonthCalendar'
import { MonthControl } from '../components/MonthControl'
import { MonthSummaryOverlay } from '../components/MonthSummaryOverlay'
import { StreakBadge } from '../components/StreakBadge'
import { useColorScheme } from '../hooks/useColorScheme'
import { useMediaQuery } from '../hooks/useMediaQuery'
import { useAuth } from '../context/AuthContext'
import { hasAppAccess } from '../lib/authAccess'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { intlLocale } from '../i18n/t'
import {
  companionDaypartForHour,
  companionLine,
} from '../lib/companion'
import {
  dayKey,
  formatDayHeading,
  formatMonthHeading,
  formatMonthHeadingCompact,
  formatTime,
  formatWeekHeading,
  formatYearMonthParam,
  getCurrentYearMonth,
  getDayBounds,
  getIsoWeekBounds,
  getMonthBounds,
  clampWeekAnchorToMonth,
  localHour,
  parseYearMonthParam,
  shiftDateKey,
  todayKey,
  weekIntersectsMonth,
} from '../lib/datetime'
import { ApiError, formatApiError } from '../lib/errors'
import { canUseDiaryFeatures } from '../lib/guestMode'
import { buildGradientWashFromScores, dayWashRecipe, motion } from '../design'
import { useScrollAmbientGlow } from '../hooks/useScrollAmbientGlow'
import { entryMoodColor } from '../lib/moodScale'
import type { GoalCalendarDayPublic, GoalPeriodStatPublic, GoalPublic } from '../types/goal'
import type { AchievementPublic } from '../types/achievement'
import type { CalendarDayPublic, MoodEntryPublic, MoodEntryStatsResponse, MoodInsightsResponse } from '../types/mood'

const PAGE_SIZE = 20
const DAY_FETCH_LIMIT = 100
const SEARCH_DEBOUNCE_MS = 300
const SEARCH_LIMIT = 40

function sortEntriesNewestFirst(items: MoodEntryPublic[]): MoodEntryPublic[] {
  return [...items].sort(
    (a, b) => new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime(),
  )
}

function mergeEntries(
  current: MoodEntryPublic[],
  incoming: MoodEntryPublic[],
): MoodEntryPublic[] {
  const byId = new Map(current.map((entry) => [entry.id, entry]))
  for (const item of incoming) {
    byId.set(item.id, item)
  }
  return sortEntriesNewestFirst(Array.from(byId.values()))
}

export function EntriesPage() {
  const { user } = useAuth()
  const diaryAccess = canUseDiaryFeatures(user)
  const { locale, t } = useLocale()
  const { scores, showStreak } = useMoodPreferences()
  const colorScheme = useColorScheme()
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [unlockedToast, setUnlockedToast] = useState<AchievementPublic[]>(() => {
    const state = location.state as { unlockedAchievements?: AchievementPublic[] } | null
    return state?.unlockedAchievements ?? []
  })
  const timeZone = user?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC'
  const dateLocale = intlLocale(locale)
  const isNarrow = useMediaQuery('(max-width: 899px)')
  const monthShortLabels = useMemo(() => t('calendar.monthsShort').split('|'), [t])
  const formatHeading = useCallback(
    (headingYear: number, headingMonth: number) =>
      isNarrow
        ? formatMonthHeadingCompact(headingYear, headingMonth, monthShortLabels)
        : formatMonthHeading(headingYear, headingMonth, dateLocale),
    [dateLocale, isNarrow, monthShortLabels],
  )

  useEffect(() => {
    const state = location.state as { unlockedAchievements?: AchievementPublic[] } | null
    if (state?.unlockedAchievements && state.unlockedAchievements.length > 0) {
      setUnlockedToast(state.unlockedAchievements)
      navigate(`${location.pathname}${location.search}`, { replace: true, state: {} })
    }
  }, [location.pathname, location.search, location.state, navigate])

  const initialMonth = (() => {
    const now = getCurrentYearMonth(timeZone)
    const parsed = parseYearMonthParam(searchParams.get('month')) ?? now
    if (parsed.year > now.year || (parsed.year === now.year && parsed.month > now.month)) {
      return now
    }
    return parsed
  })()

  const [year, setYear] = useState(initialMonth.year)
  const [month, setMonth] = useState(initialMonth.month)

  const [calendarDays, setCalendarDays] = useState<CalendarDayPublic[]>([])
  const [goalCalendarDays, setGoalCalendarDays] = useState<GoalCalendarDayPublic[]>([])
  const [goalsById, setGoalsById] = useState<Map<string, GoalPublic>>(() => new Map())
  const [calendarMode, setCalendarMode] = useState<CalendarMode>('moods')
  const [isCalendarLoading, setIsCalendarLoading] = useState(true)

  const [stats, setStats] = useState<MoodEntryStatsResponse | null>(null)
  const [isStatsLoading, setIsStatsLoading] = useState(true)
  const [streakDays, setStreakDays] = useState<number | null>(null)
  const [streakLoggedToday, setStreakLoggedToday] = useState(false)
  const [insights, setInsights] = useState<MoodInsightsResponse | null>(null)
  const [isInsightsLoading, setIsInsightsLoading] = useState(true)
  const [goalStatsPeriod, setGoalStatsPeriod] = useState<GoalStatsPeriod>('week')
  const [weekAnchorDate, setWeekAnchorDate] = useState(() => todayKey(timeZone))
  const [goalStatsItems, setGoalStatsItems] = useState<GoalPeriodStatPublic[]>([])
  const [goalStatsPeriodDays, setGoalStatsPeriodDays] = useState(7)
  const [isGoalStatsLoading, setIsGoalStatsLoading] = useState(false)

  const [entries, setEntries] = useState<MoodEntryPublic[]>([])
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [favoritesOnly, setFavoritesOnly] = useState(false)
  const [searchInput, setSearchInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [recapOpen, setRecapOpen] = useState(false)
  const [viewedSummaries, setViewedSummaries] = useState<Set<string>>(() => new Set())

  const [pendingScrollDay, setPendingScrollDay] = useState<string | null>(
    () => searchParams.get('day'),
  )
  const [pendingScrollEntry, setPendingScrollEntry] = useState<string | null>(
    () => searchParams.get('entry'),
  )

  const loadMoreRef = useRef<HTMLDivElement | null>(null)
  const loadingRef = useRef(false)
  const dayLoadRef = useRef<string | null>(null)
  const searchInputRef = useRef<HTMLInputElement | null>(null)

  const monthBounds = useMemo(() => getMonthBounds(year, month, timeZone), [year, month, timeZone])
  const isSearchMode = searchQuery.trim().length > 0
  const showSearchField = searchOpen || searchInput.length > 0
  const weekBounds = useMemo(
    () => getIsoWeekBounds(weekAnchorDate, timeZone),
    [timeZone, weekAnchorDate],
  )
  const currentWeekBounds = useMemo(
    () => getIsoWeekBounds(todayKey(timeZone), timeZone),
    [timeZone],
  )
  const currentMonth = useMemo(() => getCurrentYearMonth(timeZone), [timeZone])
  const isCurrentMonthView = year === currentMonth.year && month === currentMonth.month
  const monthKey = `${year}-${String(month).padStart(2, '0')}`
  const hasMonthEntries = (stats?.total_entries ?? 0) > 0
  const summarySeen = viewedSummaries.has(monthKey)
  const canPlaySummary =
    Boolean(hasAppAccess(user)) &&
    !isSearchMode &&
    !isCurrentMonthView &&
    hasMonthEntries &&
    !isStatsLoading
  const companionGreeting = useMemo(() => {
    if (!isCurrentMonthView || isSearchMode) {
      return null
    }
    const dateKey = todayKey(timeZone)
    return companionLine(t, 'greeting', companionDaypartForHour(localHour(timeZone)), dateKey)
  }, [isCurrentMonthView, isSearchMode, t, timeZone])
  const emptyMonthCopy = useMemo(() => {
    if (!isCurrentMonthView) {
      return t('entries.noEntriesThisMonth')
    }
    const dateKey = todayKey(timeZone)
    return companionLine(t, 'emptyMonth', companionDaypartForHour(localHour(timeZone)), dateKey)
  }, [isCurrentMonthView, t, timeZone])
  const emptyPromptCopy = useMemo(() => {
    const dateKey = todayKey(timeZone)
    return companionLine(t, 'emptyPrompt', companionDaypartForHour(localHour(timeZone)), dateKey)
  }, [t, timeZone])
  const canGoNextMonth =
    year < currentMonth.year || (year === currentMonth.year && month < currentMonth.month)
  const monthTitleSizeLabels = useMemo(
    () => Array.from({ length: 12 }, (_, index) => formatHeading(year, index)),
    [formatHeading, year],
  )
  const goalStatsBounds = goalStatsPeriod === 'week' ? weekBounds : monthBounds
  const isCurrentGoalPeriod =
    goalStatsPeriod === 'week'
      ? weekBounds.period_start === currentWeekBounds.period_start
      : isCurrentMonthView
  const weekLabel = useMemo(
    () => formatWeekHeading(weekBounds.period_start, weekBounds.period_end, dateLocale),
    [dateLocale, weekBounds.period_end, weekBounds.period_start],
  )
  const canGoPreviousWeek = useMemo(() => {
    const prev = getIsoWeekBounds(shiftDateKey(weekBounds.period_start, -7), timeZone)
    return weekIntersectsMonth(prev.period_start, prev.period_end, year, month)
  }, [month, timeZone, weekBounds.period_start, year])
  const canGoNextWeek = useMemo(() => {
    const next = getIsoWeekBounds(shiftDateKey(weekBounds.period_start, 7), timeZone)
    return weekIntersectsMonth(next.period_start, next.period_end, year, month)
  }, [month, timeZone, weekBounds.period_start, year])

  useEffect(() => {
    setWeekAnchorDate((current) => clampWeekAnchorToMonth(current, year, month, timeZone))
  }, [month, timeZone, year])

  useEffect(() => {
    setRecapOpen(false)
  }, [month, year])

  const updateMonthParams = useCallback(
    (nextYear: number, nextMonth: number, options?: { day?: string; entry?: string }) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          next.set('month', formatYearMonthParam(nextYear, nextMonth))
          if (options?.day) {
            next.set('day', options.day)
          } else {
            next.delete('day')
          }
          if (options?.entry) {
            next.set('entry', options.entry)
          } else {
            next.delete('entry')
          }
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  const setMonthView = useCallback(
    (nextYear: number, nextMonth: number) => {
      const capped =
        nextYear > currentMonth.year ||
        (nextYear === currentMonth.year && nextMonth > currentMonth.month)
          ? currentMonth
          : { year: nextYear, month: nextMonth }
      setYear(capped.year)
      setMonth(capped.month)
      setPendingScrollDay(null)
      setPendingScrollEntry(null)
      updateMonthParams(capped.year, capped.month)
    },
    [currentMonth, updateMonthParams],
  )

  useEffect(() => {
    const parsed = parseYearMonthParam(searchParams.get('month'))
    if (!parsed) {
      return
    }
    const capped =
      parsed.year > currentMonth.year ||
      (parsed.year === currentMonth.year && parsed.month > currentMonth.month)
        ? currentMonth
        : parsed
    if (capped.year !== year || capped.month !== month) {
      setYear(capped.year)
      setMonth(capped.month)
      if (capped.year !== parsed.year || capped.month !== parsed.month) {
        updateMonthParams(capped.year, capped.month)
      }
    }
  }, [currentMonth, month, searchParams, updateMonthParams, year])

  const scrollToDay = useCallback((date: string) => {
    const node = document.getElementById(`day-${date}`)
    if (!node) {
      return false
    }
    // Instant scroll — smooth + infinite loading stops mid-way on long jumps.
    node.scrollIntoView({ behavior: 'auto', block: 'start' })
    node.classList.add('day-section-highlight')
    window.setTimeout(() => node.classList.remove('day-section-highlight'), motion.highlight.holdMs)
    return true
  }, [])

  const scrollToEntry = useCallback((entryId: string) => {
    const node = document.getElementById(`entry-${entryId}`)
    if (!node) {
      return false
    }
    node.scrollIntoView({ behavior: 'auto', block: 'center' })
    node.classList.add('entry-row-highlight')
    window.setTimeout(() => node.classList.remove('entry-row-highlight'), motion.highlight.holdMs)
    return true
  }, [])

  const loadCalendar = useCallback(async () => {
    if (!diaryAccess) {
      setCalendarDays([])
      setGoalCalendarDays([])
      setGoalsById(new Map())
      setIsCalendarLoading(false)
      return
    }

    setIsCalendarLoading(true)
    try {
      if (calendarMode === 'goals') {
        const [calendarResponse, goalsResponse] = await Promise.all([
          getGoalCalendar({
            recorded_from: monthBounds.recorded_from,
            recorded_to: monthBounds.recorded_to,
          }),
          listGoals(),
        ])
        setGoalCalendarDays(calendarResponse.days)
        setGoalsById(new Map(goalsResponse.items.map((goal) => [goal.id, goal])))
      } else {
        const response = await getMoodEntryCalendar({
          recorded_from: monthBounds.recorded_from,
          recorded_to: monthBounds.recorded_to,
        })
        setCalendarDays(response.days)
      }
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 403)) {
        setError(formatApiError(err, t, 'errors.failedLoadCalendar'))
      }
      setCalendarDays([])
      setGoalCalendarDays([])
      setGoalsById(new Map())
    } finally {
      setIsCalendarLoading(false)
    }
  }, [
    calendarMode,
    locale,
    monthBounds.recorded_from,
    monthBounds.recorded_to,
    t,
    diaryAccess,
  ])

  const loadStats = useCallback(async () => {
    if (!diaryAccess) {
      setStats(null)
      setIsStatsLoading(false)
      return
    }

    setIsStatsLoading(true)
    try {
      const response = await getMoodEntryStats({
        recorded_from: monthBounds.recorded_from,
        recorded_to: monthBounds.recorded_to,
      })
      setStats(response)
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 403)) {
        setError(formatApiError(err, t, 'errors.failedLoadStats'))
      }
      setStats(null)
    } finally {
      setIsStatsLoading(false)
    }
  }, [locale, monthBounds.recorded_from, monthBounds.recorded_to, t, diaryAccess])

  const loadStreak = useCallback(async () => {
    if (!diaryAccess || !showStreak) {
      setStreakDays(null)
      setStreakLoggedToday(false)
      return
    }

    try {
      const response = await getMoodEntryStreak()
      setStreakDays(response.current_days)
      setStreakLoggedToday(response.logged_today)
    } catch {
      setStreakDays(null)
      setStreakLoggedToday(false)
    }
  }, [showStreak, diaryAccess])

  const focusEntryId = searchParams.get('entry')
  const loadInsights = useCallback(async () => {
    if (!diaryAccess) {
      setInsights(null)
      setIsInsightsLoading(false)
      return
    }

    setIsInsightsLoading(true)
    try {
      const response = await getMoodInsights({
        limit: 4,
        recorded_from: monthBounds.recorded_from,
        recorded_to: monthBounds.recorded_to,
        ...(focusEntryId ? { focus_entry_id: focusEntryId } : {}),
      })
      setInsights(response)
    } catch {
      setInsights(null)
    } finally {
      setIsInsightsLoading(false)
    }
  }, [
    focusEntryId,
    locale,
    monthBounds.recorded_from,
    monthBounds.recorded_to,
    diaryAccess,
  ])

  const loadGoalStats = useCallback(async () => {
    if (!diaryAccess || calendarMode !== 'goals') {
      setGoalStatsItems([])
      setIsGoalStatsLoading(false)
      return
    }

    setIsGoalStatsLoading(true)
    try {
      const response = await getGoalStats({
        recorded_from: goalStatsBounds.recorded_from,
        recorded_to: goalStatsBounds.recorded_to,
      })
      setGoalStatsItems(response.items)
      setGoalStatsPeriodDays(response.period_days)
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 403)) {
        setError(formatApiError(err, t, 'errors.failedLoadGoalStats'))
      }
      setGoalStatsItems([])
    } finally {
      setIsGoalStatsLoading(false)
    }
  }, [
    calendarMode,
    goalStatsBounds.recorded_from,
    goalStatsBounds.recorded_to,
    locale,
    t,
    diaryAccess,
  ])

  const loadPage = useCallback(
    async (pageOffset: number, replace: boolean) => {
      if (!diaryAccess) {
        setIsLoading(false)
        return
      }
      if (loadingRef.current) {
        return
      }
      loadingRef.current = true

      if (replace) {
        setIsLoading(true)
      } else {
        setIsLoadingMore(true)
      }
      setError(null)

      try {
        const response = await listMoodEntries({
          limit: PAGE_SIZE,
          offset: pageOffset,
          recorded_from: monthBounds.recorded_from,
          recorded_to: monthBounds.recorded_to,
          ...(favoritesOnly ? { is_favorite: true } : {}),
        })

        setEntries((current) =>
          replace ? response.items : mergeEntries(current, response.items),
        )
        setOffset(pageOffset + response.items.length)
        setHasMore(response.items.length === PAGE_SIZE)
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError(t('errors.verifyToViewEntries'))
        } else {
          setError(formatApiError(err, t, 'errors.failedLoadEntries'))
        }
      } finally {
        setIsLoading(false)
        setIsLoadingMore(false)
        loadingRef.current = false
      }
    },
    [
      favoritesOnly,
      locale,
      monthBounds.recorded_from,
      monthBounds.recorded_to,
      t,
      diaryAccess,
    ],
  )

  const ensureEntriesFromDay = useCallback(
    async (date: string): Promise<boolean | null> => {
      if (!diaryAccess) {
        return false
      }
      if (dayLoadRef.current === date) {
        return null
      }

      dayLoadRef.current = date
      setError(null)
      try {
        // Load a continuous newest→target-day prefix so infinite scroll cannot
        // insert "middle" days above the target while/after we jump there.
        const dayBounds = getDayBounds(date, timeZone)
        const items: MoodEntryPublic[] = []
        let pageOffset = 0
        while (true) {
          const response = await listMoodEntries({
            limit: DAY_FETCH_LIMIT,
            offset: pageOffset,
            recorded_from: dayBounds.recorded_from,
            recorded_to: monthBounds.recorded_to,
            ...(favoritesOnly ? { is_favorite: true } : {}),
          })
          items.push(...response.items)
          pageOffset += response.items.length
          if (response.items.length < DAY_FETCH_LIMIT) {
            break
          }
        }

        setEntries((current) => mergeEntries(current, items))
        // This range is a prefix of the month feed (newest-first).
        setOffset((current) => Math.max(current, items.length))
        return items.some((entry) => dayKey(entry.recorded_at, timeZone) === date)
      } catch (err) {
        if (!(err instanceof ApiError && err.status === 403)) {
          setError(formatApiError(err, t, 'errors.failedLoadEntries'))
        }
        return false
      } finally {
        if (dayLoadRef.current === date) {
          dayLoadRef.current = null
        }
      }
    },
    [
      favoritesOnly,
      monthBounds.recorded_to,
      t,
      timeZone,
      diaryAccess,
    ],
  )

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setSearchQuery(searchInput.trim())
    }, SEARCH_DEBOUNCE_MS)
    return () => window.clearTimeout(handle)
  }, [searchInput])

  useEffect(() => {
    if (!searchOpen) {
      return
    }
    searchInputRef.current?.focus()
  }, [searchOpen])

  useEffect(() => {
    void loadCalendar()
  }, [loadCalendar])

  useEffect(() => {
    void loadStats()
  }, [loadStats])

  useEffect(() => {
    void loadStreak()
  }, [loadStreak])

  useEffect(() => {
    void loadInsights()
  }, [loadInsights])

  useEffect(() => {
    void loadGoalStats()
  }, [loadGoalStats])

  useEffect(() => {
    if (isSearchMode) {
      return
    }
    setEntries([])
    setOffset(0)
    setHasMore(true)
    dayLoadRef.current = null
    void loadPage(0, true)
  }, [isSearchMode, loadPage])

  useEffect(() => {
    if (!isSearchMode) {
      return
    }
    if (!diaryAccess) {
      setIsLoading(false)
      return
    }
    if (loadingRef.current) {
      return
    }

    let cancelled = false
    loadingRef.current = true
    setIsLoading(true)
    setError(null)
    setHasMore(false)

    void (async () => {
      try {
        const response = await searchMoodEntries({
          q: searchQuery,
          limit: SEARCH_LIMIT,
        })
        if (!cancelled) {
          setEntries(response.items)
          setOffset(response.items.length)
        }
      } catch (err) {
        if (!cancelled) {
          if (err instanceof ApiError && err.status === 403) {
            setError(t('errors.verifyToViewEntries'))
          } else {
            setError(formatApiError(err, t, 'errors.failedLoadEntries'))
          }
          setEntries([])
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
        loadingRef.current = false
      }
    })()

    return () => {
      cancelled = true
      loadingRef.current = false
    }
  }, [isSearchMode, locale, searchQuery, t, diaryAccess])

  useEffect(() => {
    const node = loadMoreRef.current
    // Pause while jumping to a calendar day/entry — otherwise newly loaded
    // pages shift the target and the scroll stops mid-feed.
    if (
      isSearchMode ||
      !node ||
      !hasMore ||
      isLoading ||
      isLoadingMore ||
      pendingScrollDay ||
      pendingScrollEntry
    ) {
      return
    }

    const observer = new IntersectionObserver(
      (records) => {
        if (records[0]?.isIntersecting) {
          void loadPage(offset, false)
        }
      },
      { rootMargin: '200px' },
    )

    observer.observe(node)
    return () => observer.disconnect()
  }, [
    hasMore,
    isLoading,
    isLoadingMore,
    isSearchMode,
    loadPage,
    offset,
    pendingScrollDay,
    pendingScrollEntry,
  ])

  useEffect(() => {
    if (isLoading || (!pendingScrollDay && !pendingScrollEntry)) {
      return
    }

    let cancelled = false

    const run = async () => {
      const day = pendingScrollDay
      const entryId = pendingScrollEntry

      if (day) {
        const loaded = await ensureEntriesFromDay(day)
        if (cancelled) {
          return
        }
        if (loaded === null) {
          return
        }
        if (!loaded) {
          setPendingScrollDay(null)
          setPendingScrollEntry(null)
          return
        }
      }

      // Wait for the merged day sections to commit before jumping.
      await new Promise<void>((resolve) => {
        requestAnimationFrame(() => {
          requestAnimationFrame(() => resolve())
        })
      })
      if (cancelled) {
        return
      }

      if (entryId && scrollToEntry(entryId)) {
        setPendingScrollEntry(null)
        setPendingScrollDay(null)
        return
      }
      if (day && scrollToDay(day)) {
        setPendingScrollDay(null)
        if (!entryId) {
          return
        }
      }
      setPendingScrollEntry(null)
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [
    ensureEntriesFromDay,
    isLoading,
    pendingScrollDay,
    pendingScrollEntry,
    scrollToDay,
    scrollToEntry,
  ])

  const groupedEntries = useMemo(() => {
    const groups = new Map<string, MoodEntryPublic[]>()
    for (const entry of entries) {
      const key = dayKey(entry.recorded_at, timeZone)
      const bucket = groups.get(key) ?? []
      bucket.push(entry)
      groups.set(key, bucket)
    }
    return Array.from(groups.entries())
  }, [entries, timeZone])

  const ambientSources = useMemo(
    () =>
      isSearchMode
        ? entries.length > 0
          ? [
              {
                id: 'search-results',
                colors: entries.map((entry) => entryMoodColor(entry, scores)),
              },
            ]
          : []
        : groupedEntries.map(([key, dayEntries]) => ({
            id: `day-${key}`,
            colors: dayEntries.map((entry) => entryMoodColor(entry, scores)),
          })),
    [groupedEntries, entries, isSearchMode, scores],
  )

  useScrollAmbientGlow(ambientSources, ambientSources.length > 0)

  const goToPreviousMonth = () => {
    if (month === 0) {
      setMonthView(year - 1, 11)
      return
    }
    setMonthView(year, month - 1)
  }

  const goToNextMonth = () => {
    if (!canGoNextMonth) {
      return
    }
    if (month === 11) {
      setMonthView(year + 1, 0)
      return
    }
    setMonthView(year, month + 1)
  }

  const goToPreviousWeek = () => {
    setWeekAnchorDate((current) => {
      const prevAnchor = shiftDateKey(current, -7)
      const prev = getIsoWeekBounds(prevAnchor, timeZone)
      if (!weekIntersectsMonth(prev.period_start, prev.period_end, year, month)) {
        return current
      }
      return prev.period_start
    })
  }

  const goToNextWeek = () => {
    setWeekAnchorDate((current) => {
      const nextAnchor = shiftDateKey(current, 7)
      const next = getIsoWeekBounds(nextAnchor, timeZone)
      if (!weekIntersectsMonth(next.period_start, next.period_end, year, month)) {
        return current
      }
      return next.period_start
    })
  }

  const handleSelectWeekDay = (date: string) => {
    setWeekAnchorDate(clampWeekAnchorToMonth(date, year, month, timeZone))
  }

  const handleDelete = async (entryId: string) => {
    await deleteMoodEntry(entryId)
    setEntries((current) => current.filter((entry) => entry.id !== entryId))
    void loadCalendar()
    void loadStats()
    void loadInsights()
    void loadGoalStats()
    void loadStreak()
  }

  const handleToggleFavorite = async (entryId: string, isFavorite: boolean) => {
    const previous = entries.find((entry) => entry.id === entryId)
    if (!previous) {
      return
    }

    setEntries((current) =>
      current
        .map((entry) => (entry.id === entryId ? { ...entry, is_favorite: isFavorite } : entry))
        .filter((entry) => !(favoritesOnly && !entry.is_favorite)),
    )
    setError(null)

    try {
      await patchMoodEntry(entryId, { is_favorite: isFavorite })
    } catch (err) {
      setEntries((current) => {
        const restored = current.some((entry) => entry.id === entryId)
          ? current.map((entry) => (entry.id === entryId ? previous : entry))
          : mergeEntries(current, [previous])
        return restored
      })
      setError(formatApiError(err, t, 'errors.failedSaveEntry'))
    }
  }

  const handleDayWithEntries = (date: string) => {
    setPendingScrollEntry(null)
    setPendingScrollDay(date)
    updateMonthParams(year, month, { day: date })
  }

  const markSummarySeen = () => {
    setViewedSummaries((current) => {
      if (current.has(monthKey)) {
        return current
      }
      const next = new Set(current)
      next.add(monthKey)
      return next
    })
  }

  const handleCloseSummary = () => {
    markSummarySeen()
    setRecapOpen(false)
  }

  return (
    <section className="page">
      <EmailVerificationBanner />
      {unlockedToast.length > 0 ? (
        <Alert variant="success">
          <div className="achievement-unlock-toast">
            <strong>{t('achievements.unlockedToastTitle')}</strong>
            <ul>
              {unlockedToast.map((item) => (
                <li key={item.id}>
                  <span aria-hidden="true">{item.icon || '🏆'}</span> {item.name}
                </li>
              ))}
            </ul>
            <Link to="/achievements">{t('achievements.viewAll')}</Link>
          </div>
        </Alert>
      ) : null}

      <header className="page-header entries-toolbar">
        <MonthControl
          label={formatHeading(year, month)}
          sizeLabels={monthTitleSizeLabels}
          previousLabel={t('calendar.previousMonth')}
          nextLabel={t('calendar.nextMonth')}
          onPrevious={goToPreviousMonth}
          onNext={goToNextMonth}
          canGoNext={canGoNextMonth}
        />
        <div className="entries-toolbar-actions">
          <IconButton
            className="entries-search-toggle"
            label={showSearchField ? t('entries.searchClose') : t('entries.searchPlaceholder')}
            size="sm"
            variant="ghost"
            isActive={showSearchField}
            aria-expanded={showSearchField}
            onClick={() => {
              if (showSearchField) {
                setSearchInput('')
                setSearchOpen(false)
                return
              }
              setSearchOpen(true)
            }}
          >
            <SearchIcon />
          </IconButton>
          <IconButton
            label={t('entries.favoritesOnly')}
            size="sm"
            variant="ghost"
            isActive={favoritesOnly}
            className={favoritesOnly ? 'is-favorite' : ''}
            aria-pressed={favoritesOnly}
            disabled={isSearchMode}
            onClick={() => setFavoritesOnly((value) => !value)}
          >
            <HeartIcon filled={favoritesOnly} />
          </IconButton>
          <IconLinkButton
            className="entries-new-icon"
            label={t('entries.newEntry')}
            to="/entries/new"
            size="sm"
          >
            <PlusIcon />
          </IconLinkButton>
        </div>
        <div
          className={`entries-search${showSearchField ? ' is-open' : ''}${searchInput ? ' has-clear' : ''}`}
        >
          <input
            ref={searchInputRef}
            type="search"
            className="form-input entries-search-input"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder={t('entries.searchPlaceholder')}
            aria-label={t('entries.searchPlaceholder')}
          />
          {searchInput ? (
            <button
              type="button"
              className="entries-search-clear"
              onClick={() => {
                setSearchInput('')
                setSearchOpen(false)
              }}
              aria-label={t('entries.searchClear')}
            >
              ×
            </button>
          ) : null}
        </div>
      </header>

      {companionGreeting || (showStreak && streakDays != null) ? (
        <div className="entries-hero">
          {companionGreeting ? (
            <p className="companion-line">{companionGreeting}</p>
          ) : null}
          {showStreak && streakDays != null ? (
            <StreakBadge days={streakDays} loggedToday={streakLoggedToday} />
          ) : null}
        </div>
      ) : null}

      <PageErrorAlert error={error} />

      {diaryAccess && !isSearchMode ? (
        <div className={isCalendarLoading ? 'calendar-panel is-refreshing' : 'calendar-panel'}>
          <div
            className="segmented-control calendar-mode-tabs"
            role="group"
            aria-label={t('calendar.modeGroup')}
          >
            <button
              type="button"
              className={`segmented-control-option${calendarMode === 'moods' ? ' is-active' : ''}`}
              aria-pressed={calendarMode === 'moods'}
              onClick={() => setCalendarMode('moods')}
            >
              {t('calendar.modeMoods')}
            </button>
            <button
              type="button"
              className={`segmented-control-option${calendarMode === 'goals' ? ' is-active' : ''}`}
              aria-pressed={calendarMode === 'goals'}
              onClick={() => setCalendarMode('goals')}
            >
              {t('calendar.modeGoals')}
            </button>
          </div>
          {isCalendarLoading && calendarDays.length === 0 && goalCalendarDays.length === 0 ? (
            <p className="muted calendar-panel-status">{t('common.loadingCalendar')}</p>
          ) : (
            <MonthCalendar
              year={year}
              month={month}
              timeZone={timeZone}
              mode={calendarMode}
              moodDays={calendarDays}
              goalDays={goalCalendarDays}
              goalsById={goalsById}
              onDayWithEntries={handleDayWithEntries}
              onSelectWeekDay={
                calendarMode === 'goals' && goalStatsPeriod === 'week'
                  ? handleSelectWeekDay
                  : undefined
              }
            />
          )}
        </div>
      ) : null}

      {diaryAccess && !isSearchMode ? (
        calendarMode === 'goals' ? (
          isGoalStatsLoading && goalStatsItems.length === 0 ? (
            <p className="muted">{t('common.loadingGoalStats')}</p>
          ) : (
            <GoalPeriodStats
              items={goalStatsItems}
              period={goalStatsPeriod}
              periodDays={goalStatsPeriodDays}
              timeZone={timeZone}
              isCurrentPeriod={isCurrentGoalPeriod}
              isRefreshing={isGoalStatsLoading}
              weekLabel={weekLabel}
              canGoPreviousWeek={canGoPreviousWeek}
              canGoNextWeek={canGoNextWeek}
              onPreviousWeek={goToPreviousWeek}
              onNextWeek={goToNextWeek}
              onPeriodChange={setGoalStatsPeriod}
            />
          )
        ) : isStatsLoading ? (
          <p className="muted">{t('common.loadingStats')}</p>
        ) : stats ? (
          <EmotionStatsBarChart
            stats={stats}
            todayDate={todayKey(timeZone)}
            canAddToday={isCurrentMonthView}
            emptyPrompt={emptyPromptCopy}
            headerAction={
              canPlaySummary ? (
                <button
                  type="button"
                  className={
                    summarySeen
                      ? 'button button-secondary button-small month-summary-replay'
                      : 'month-summary-invite'
                  }
                  onClick={() => setRecapOpen(true)}
                  aria-label={summarySeen ? t('monthSummary.replay') : t('monthSummary.buttonAria')}
                >
                  <SparkleIcon />
                  <span>{summarySeen ? t('monthSummary.replay') : t('monthSummary.button')}</span>
                </button>
              ) : null
            }
          />
        ) : null
      ) : null}

      {diaryAccess && !isSearchMode ? (
        <PatternInsights
          insights={insights}
          isLoading={isInsightsLoading}
          highlightId={focusEntryId ? insights?.items[0]?.id : null}
          isCurrentPeriod={isCurrentMonthView}
        />
      ) : null}

      {recapOpen && stats ? (
        <MonthSummaryOverlay
          open={recapOpen}
          monthLabel={formatHeading(year, month)}
          year={year}
          month={month}
          stats={stats}
          days={calendarDays}
          highlight={insights?.items[0] ?? null}
          onClose={handleCloseSummary}
        />
      ) : null}

      {isLoading ? (
        <p className="muted">{t('common.loadingEntries')}</p>
      ) : diaryAccess && entries.length === 0 && (isSearchMode || favoritesOnly || !stats) ? (
        <div className="entry-feed">
          <section className="day-section">
            <p className="muted entry-feed-empty">
              {isSearchMode
                ? t('entries.searchNoResults')
                : favoritesOnly
                  ? t('entries.noFavoritesThisMonth')
                  : emptyMonthCopy}
            </p>
          </section>
        </div>
      ) : null}

      {isSearchMode ? (
        <div className="entry-feed">
          {entries.length > 0 ? (
            <section className="day-section" id="search-results">
              <h2 className="day-heading">{t('entries.searchResults')}</h2>
              <ul className="entry-list">
                {entries.map((entry) => (
                  <li key={entry.id} id={`entry-${entry.id}`}>
                    <EntryRow
                      entry={entry}
                      timeLabel={`${formatDayHeading(entry.recorded_at, timeZone, dateLocale)} ${formatTime(entry.recorded_at, timeZone, dateLocale)}`}
                      timeZone={timeZone}
                      onDelete={handleDelete}
                      onToggleFavorite={handleToggleFavorite}
                    />
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      ) : (
      <div className="entry-feed">
        {groupedEntries.map(([key, dayEntries]) => {
          const dayWash = buildGradientWashFromScores(
            dayEntries,
            (_score, entry) => entryMoodColor(entry, scores),
            dayWashRecipe(colorScheme),
          )
          return (
            <section
              key={key}
              id={`day-${key}`}
              className="day-section"
              style={dayWash ?? undefined}
            >
              <h2 className="day-heading">
                {formatDayHeading(dayEntries[0].recorded_at, timeZone, dateLocale)}
              </h2>
              <ul className="entry-list">
                {dayEntries.map((entry) => (
                  <li key={entry.id} id={`entry-${entry.id}`}>
                    <EntryRow
                      entry={entry}
                      timeLabel={formatTime(entry.recorded_at, timeZone, dateLocale)}
                      timeZone={timeZone}
                      onDelete={handleDelete}
                      onToggleFavorite={handleToggleFavorite}
                    />
                  </li>
                ))}
              </ul>
              <div className="day-section-footer">
                <Link className="button button-secondary button-small" to={`/entries/new?date=${key}`}>
                  {t('entries.addEntryForDay')}
                </Link>
              </div>
            </section>
          )
        })}
      </div>
      )}

      {!isSearchMode && hasMore && diaryAccess ? (
        <div ref={loadMoreRef} className="load-more-sentinel">
          {isLoadingMore ? <p className="muted">{t('common.loadingMore')}</p> : null}
        </div>
      ) : null}
    </section>
  )
}
