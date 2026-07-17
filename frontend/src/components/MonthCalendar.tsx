import { useMemo } from 'react'
import { Link } from 'react-router-dom'

import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { buildMonthCalendarCells, isFutureDate, todayKey } from '../lib/datetime'
import { getMoodScoreStyle } from '../lib/moodScale'
import { GoalIcon } from './GoalIcon'
import { MoodScoreIcon } from './MoodScoreIcon'
import type { GoalCalendarDayPublic, GoalPublic, GoalStyle } from '../types/goal'
import type { CalendarDayPublic } from '../types/mood'

export type CalendarMode = 'moods' | 'goals'

type MonthCalendarProps = {
  year: number
  month: number
  timeZone: string
  mode: CalendarMode
  moodDays: CalendarDayPublic[]
  goalDays: GoalCalendarDayPublic[]
  goalsById: Map<string, GoalPublic>
  onDayWithEntries: (date: string) => void
}

function goalStyleFrom(goal: GoalPublic | undefined): GoalStyle {
  if (!goal) {
    return { color: '#60a5fa', icon_type: 'emoji', icon: '🎯' }
  }
  return {
    color: goal.color,
    icon_type: goal.icon_type,
    icon: goal.icon,
  }
}

export function MonthCalendar({
  year,
  month,
  timeZone,
  mode,
  moodDays,
  goalDays,
  goalsById,
  onDayWithEntries,
}: MonthCalendarProps) {
  const { t } = useLocale()
  const { scores: scoreStyles } = useMoodPreferences()
  const weekdays = t('calendar.weekdays').split('|')
  const cells = useMemo(() => buildMonthCalendarCells(year, month), [year, month])
  const moodDaysByDate = useMemo(() => {
    const map = new Map<string, CalendarDayPublic>()
    for (const day of moodDays) {
      map.set(day.date, day)
    }
    return map
  }, [moodDays])
  const goalDaysByDate = useMemo(() => {
    const map = new Map<string, GoalCalendarDayPublic>()
    for (const day of goalDays) {
      map.set(day.date, day)
    }
    return map
  }, [goalDays])
  const today = todayKey(timeZone)
  const ariaLabel = mode === 'goals' ? t('calendar.ariaLabelGoals') : t('calendar.ariaLabel')

  return (
    <div className="month-calendar" role="grid" aria-label={ariaLabel}>
      <div className="month-calendar-weekdays" role="row">
        {weekdays.map((label) => (
          <div key={label} className="month-calendar-weekday" role="columnheader">
            {label}
          </div>
        ))}
      </div>
      <div className="month-calendar-grid" role="rowgroup">
        {cells.map((cell) => {
          const moodDay = cell.date ? moodDaysByDate.get(cell.date) : undefined
          const goalDay = cell.date ? goalDaysByDate.get(cell.date) : undefined
          const dayScores = moodDay?.scores ?? []
          const dayGoals = goalDay?.goals ?? []
          const entryCount =
            mode === 'goals' ? (goalDay?.entry_count ?? 0) : (moodDay?.entry_count ?? 0)
          const markCount = mode === 'goals' ? dayGoals.length : dayScores.length
          const isToday = cell.date === today
          const isFuture = cell.date ? isFutureDate(cell.date, timeZone) : false
          const canInteract = Boolean(cell.inMonth && cell.date && !isFuture)
          const hasEntries = entryCount > 0

          const marks =
            mode === 'goals' ? (
              <span className="month-calendar-emojis" aria-hidden="true">
                {dayGoals.map((item, index) => {
                  const goal = goalsById.get(item.goal_id)
                  const style = goalStyleFrom(goal)
                  return (
                    <span
                      key={`${cell.date}-${index}-${item.goal_id}`}
                      className="month-calendar-emoji"
                      style={{
                        zIndex: dayGoals.length - index,
                        filter: `drop-shadow(0 0 0.35rem ${style.color}88)`,
                      }}
                    >
                      <GoalIcon style={style} />
                    </span>
                  )
                })}
              </span>
            ) : (
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
            )

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
                  {marks}
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
                  {markCount > 0 ? marks : null}
                </>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
