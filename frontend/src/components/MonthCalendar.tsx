import { useMemo, type CSSProperties, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { moodGlowFilter } from '../design'
import { buildMonthCalendarCells, isFutureDate, todayKey, type CalendarCell } from '../lib/datetime'
import { getMoodScoreStyle } from '../lib/moodScale'
import { weekGoalHighlightStyle } from '../lib/weekGoalHighlight'
import { GoalIcon } from './GoalIcon'
import { MoodScoreIcon } from './MoodScoreIcon'
import type { GoalCalendarDayPublic, GoalPublic, GoalStyle } from '../types/goal'
import type { CalendarDayPublic } from '../types/mood'

export type CalendarMode = 'moods' | 'goals'

/** Keep day cells calm: show a few marks, then +N. */
const MAX_VISIBLE_MARKS = 3

type MonthCalendarProps = {
  year: number
  month: number
  timeZone: string
  mode: CalendarMode
  moodDays: CalendarDayPublic[]
  goalDays: GoalCalendarDayPublic[]
  goalsById: Map<string, GoalPublic>
  /** Inclusive Monday `YYYY-MM-DD` of the week to highlight (goals + week stats). */
  highlightWeekStart?: string | null
  /** Exclusive next-Monday end of the highlighted week. */
  highlightWeekEnd?: string | null
  onDayWithEntries: (date: string) => void
  /** When set, choosing a day also selects its week (goals week mode). */
  onSelectWeekDay?: (date: string) => void
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

function chunkWeeks(cells: CalendarCell[]): CalendarCell[][] {
  const weeks: CalendarCell[][] = []
  for (let i = 0; i < cells.length; i += 7) {
    weeks.push(cells.slice(i, i + 7))
  }
  return weeks
}

function weekIsHighlighted(
  week: CalendarCell[],
  highlightWeekStart: string | null | undefined,
  highlightWeekEnd: string | null | undefined,
): boolean {
  if (!highlightWeekStart || !highlightWeekEnd) {
    return false
  }
  return week.some(
    (cell) =>
      cell.date != null && cell.date >= highlightWeekStart && cell.date < highlightWeekEnd,
  )
}

function DayMarks({ children, overflow }: { children: ReactNode; overflow: number }) {
  return (
    <span className="month-calendar-emojis" aria-hidden="true">
      {children}
      {overflow > 0 ? <span className="month-calendar-more">+{overflow}</span> : null}
    </span>
  )
}

export function MonthCalendar({
  year,
  month,
  timeZone,
  mode,
  moodDays,
  goalDays,
  goalsById,
  highlightWeekStart = null,
  highlightWeekEnd = null,
  onDayWithEntries,
  onSelectWeekDay,
}: MonthCalendarProps) {
  const { t } = useLocale()
  const { scores: scoreStyles } = useMoodPreferences()
  const weekdays = t('calendar.weekdays').split('|')
  const cells = useMemo(() => buildMonthCalendarCells(year, month), [year, month])
  const weeks = useMemo(() => chunkWeeks(cells), [cells])
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
  const showWeekHighlight = mode === 'goals' && Boolean(highlightWeekStart && highlightWeekEnd)

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
        {weeks.map((week, weekIndex) => {
          const highlighted = showWeekHighlight && weekIsHighlighted(week, highlightWeekStart, highlightWeekEnd)
          const highlightStyle = highlighted
            ? weekGoalHighlightStyle(
                week.map((cell) => cell.date),
                goalDaysByDate,
                goalsById,
              )
            : null

          return (
            <div
              key={`week-${weekIndex}`}
              className={`month-calendar-week${highlighted ? ' is-week-highlighted' : ''}`}
              role="row"
              style={
                highlightStyle
                  ? ({
                      '--week-highlight-gradient': highlightStyle.backgroundImage,
                      '--week-strip-gradient': highlightStyle.stripImage,
                    } as CSSProperties)
                  : undefined
              }
            >
              {week.map((cell) => {
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
                const inHighlightWeek =
                  highlighted &&
                  cell.date != null &&
                  highlightWeekStart != null &&
                  highlightWeekEnd != null &&
                  cell.date >= highlightWeekStart &&
                  cell.date < highlightWeekEnd

                const marks =
                  mode === 'goals' ? (
                    <DayMarks overflow={Math.max(0, dayGoals.length - MAX_VISIBLE_MARKS)}>
                      {dayGoals.slice(0, MAX_VISIBLE_MARKS).map((item, index) => {
                        const goal = goalsById.get(item.goal_id)
                        const style = goalStyleFrom(goal)
                        return (
                          <span
                            key={`${cell.date}-${index}-${item.goal_id}`}
                            className="month-calendar-emoji"
                            style={{
                              zIndex: MAX_VISIBLE_MARKS - index,
                              filter: moodGlowFilter(style.color, 'xs'),
                            }}
                          >
                            <GoalIcon style={style} />
                          </span>
                        )
                      })}
                    </DayMarks>
                  ) : (
                    <DayMarks overflow={Math.max(0, dayScores.length - MAX_VISIBLE_MARKS)}>
                      {dayScores.slice(0, MAX_VISIBLE_MARKS).map((item, index) => {
                        const style = getMoodScoreStyle(item.score, scoreStyles)
                        return (
                          <span
                            key={`${cell.date}-${index}-${item.score}`}
                            className="month-calendar-emoji"
                            style={{
                              zIndex: MAX_VISIBLE_MARKS - index,
                              filter: moodGlowFilter(style.color, 'xs'),
                            }}
                          >
                            <MoodScoreIcon style={style} />
                          </span>
                        )
                      })}
                    </DayMarks>
                  )

                const selectWeek = () => {
                  if (cell.date && onSelectWeekDay) {
                    onSelectWeekDay(cell.date)
                  }
                }

                return (
                  <div
                    key={cell.key}
                    className={[
                      'month-calendar-cell',
                      cell.inMonth ? '' : 'month-calendar-cell-muted',
                      isToday ? 'month-calendar-cell-today' : '',
                      isFuture && cell.inMonth ? 'month-calendar-cell-future' : '',
                      canInteract ? 'month-calendar-cell-clickable' : '',
                      inHighlightWeek ? 'month-calendar-cell-in-week' : '',
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
                        onClick={() => {
                          selectWeek()
                          onDayWithEntries(cell.date!)
                        }}
                      >
                        <span className="month-calendar-day">{cell.day}</span>
                        {marks}
                      </button>
                    ) : canInteract && cell.date ? (
                      onSelectWeekDay ? (
                        <button
                          type="button"
                          className="month-calendar-day-button"
                          onClick={selectWeek}
                          aria-label={t('calendar.selectWeekDay', { date: cell.date })}
                        >
                          <span className="month-calendar-day">{cell.day}</span>
                        </button>
                      ) : (
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
                      )
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
          )
        })}
      </div>
    </div>
  )
}
