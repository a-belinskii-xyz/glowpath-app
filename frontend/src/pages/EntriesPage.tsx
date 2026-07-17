import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { deleteMoodEntry, getMoodEntryCalendar, getMoodEntryStats, listMoodEntries, patchMoodEntry } from '../api/moodEntries'
import { getGoalCalendar, listGoals } from '../api/goals'
import { Alert } from '../components/Alert'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { EmotionStatsBarChart } from '../components/EmotionStatsBarChart'
import { EntryActionMenu } from '../components/EntryActionMenu'
import { EntryAttachmentThumbs } from '../components/EntryAttachmentThumbs'
import { GoalIcon } from '../components/GoalIcon'
import { MarkdownNote } from '../components/MarkdownNote'
import { MonthCalendar, type CalendarMode } from '../components/MonthCalendar'
import { MoodScoreIcon } from '../components/MoodScoreIcon'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { intlLocale } from '../i18n/t'
import { ApiError } from '../lib/errors'
import {
  dayKey,
  formatDayHeading,
  formatMonthHeading,
  formatTime,
  formatYearMonthParam,
  getCurrentYearMonth,
  getDayBounds,
  getMonthBounds,
  parseYearMonthParam,
} from '../lib/datetime'
import { dayMoodWashFromScores } from '../lib/dayMoodWash'
import { getMoodScoreColor, getMoodScoreStyle } from '../lib/moodScale'
import type { GoalCalendarDayPublic, GoalPublic } from '../types/goal'
import type { CalendarDayPublic, MoodEntryPublic, MoodEntryStatsResponse } from '../types/mood'

const PAGE_SIZE = 20
const DAY_FETCH_LIMIT = 100

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
  const { locale, t } = useLocale()
  const { scores } = useMoodPreferences()
  const [searchParams, setSearchParams] = useSearchParams()
  const timeZone = user?.timezone ?? 'UTC'
  const dateLocale = intlLocale(locale)

  const initialMonth =
    parseYearMonthParam(searchParams.get('month')) ?? getCurrentYearMonth(timeZone)

  const [year, setYear] = useState(initialMonth.year)
  const [month, setMonth] = useState(initialMonth.month)

  const [calendarDays, setCalendarDays] = useState<CalendarDayPublic[]>([])
  const [goalCalendarDays, setGoalCalendarDays] = useState<GoalCalendarDayPublic[]>([])
  const [goalsById, setGoalsById] = useState<Map<string, GoalPublic>>(() => new Map())
  const [calendarMode, setCalendarMode] = useState<CalendarMode>('moods')
  const [isCalendarLoading, setIsCalendarLoading] = useState(true)

  const [stats, setStats] = useState<MoodEntryStatsResponse | null>(null)
  const [isStatsLoading, setIsStatsLoading] = useState(true)

  const [entries, setEntries] = useState<MoodEntryPublic[]>([])
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [favoritesOnly, setFavoritesOnly] = useState(false)

  const [pendingScrollDay, setPendingScrollDay] = useState<string | null>(
    () => searchParams.get('day'),
  )
  const [pendingScrollEntry, setPendingScrollEntry] = useState<string | null>(
    () => searchParams.get('entry'),
  )

  const loadMoreRef = useRef<HTMLDivElement | null>(null)
  const loadingRef = useRef(false)
  const dayLoadRef = useRef<string | null>(null)

  const monthBounds = useMemo(() => getMonthBounds(year, month, timeZone), [year, month, timeZone])

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
      setYear(nextYear)
      setMonth(nextMonth)
      setPendingScrollDay(null)
      setPendingScrollEntry(null)
      updateMonthParams(nextYear, nextMonth)
    },
    [updateMonthParams],
  )

  useEffect(() => {
    const parsed = parseYearMonthParam(searchParams.get('month'))
    if (!parsed) {
      return
    }
    if (parsed.year !== year || parsed.month !== month) {
      setYear(parsed.year)
      setMonth(parsed.month)
    }
  }, [month, searchParams, year])

  const scrollToDay = useCallback((date: string) => {
    const node = document.getElementById(`day-${date}`)
    if (!node) {
      return false
    }
    // Instant scroll — smooth + infinite loading stops mid-way on long jumps.
    node.scrollIntoView({ behavior: 'auto', block: 'start' })
    node.classList.add('day-section-highlight')
    window.setTimeout(() => node.classList.remove('day-section-highlight'), 1600)
    return true
  }, [])

  const scrollToEntry = useCallback((entryId: string) => {
    const node = document.getElementById(`entry-${entryId}`)
    if (!node) {
      return false
    }
    node.scrollIntoView({ behavior: 'auto', block: 'center' })
    node.classList.add('entry-row-highlight')
    window.setTimeout(() => node.classList.remove('entry-row-highlight'), 1600)
    return true
  }, [])

  const loadCalendar = useCallback(async () => {
    if (!user?.email_verified) {
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
        setError(err instanceof Error ? err.message : t('errors.failedLoadCalendar'))
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
    user?.email_verified,
  ])

  const loadStats = useCallback(async () => {
    if (!user?.email_verified) {
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
        setError(err instanceof Error ? err.message : t('errors.failedLoadStats'))
      }
      setStats(null)
    } finally {
      setIsStatsLoading(false)
    }
  }, [locale, monthBounds.recorded_from, monthBounds.recorded_to, t, user?.email_verified])

  const loadPage = useCallback(
    async (pageOffset: number, replace: boolean) => {
      if (!user?.email_verified) {
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
          setError(err instanceof Error ? err.message : t('errors.failedLoadEntries'))
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
      user?.email_verified,
    ],
  )

  const ensureEntriesFromDay = useCallback(
    async (date: string): Promise<boolean | null> => {
      if (!user?.email_verified) {
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
          setError(err instanceof Error ? err.message : t('errors.failedLoadEntries'))
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
      user?.email_verified,
    ],
  )

  useEffect(() => {
    void loadCalendar()
  }, [loadCalendar])

  useEffect(() => {
    void loadStats()
  }, [loadStats])

  useEffect(() => {
    setEntries([])
    setOffset(0)
    setHasMore(true)
    dayLoadRef.current = null
    void loadPage(0, true)
  }, [loadPage])

  useEffect(() => {
    const node = loadMoreRef.current
    // Pause while jumping to a calendar day/entry — otherwise newly loaded
    // pages shift the target and the scroll stops mid-feed.
    if (
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

  const goToPreviousMonth = () => {
    if (month === 0) {
      setMonthView(year - 1, 11)
      return
    }
    setMonthView(year, month - 1)
  }

  const goToNextMonth = () => {
    if (month === 11) {
      setMonthView(year + 1, 0)
      return
    }
    setMonthView(year, month + 1)
  }

  const handleDelete = async (entryId: string) => {
    try {
      await deleteMoodEntry(entryId)
      setEntries((current) => current.filter((entry) => entry.id !== entryId))
      void loadCalendar()
      void loadStats()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.failedDeleteEntry'))
    }
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
      setError(err instanceof Error ? err.message : t('errors.failedSaveEntry'))
    }
  }

  const handleDayWithEntries = (date: string) => {
    setPendingScrollEntry(null)
    setPendingScrollDay(date)
    updateMonthParams(year, month, { day: date })
  }

  return (
    <section className="page">
      <EmailVerificationBanner />

      <header className="page-header">
        <div className="month-nav">
          <button type="button" className="button button-secondary button-small" onClick={goToPreviousMonth}>
            {t('common.previous')}
          </button>
          <h1>{formatMonthHeading(year, month, dateLocale)}</h1>
          <button type="button" className="button button-secondary button-small" onClick={goToNextMonth}>
            {t('common.next')}
          </button>
        </div>
        <div className="page-header-actions">
          <button
            type="button"
            className={`button button-secondary button-small${favoritesOnly ? ' is-active' : ''}`}
            aria-pressed={favoritesOnly}
            onClick={() => setFavoritesOnly((value) => !value)}
          >
            {t('entries.favoritesOnly')}
          </button>
          <Link className="button" to="/entries/new">
            {t('entries.newEntry')}
          </Link>
        </div>
      </header>

      {error ? <Alert variant="error">{error}</Alert> : null}

      {user?.email_verified ? (
        <>
          <div className="calendar-mode-toggle" role="group" aria-label={t('calendar.modeGroup')}>
            <button
              type="button"
              className={`button button-secondary button-small${calendarMode === 'moods' ? ' is-active' : ''}`}
              aria-pressed={calendarMode === 'moods'}
              onClick={() => setCalendarMode('moods')}
            >
              {t('calendar.modeMoods')}
            </button>
            <button
              type="button"
              className={`button button-secondary button-small${calendarMode === 'goals' ? ' is-active' : ''}`}
              aria-pressed={calendarMode === 'goals'}
              onClick={() => setCalendarMode('goals')}
            >
              {t('calendar.modeGoals')}
            </button>
          </div>
          {isCalendarLoading ? (
            <p className="muted">{t('common.loadingCalendar')}</p>
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
            />
          )}
        </>
      ) : null}

      {user?.email_verified ? (
        isStatsLoading ? (
          <p className="muted">{t('common.loadingStats')}</p>
        ) : stats ? (
          <EmotionStatsBarChart stats={stats} />
        ) : null
      ) : null}

      {isLoading ? (
        <p className="muted">{t('common.loadingEntries')}</p>
      ) : user?.email_verified && entries.length === 0 ? (
        <p className="muted">
          {favoritesOnly ? t('entries.noFavoritesThisMonth') : t('entries.noEntriesThisMonth')}
        </p>
      ) : null}

      <div className="entry-feed">
        {groupedEntries.map(([key, dayEntries]) => {
          const dayWash = dayMoodWashFromScores(dayEntries, (score) => getMoodScoreColor(score, scores))
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
                    <article className="entry-row">
                      <Link className="entry-row-link" to={`/entries/${entry.id}`}>
                        <div className="entry-row-main">
                          <span className="entry-score">
                            {entry.is_favorite ? (
                              <span className="entry-favorite-mark" aria-hidden="true">
                                ★
                              </span>
                            ) : null}
                            <MoodScoreIcon
                              style={getMoodScoreStyle(entry.score, scores)}
                              className="entry-score-icon"
                              fallbackScore={entry.score}
                            />{' '}
                            {entry.score_label}
                          </span>
                          <span className="entry-time">
                            {formatTime(entry.recorded_at, timeZone, dateLocale)}
                          </span>
                        </div>
                        {entry.note ? (
                          <MarkdownNote content={entry.note} compact className="entry-note" />
                        ) : null}
                        {entry.tags.length > 0 ? (
                          <div className="entry-tags">
                            {entry.tags.map((tag) => (
                              <span key={tag.id} className="entry-tag">
                                {tag.label}
                              </span>
                            ))}
                          </div>
                        ) : null}
                        {entry.goals.length > 0 ? (
                          <div className="entry-tags entry-goals">
                            {entry.goals.map((goal) => (
                              <span key={goal.id} className="entry-tag entry-goal">
                                <GoalIcon
                                  style={{
                                    color: goal.color,
                                    icon_type: goal.icon_type,
                                    icon: goal.icon,
                                  }}
                                  className="entry-goal-icon"
                                />
                                {goal.label}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </Link>
                      <div className="entry-row-media">
                        <EntryAttachmentThumbs entryId={entry.id} attachments={entry.attachments} />
                      </div>
                      <div className="entry-row-actions">
                        <EntryActionMenu
                          entry={entry}
                          onDelete={handleDelete}
                          onToggleFavorite={handleToggleFavorite}
                        />
                      </div>
                    </article>
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

      {hasMore && user?.email_verified ? (
        <div ref={loadMoreRef} className="load-more-sentinel">
          {isLoadingMore ? <p className="muted">{t('common.loadingMore')}</p> : null}
        </div>
      ) : null}
    </section>
  )
}
