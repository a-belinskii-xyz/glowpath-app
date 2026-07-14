import { useMemo } from 'react'
import { Link } from 'react-router-dom'

import { buildMonthCalendarCells, isFutureDate, todayKey } from '../lib/datetime'
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
          const canInteract = Boolean(cell.inMonth && cell.date && !isFuture)
          const hasEntries = entryCount > 0

          return (
            <div
              key={cell.key}
              className={[
                'month-calendar-cell',
                cell.inMonth ? '' : 'month-calendar-cell-muted',
                isToday ? 'month-calendar-cell-today' : '',
                isFuture && cell.inMonth ? 'month-calendar-cell-future' : '',
                canInteract ? 'month-calendar-cell-clickable' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              role="gridcell"
              aria-label={
                cell.date
                  ? hasEntries
                    ? `${cell.date}, ${entryCount} entries`
                    : canInteract
                      ? `${cell.date}, add entry`
                      : cell.date
                  : undefined
              }
            >
              {canInteract && cell.date && hasEntries ? (
                <button
                  type="button"
                  className="month-calendar-day-button"
                  onClick={() => onDayWithEntries(cell.date!)}
                >
                  <span className="month-calendar-day">{cell.day}</span>
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
                </button>
              ) : canInteract && cell.date ? (
                <Link
                  className="month-calendar-day-button month-calendar-day-link"
                  to={`/entries/new?date=${cell.date}`}
                  aria-label={`Add entry on ${cell.date}`}
                >
                  <span className="month-calendar-day">{cell.day}</span>
                  <span className="month-calendar-add" aria-hidden="true">
                    +
                  </span>
                </Link>
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
            </div>
          )
        })}
      </div>
    </div>
  )
}
