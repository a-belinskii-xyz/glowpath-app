import { useMemo } from 'react'
import { Link } from 'react-router-dom'

import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { buildMonthCalendarCells, isFutureDate, todayKey } from '../lib/datetime'
import { getMoodScoreStyle } from '../lib/moodScale'
import { MoodScoreIcon } from './MoodScoreIcon'
import type { CalendarDayPublic } from '../types/mood'

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
  const { t } = useLocale()
  const { scores: scoreStyles } = useMoodPreferences()
  const weekdays = t('calendar.weekdays').split('|')
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
    <div className="month-calendar" role="grid" aria-label={t('calendar.ariaLabel')}>
      <div className="month-calendar-weekdays" role="row">
        {weekdays.map((label) => (
          <div key={label} className="month-calendar-weekday" role="columnheader">
            {label}
          </div>
        ))}
      </div>
      <div className="month-calendar-grid" role="rowgroup">
        {cells.map((cell) => {
          const dayData = cell.date ? daysByDate.get(cell.date) : undefined
          const dayScores = dayData?.scores ?? []
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
                    ? t('calendar.cellWithEntries', { date: cell.date, count: entryCount })
                    : canInteract
                      ? t('calendar.cellAddEntry', { date: cell.date })
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
                    {dayScores.map((item, index) => {
                      const style = getMoodScoreStyle(item.score, scoreStyles)
                      return (
                      <span
                        key={`${cell.date}-${index}-${item.score}`}
                        className="month-calendar-emoji"
                        style={{
                          zIndex: dayScores.length - index,
                          filter: `drop-shadow(0 0 0.35rem ${style.color}88)`,
                        }}
                      >
                        <MoodScoreIcon style={style} />
                      </span>
                      )
                    })}
                  </span>
                </button>
              ) : canInteract && cell.date ? (
                <Link
                  className="month-calendar-day-button month-calendar-day-link"
                  to={`/entries/new?date=${cell.date}`}
                  aria-label={t('calendar.addEntryOn', { date: cell.date })}
                >
                  <span className="month-calendar-day">{cell.day}</span>
                  <span className="month-calendar-add" aria-hidden="true">
                    +
                  </span>
                </Link>
              ) : (
                <>
                  <span className="month-calendar-day">{cell.day}</span>
                  {dayScores.length > 0 ? (
                    <span className="month-calendar-emojis" aria-hidden="true">
                      {dayScores.map((item, index) => {
                        const style = getMoodScoreStyle(item.score, scoreStyles)
                        return (
                        <span
                          key={`${cell.date}-${index}-${item.score}`}
                          className="month-calendar-emoji"
                          style={{
                            zIndex: dayScores.length - index,
                            filter: `drop-shadow(0 0 0.35rem ${style.color}88)`,
                          }}
                        >
                          <MoodScoreIcon style={style} />
                        </span>
                        )
                      })}
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
