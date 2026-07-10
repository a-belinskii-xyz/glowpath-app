import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { deleteMoodEntry, listMoodEntries } from '../api/moodEntries'
import { Alert } from '../components/Alert'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { EntryActionMenu } from '../components/EntryActionMenu'
import { EntryAttachmentThumbs } from '../components/EntryAttachmentThumbs'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../lib/errors'
import {
  dayKey,
  formatDayHeading,
  formatMonthHeading,
  formatTime,
  getCurrentYearMonth,
  getMonthBounds,
} from '../lib/datetime'
import type { MoodEntryPublic } from '../types/mood'

const PAGE_SIZE = 20

export function EntriesPage() {
  const { user } = useAuth()
  const timeZone = user?.timezone ?? 'UTC'
  const initialMonth = getCurrentYearMonth(timeZone)

  const [year, setYear] = useState(initialMonth.year)
  const [month, setMonth] = useState(initialMonth.month)

  const [entries, setEntries] = useState<MoodEntryPublic[]>([])
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadMoreRef = useRef<HTMLDivElement | null>(null)
  const loadingRef = useRef(false)

  const monthBounds = useMemo(() => getMonthBounds(year, month, timeZone), [year, month, timeZone])

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
        })

        setEntries((current) =>
          replace ? response.items : [...current, ...response.items],
        )
        setOffset(pageOffset + response.items.length)
        setHasMore(response.items.length === PAGE_SIZE)
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError('Verify your email to view mood entries.')
        } else {
          setError(err instanceof Error ? err.message : 'Failed to load entries')
        }
      } finally {
        setIsLoading(false)
        setIsLoadingMore(false)
        loadingRef.current = false
      }
    },
    [monthBounds.recorded_from, monthBounds.recorded_to, user?.email_verified],
  )

  useEffect(() => {
    setEntries([])
    setOffset(0)
    setHasMore(true)
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete entry')
    }
  }

  return (
    <section className="page">
      <EmailVerificationBanner />

      <header className="page-header">
        <div className="month-nav">
          <button type="button" className="button button-secondary button-small" onClick={goToPreviousMonth}>
            Previous
          </button>
          <h1>{formatMonthHeading(year, month)}</h1>
          <button type="button" className="button button-secondary button-small" onClick={goToNextMonth}>
            Next
          </button>
        </div>
        <Link className="button" to="/entries/new">
          New entry
        </Link>
      </header>

      {error ? <Alert variant="error">{error}</Alert> : null}

      {isLoading ? (
        <p className="muted">Loading entries…</p>
      ) : user?.email_verified && entries.length === 0 ? (
        <p className="muted">No entries for this month yet.</p>
      ) : null}

      <div className="entry-feed">
        {groupedEntries.map(([key, dayEntries]) => (
          <section key={key} className="day-section">
            <h2 className="day-heading">{formatDayHeading(dayEntries[0].recorded_at, timeZone)}</h2>
            <ul className="entry-list">
              {dayEntries.map((entry) => (
                <li key={entry.id}>
                  <article className="entry-row">
                    <div className="entry-row-main">
                      <span className="entry-score">
                        {entry.score_emoji} {entry.score_label}
                      </span>
                      <div className="entry-row-meta">
                        <span className="entry-time">{formatTime(entry.recorded_at, timeZone)}</span>
                        <EntryActionMenu entry={entry} onDelete={handleDelete} />
                      </div>
                    </div>
                    {entry.note ? <p className="entry-note">{entry.note}</p> : null}
                    {entry.tags.length > 0 ? (
                      <div className="entry-tags">
                        {entry.tags.map((tag) => (
                          <span key={tag.id} className="entry-tag">
                            {tag.label}
                          </span>
                        ))}
                      </div>
                    ) : null}
                    <EntryAttachmentThumbs entryId={entry.id} attachments={entry.attachments} />
                  </article>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      {hasMore && user?.email_verified ? (
        <div ref={loadMoreRef} className="load-more-sentinel">
          {isLoadingMore ? <p className="muted">Loading more…</p> : null}
        </div>
      ) : null}
    </section>
  )
}
