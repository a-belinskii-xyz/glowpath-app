import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  buildMonthCalendarCells,
  formatCalendarDate,
  isFutureDate,
  todayKey,
} from '../lib/datetime'
import type { CalendarDayPublic } from '../types/mood'

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

type MonthCalendarProps = {
  year: number
  month: number
  timeZone: string
  days: CalendarDayPublic[]
  onDayWithEntries: (date: string) => void
}

export function MonthCalendar({
  year,
  month,
  timeZone,
  days,
  onDayWithEntries,
}: MonthCalendarProps) {
  const cells = useMemo(() => buildMonthCalendarCells(year, month), [year, month])
  const daysByDate = useMemo(() => {
    const map = new Map<string, CalendarDayPublic>()
    for (const day of days) {
      map.set(day.date, day)
    }
    return map
  }, [days])
  const today = todayKey(timeZone)

  const [emptyDayMenu, setEmptyDayMenu] = useState<string | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!emptyDayMenu) {
      return
    }

    const handleClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setEmptyDayMenu(null)
      }
    }
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setEmptyDayMenu(null)
      }
    }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKey)
    }
  }, [emptyDayMenu])

  const handleDayClick = (date: string, entryCount: number) => {
    if (isFutureDate(date, timeZone)) {
      return
    }
    if (entryCount > 0) {
      setEmptyDayMenu(null)
      onDayWithEntries(date)
      return
    }
    setEmptyDayMenu((current) => (current === date ? null : date))
  }

  return (
    <div className="month-calendar" role="grid" aria-label="Mood calendar">
      <div className="month-calendar-weekdays" role="row">
        {WEEKDAYS.map((label) => (
          <div key={label} className="month-calendar-weekday" role="columnheader">
            {label}
          </div>
        ))}
      </div>
      <div className="month-calendar-grid" role="rowgroup">
        {cells.map((cell) => {
          const dayData = cell.date ? daysByDate.get(cell.date) : undefined
          const scores = dayData?.scores ?? []
          const entryCount = dayData?.entry_count ?? 0
          const isToday = cell.date === today
          const isFuture = cell.date ? isFutureDate(cell.date, timeZone) : false
          const isClickable = Boolean(cell.inMonth && cell.date && !isFuture)
          const menuOpen = cell.date !== null && emptyDayMenu === cell.date

          return (
            <div
              key={cell.key}
              className={[
                'month-calendar-cell',
                cell.inMonth ? '' : 'month-calendar-cell-muted',
                isToday ? 'month-calendar-cell-today' : '',
                isFuture && cell.inMonth ? 'month-calendar-cell-future' : '',
                isClickable ? 'month-calendar-cell-clickable' : '',
                menuOpen ? 'month-calendar-cell-menu-open' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              role="gridcell"
              aria-label={
                cell.date
                  ? scores.length > 0
                    ? `${cell.date}, ${entryCount} entries`
                    : cell.date
                  : undefined
              }
            >
              {isClickable && cell.date ? (
                <button
                  type="button"
                  className="month-calendar-day-button"
                  onClick={() => handleDayClick(cell.date!, entryCount)}
                  aria-haspopup={entryCount === 0 ? 'menu' : undefined}
                  aria-expanded={entryCount === 0 ? menuOpen : undefined}
                >
                  <span className="month-calendar-day">{cell.day}</span>
                  {scores.length > 0 ? (
                    <span className="month-calendar-emojis" aria-hidden="true">
                      {scores.map((item, index) => (
                        <span
                          key={`${cell.date}-${index}-${item.score}`}
                          className="month-calendar-emoji"
                          style={{ zIndex: scores.length - index }}
                        >
                          {item.score_emoji}
                        </span>
                      ))}
                    </span>
                  ) : null}
                </button>
              ) : (
                <>
                  <span className="month-calendar-day">{cell.day}</span>
                  {scores.length > 0 ? (
                    <span className="month-calendar-emojis" aria-hidden="true">
                      {scores.map((item, index) => (
                        <span
                          key={`${cell.date}-${index}-${item.score}`}
                          className="month-calendar-emoji"
                          style={{ zIndex: scores.length - index }}
                        >
                          {item.score_emoji}
                        </span>
                      ))}
                    </span>
                  ) : null}
                </>
              )}

              {menuOpen && cell.date ? (
                <div
                  className="month-calendar-day-menu"
                  role="menu"
                  aria-label={`Create entry for ${formatCalendarDate(cell.date)}`}
                  ref={menuRef}
                >
                  <p className="month-calendar-day-menu-text">
                    No entries on {formatCalendarDate(cell.date)}
                  </p>
                  <Link
                    className="entry-overflow-item"
                    role="menuitem"
                    to={`/entries/new?date=${cell.date}`}
                    onClick={() => setEmptyDayMenu(null)}
                  >
                    Create entry at 8:00 PM
                  </Link>
                  <button
                    type="button"
                    className="entry-overflow-item"
                    role="menuitem"
                    onClick={() => setEmptyDayMenu(null)}
                  >
                    Cancel
                  </button>
                </div>
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}
