import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { deleteMoodEntry, getMoodEntryCalendar, getMoodEntryStats, listMoodEntries, patchMoodEntry } from '../api/moodEntries'
import { Alert } from '../components/Alert'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { EmotionStatsBarChart } from '../components/EmotionStatsBarChart'
import { EntryActionMenu } from '../components/EntryActionMenu'
import { EntryAttachmentThumbs } from '../components/EntryAttachmentThumbs'
import { MarkdownNote } from '../components/MarkdownNote'
import { MonthCalendar } from '../components/MonthCalendar'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { intlLocale } from '../i18n/t'
import { ApiError } from '../lib/errors'
import {
  dayKey,
  formatDayHeading,
  formatMonthHeading,
  formatTime,
  getCurrentYearMonth,
  getMonthBounds,
} from '../lib/datetime'
import type { CalendarDayPublic, MoodEntryPublic, MoodEntryStatsResponse } from '../types/mood'

const PAGE_SIZE = 20

export function EntriesPage() {
  const { user } = useAuth()
  const { locale, t } = useLocale()
  const timeZone = user?.timezone ?? 'UTC'
  const dateLocale = intlLocale(locale)
  const initialMonth = getCurrentYearMonth(timeZone)

  const [year, setYear] = useState(initialMonth.year)
  const [month, setMonth] = useState(initialMonth.month)

  const [calendarDays, setCalendarDays] = useState<CalendarDayPublic[]>([])
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

  const loadMoreRef = useRef<HTMLDivElement | null>(null)
  const loadingRef = useRef(false)
  const pendingScrollDayRef = useRef<string | null>(null)

  const monthBounds = useMemo(() => getMonthBounds(year, month, timeZone), [year, month, timeZone])

  const scrollToDay = useCallback((date: string) => {
    const node = document.getElementById(`day-${date}`)
    if (!node) {
      return false
    }
    node.scrollIntoView({ behavior: 'smooth', block: 'start' })
    node.classList.add('day-section-highlight')
    window.setTimeout(() => node.classList.remove('day-section-highlight'), 1600)
    pendingScrollDayRef.current = null
    return true
  }, [])

  const loadCalendar = useCallback(async () => {
    if (!user?.email_verified) {
      setCalendarDays([])
      setIsCalendarLoading(false)
      return
    }

    setIsCalendarLoading(true)
    try {
      const response = await getMoodEntryCalendar({
        recorded_from: monthBounds.recorded_from,
        recorded_to: monthBounds.recorded_to,
      })
      setCalendarDays(response.days)
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 403)) {
        setError(err instanceof Error ? err.message : t('errors.failedLoadCalendar'))
      }
      setCalendarDays([])
    } finally {
      setIsCalendarLoading(false)
    }
  }, [locale, monthBounds.recorded_from, monthBounds.recorded_to, t, user?.email_verified])

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
          replace ? response.items : [...current, ...response.items],
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
    pendingScrollDayRef.current = null
    void loadPage(0, true)
  }, [loadPage])

  useEffect(() => {
    const node = loadMoreRef.current
    if (!node || !hasMore || isLoading || isLoadingMore) {
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
  }, [hasMore, isLoading, isLoadingMore, loadPage, offset])

  useEffect(() => {
    const pending = pendingScrollDayRef.current
    if (!pending || isLoading) {
      return
    }
    if (scrollToDay(pending)) {
      return
    }
    if (!hasMore && !isLoadingMore) {
      pendingScrollDayRef.current = null
    }
  }, [entries, hasMore, isLoading, isLoadingMore, scrollToDay])

  // Keep loading pages while waiting for a day section to appear after calendar click.
  useEffect(() => {
    if (!pendingScrollDayRef.current || !hasMore || isLoading || isLoadingMore) {
      return
    }
    void loadPage(offset, false)
  }, [entries, hasMore, isLoading, isLoadingMore, loadPage, offset])

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
      setYear((value) => value - 1)
      setMonth(11)
      return
    }
    setMonth((value) => value - 1)
  }

  const goToNextMonth = () => {
    if (month === 11) {
      setYear((value) => value + 1)
      setMonth(0)
      return
    }
    setMonth((value) => value + 1)
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
          : [...current, previous].sort(
              (a, b) => new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime(),
            )
        return restored
      })
      setError(err instanceof Error ? err.message : t('errors.failedSaveEntry'))
    }
  }

  const handleDayWithEntries = (date: string) => {
    if (!scrollToDay(date)) {
      pendingScrollDayRef.current = date
    }
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
        isCalendarLoading ? (
          <p className="muted">{t('common.loadingCalendar')}</p>
        ) : (
          <MonthCalendar
            year={year}
            month={month}
            timeZone={timeZone}
            days={calendarDays}
            onDayWithEntries={handleDayWithEntries}
          />
        )
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
        {groupedEntries.map(([key, dayEntries]) => (
          <section key={key} id={`day-${key}`} className="day-section">
            <h2 className="day-heading">
              {formatDayHeading(dayEntries[0].recorded_at, timeZone, dateLocale)}
            </h2>
            <ul className="entry-list">
              {dayEntries.map((entry) => (
                <li key={entry.id}>
                  <article className="entry-row">
                    <Link className="entry-row-link" to={`/entries/${entry.id}`}>
                      <div className="entry-row-main">
                        <span className="entry-score">
                          {entry.is_favorite ? (
                            <span className="entry-favorite-mark" aria-hidden="true">
                              ★
                            </span>
                          ) : null}
                          {entry.score_emoji} {entry.score_label}
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
        ))}
      </div>

      {hasMore && user?.email_verified ? (
        <div ref={loadMoreRef} className="load-more-sentinel">
          {isLoadingMore ? <p className="muted">{t('common.loadingMore')}</p> : null}
        </div>
      ) : null}
    </section>
  )
}
