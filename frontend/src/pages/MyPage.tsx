import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { deleteGoalCheckin, listGoals, setGoalCheckin } from '../api/goals'
import { createMoodEntry, listMoodEntries, patchMoodEntry } from '../api/moodEntries'
import { EditorDrawer } from '../components/EditorDrawer'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { GoalIcon } from '../components/GoalIcon'
import { MoodScoreIcon } from '../components/MoodScoreIcon'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { StableButtonLabel } from '../components/StableButtonLabel'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { intlLocale } from '../i18n/t'
import {
  dayKey,
  formatCalendarDate,
  formatWeekHeading,
  getIsoWeekBounds,
  instantToIsoInTimezone,
  shiftDateKey,
  todayKey,
} from '../lib/datetime'
import { formatApiError } from '../lib/errors'
import { markdownToPlainText } from '../lib/markdownPlainText'
import { getMoodScoreOptions } from '../lib/moodScale'
import type { GoalCheckinLevel, GoalPublic } from '../types/goal'
import type { MoodEntryPublic } from '../types/mood'

const WINS_SHOWN = 3

function isActiveOn(goal: GoalPublic, day: string): boolean {
  return goal.starts_on <= day && (goal.ends_on == null || goal.ends_on >= day)
}

function levelOn(goal: GoalPublic, day: string): GoalCheckinLevel | null {
  return goal.week_marks.find((mark) => mark.date === day)?.level ?? null
}

function formatDay(day: string, dateLocale: string, options: Intl.DateTimeFormatOptions): string {
  const [year, month, date] = day.split('-').map(Number)
  return new Intl.DateTimeFormat(dateLocale, { ...options, timeZone: 'UTC' }).format(
    new Date(Date.UTC(year, month - 1, date)),
  )
}

function weekdayShort(day: string, dateLocale: string): string {
  return formatDay(day, dateLocale, { weekday: 'short' })
}

/**
 * A calm home for goals and small wins (GP-44): the week's goals with a one-tap
 * mark, and the entries starred as "what worked out".
 */
export function MyPage() {
  const { user } = useAuth()
  const { locale, t } = useLocale()
  const { scores } = useMoodPreferences()
  const timeZone = user?.timezone ?? 'UTC'
  const dateLocale = intlLocale(locale)
  const today = todayKey(timeZone)
  const week = getIsoWeekBounds(today, timeZone)
  const weekDays = useMemo(
    () => Array.from({ length: 7 }, (_, index) => shiftDateKey(week.period_start, index)),
    [week.period_start],
  )

  const [goals, setGoals] = useState<GoalPublic[]>([])
  const [wins, setWins] = useState<MoodEntryPublic[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [markGoal, setMarkGoal] = useState<GoalPublic | null>(null)
  const [markLevel, setMarkLevel] = useState<GoalCheckinLevel>('partial')
  const [markError, setMarkError] = useState<string | null>(null)
  const [isMarking, setIsMarking] = useState(false)
  const [winOpen, setWinOpen] = useState(false)

  const loadWins = useCallback(async () => {
    const response = await listMoodEntries({ is_favorite: true, limit: WINS_SHOWN })
    setWins(response.items)
  }, [])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setIsLoading(true)
      try {
        const [goalList, favorites] = await Promise.all([
          listGoals({ progressOn: today }),
          listMoodEntries({ is_favorite: true, limit: WINS_SHOWN }),
        ])
        if (cancelled) return
        setGoals(goalList.items)
        setWins(favorites.items)
        setError(null)
      } catch (err) {
        if (!cancelled) setError(formatApiError(err, t, 'errors.failedLoadGoals'))
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [today, locale, t])

  const activeGoals = goals.filter((goal) => isActiveOn(goal, today))
  usePageAmbientGlow(activeGoals.map((goal) => goal.color))

  const replaceGoal = (updated: GoalPublic) => {
    setGoals((current) => current.map((goal) => (goal.id === updated.id ? updated : goal)))
  }

  const openMark = (goal: GoalPublic) => {
    setMarkGoal(goal)
    setMarkLevel(levelOn(goal, today) ?? 'partial')
    setMarkError(null)
  }

  const saveMark = async (level: GoalCheckinLevel | null) => {
    if (!markGoal) return
    setIsMarking(true)
    setMarkError(null)
    try {
      const updated =
        level === null
          ? await deleteGoalCheckin(markGoal.id, today)
          : await setGoalCheckin(markGoal.id, today, level)
      replaceGoal(updated)
      setMarkGoal(null)
    } catch (err) {
      setMarkError(formatApiError(err, t, 'errors.failedSave'))
    } finally {
      setIsMarking(false)
    }
  }

  const formatWinDate = (iso: string) => {
    const day = dayKey(iso, timeZone)
    if (day === today) return t('myPage.today')
    if (day === shiftDateKey(today, -1)) return t('myPage.yesterday')
    return formatDay(day, dateLocale, {
      day: 'numeric',
      month: 'long',
      ...(day.slice(0, 4) === today.slice(0, 4) ? {} : { year: 'numeric' }),
    })
  }

  return (
    <section className="page page-my">
      <EmailVerificationBanner />

      <header className="page-header my-header">
        <div>
          <h1>{t('myPage.title')}</h1>
          <p className="my-week muted">
            {formatWeekHeading(week.period_start, week.period_end, dateLocale)}
          </p>
        </div>
      </header>

      <p className="my-hello">{t('myPage.hello')}</p>
      <PageErrorAlert error={error} />

      <section className="card my-card" aria-labelledby="my-goals-title">
        <div className="my-card-head">
          <h2 id="my-goals-title">{t('myPage.goalsTitle')}</h2>
          <Link to="/goals" className="my-card-link">
            {t('myPage.allGoals')}
          </Link>
        </div>
        {isLoading ? (
          <p className="muted">{t('common.loading')}</p>
        ) : activeGoals.length === 0 ? (
          <p className="my-empty">
            {t('myPage.goalsEmpty')}{' '}
            <Link to="/goals">{t('myPage.addGoal')}</Link>
          </p>
        ) : (
          <ul className="my-goal-list">
            {activeGoals.map((goal) => {
              const todayLevel = levelOn(goal, today)
              return (
                <li key={goal.id} className="my-goal">
                  <span
                    className="my-goal-icon"
                    style={{ backgroundColor: `color-mix(in oklab, ${goal.color} 18%, transparent)` }}
                  >
                    <GoalIcon
                      style={{ color: goal.color, icon_type: goal.icon_type, icon: goal.icon }}
                    />
                  </span>
                  <div className="my-goal-body">
                    <span className="my-goal-name">{goal.label}</span>
                    {goal.partial_label ? (
                      <span className="my-goal-hint">
                        {t('myPage.partialHint', { label: goal.partial_label })}
                      </span>
                    ) : goal.times_per_week < 7 ? (
                      <span className="my-goal-hint">
                        {t('myPage.timesPerWeek', { count: goal.times_per_week })}
                      </span>
                    ) : null}
                    <span className="my-goal-days" style={{ ['--goal-color' as string]: goal.color }}>
                      {weekDays.map((day) => {
                        const level = levelOn(goal, day)
                        // Days outside the goal's dates are not "missed"; they stay quietly grey.
                        if (!isActiveOn(goal, day)) {
                          return (
                            <span key={day} className="my-day is-before" aria-hidden>
                              {weekdayShort(day, dateLocale)}
                            </span>
                          )
                        }
                        return (
                          <span
                            key={day}
                            className={`my-day${level ? ` is-${level}` : ''}${day === today ? ' is-today' : ''}`}
                            title={formatCalendarDate(day, dateLocale)}
                          >
                            {weekdayShort(day, dateLocale)}
                          </span>
                        )
                      })}
                    </span>
                  </div>
                  <button
                    type="button"
                    className={`my-goal-mark${todayLevel ? ` is-${todayLevel}` : ''}`}
                    style={{ ['--goal-color' as string]: goal.color }}
                    aria-label={t('myPage.markAria', { label: goal.label })}
                    onClick={() => openMark(goal)}
                  >
                    ✓
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <section className="card my-card" aria-labelledby="my-wins-title">
        <div className="my-card-head">
          <h2 id="my-wins-title">{t('myPage.winsTitle')}</h2>
          {wins.length > 0 ? (
            <Link to="/?favorites=1" className="my-card-link">
              {t('myPage.allWins')}
            </Link>
          ) : null}
        </div>
        {isLoading ? null : wins.length === 0 ? (
          <p className="my-empty">{t('myPage.winsEmpty')}</p>
        ) : (
          <ul className="my-win-list">
            {wins.map((entry) => (
              <li key={entry.id}>
                <Link to={`/entries/${entry.id}`} className="my-win">
                  <span className="my-win-star" aria-hidden>
                    ★
                  </span>
                  <span className="my-win-body">
                    <span className="my-win-text">
                      {markdownToPlainText(entry.note ?? '').trim() || entry.score_label}
                    </span>
                    <span className="my-win-date">
                      <span
                        className="my-win-mood"
                        style={{ backgroundColor: entry.score_color }}
                        aria-hidden
                      />
                      {formatWinDate(entry.recorded_at)}
                    </span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <button type="button" className="my-write" onClick={() => setWinOpen(true)}>
        {t('myPage.write')}
      </button>

      <EditorDrawer
        open={markGoal !== null}
        title={markGoal?.label ?? ''}
        description={formatDay(today, dateLocale, { weekday: 'long', day: 'numeric', month: 'long' })}
        accentColors={markGoal ? [markGoal.color] : []}
        onClose={() => {
          if (!isMarking) setMarkGoal(null)
        }}
        footer={
          <div className="button-row">
            <button
              type="button"
              className="button my-primary"
              disabled={isMarking}
              onClick={() => void saveMark(markLevel)}
            >
              <StableButtonLabel
                active={isMarking ? t('common.saving') : t('myPage.mark')}
                labels={[t('myPage.mark'), t('common.saving')]}
              />
            </button>
            {markGoal && levelOn(markGoal, today) ? (
              <button
                type="button"
                className="button button-secondary"
                disabled={isMarking}
                onClick={() => void saveMark(null)}
              >
                {t('myPage.unmark')}
              </button>
            ) : null}
          </div>
        }
      >
        <PageErrorAlert error={markError} />
        <div className="my-levels" role="radiogroup" aria-label={t('myPage.markAria', { label: markGoal?.label ?? '' })}>
          {(['partial', 'full'] as const).map((level) => (
            <button
              key={level}
              type="button"
              role="radio"
              aria-checked={markLevel === level}
              className={`my-level${markLevel === level ? ' is-selected' : ''}`}
              style={{ ['--goal-color' as string]: markGoal?.color }}
              onClick={() => setMarkLevel(level)}
            >
              <span className={`my-day my-level-dot is-${level}`} aria-hidden />
              <span>
                <strong>{t(level === 'partial' ? 'myPage.levelPartial' : 'myPage.levelFull')}</strong>
                <span className="my-level-hint">
                  {level === 'partial'
                    ? markGoal?.partial_label || t('myPage.levelPartialHint')
                    : t('myPage.levelFullHint')}
                </span>
              </span>
            </button>
          ))}
        </div>
        <p className="my-gentle muted">{t('myPage.noPenalty')}</p>
      </EditorDrawer>

      <WinDrawer
        open={winOpen}
        timeZone={timeZone}
        onClose={() => setWinOpen(false)}
        onSaved={async () => {
          setWinOpen(false)
          await loadWins()
        }}
        scores={scores}
      />
    </section>
  )
}

type WinDrawerProps = {
  open: boolean
  timeZone: string
  scores: ReturnType<typeof useMoodPreferences>['scores']
  onClose: () => void
  onSaved: () => Promise<void>
}

function WinDrawer({ open, timeZone, scores, onClose, onSaved }: WinDrawerProps) {
  const { locale, t } = useLocale()
  const options = getMoodScoreOptions(locale, scores)
  const [text, setText] = useState('')
  const [score, setScore] = useState<number | null>(null)
  const [starred, setStarred] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setText('')
      setScore(null)
      setStarred(true)
      setError(null)
    }
  }, [open])

  const canSave = text.trim().length > 0 && score !== null && !isSaving

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!canSave || score === null) return
    setIsSaving(true)
    setError(null)
    try {
      const created = await createMoodEntry({
        score,
        recorded_at: instantToIsoInTimezone(new Date(), timeZone),
        note: text.trim(),
        tag_ids: [],
        goal_ids: [],
      })
      if (starred) {
        await patchMoodEntry(created.id, { is_favorite: true })
      }
      await onSaved()
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedSave'))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <EditorDrawer
      open={open}
      title={t('myPage.winTitle')}
      onClose={() => {
        if (!isSaving) onClose()
      }}
      footer={
        <div className="button-row">
          <button type="submit" form="my-win-form" className="button my-primary" disabled={!canSave}>
            <StableButtonLabel
              active={isSaving ? t('common.saving') : t('common.save')}
              labels={[t('common.save'), t('common.saving')]}
            />
          </button>
        </div>
      }
    >
      <form id="my-win-form" className="form my-win-form" onSubmit={(event) => void handleSubmit(event)}>
        <PageErrorAlert error={error} />
        <textarea
          className="form-input my-win-input"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={t('myPage.winPlaceholder')}
          aria-label={t('myPage.winTitle')}
          rows={3}
          maxLength={2000}
          autoFocus
        />
        <div className="form-field">
          <span className="form-label">{t('myPage.moodLabel')}</span>
          <div className="my-moods" role="radiogroup" aria-label={t('myPage.moodLabel')}>
            {options.map((option) => (
              <button
                key={option.score}
                type="button"
                role="radio"
                aria-checked={score === option.score}
                aria-label={option.label}
                title={option.label}
                className={`my-mood${score === option.score ? ' is-selected' : ''}`}
                style={{ ['--mood-color' as string]: option.color }}
                onClick={() => setScore(option.score)}
              >
                <MoodScoreIcon style={option.style} fallbackScore={option.score} />
              </button>
            ))}
          </div>
        </div>
        <label className="my-star-toggle">
          <span>
            <strong>{t('myPage.starLabel')}</strong>
            <span className="my-level-hint">{t('myPage.starHint')}</span>
          </span>
          <input
            type="checkbox"
            checked={starred}
            onChange={(event) => setStarred(event.target.checked)}
          />
        </label>
      </form>
    </EditorDrawer>
  )
}
