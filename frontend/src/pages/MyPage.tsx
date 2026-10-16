import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { getBodySettings } from '../api/body'
import { deleteGoalCheckin, listGoals, setGoalCheckin } from '../api/goals'
import { createMoodEntry, listMoodEntries } from '../api/moodEntries'
import { BodyCard, BodySettingsDrawer } from '../components/BodyCard'
import { EditorDrawer } from '../components/EditorDrawer'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { GoalIcon } from '../components/GoalIcon'
import { MoodScoreIcon } from '../components/MoodScoreIcon'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { QuickTagPicker } from '../components/QuickTagPicker'
import { StableButtonLabel } from '../components/StableButtonLabel'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { intlLocale, tp } from '../i18n/t'
import { pickCompanionVariant } from '../lib/companion'
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
import { isGuestDiaryMode } from '../lib/guestMode'
import { markdownToPlainText } from '../lib/markdownPlainText'
import { getMoodScoreOptions } from '../lib/moodScale'
import type { BodySettings } from '../types/body'
import type { GoalCheckinLevel, GoalDayMark, GoalPublic } from '../types/goal'
import type { MoodEntryPublic } from '../types/mood'

const WINS_SHOWN = 3

function isActiveOn(goal: GoalPublic, day: string): boolean {
  return goal.starts_on <= day && (goal.ends_on == null || goal.ends_on >= day)
}

function markOn(goal: GoalPublic, day: string): GoalDayMark | null {
  return goal.week_marks.find((mark) => mark.date === day) ?? null
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

/** How much of a quantity day is done, 0–100, for the dot fill. */
function fillPercent(goal: GoalPublic, mark: GoalDayMark | null): number {
  if (!mark) return 0
  if (goal.tracking_kind !== 'quantity' || !goal.target_amount || mark.amount == null) {
    return mark.level === 'full' ? 100 : 50
  }
  return Math.min(100, Math.round((mark.amount / goal.target_amount) * 100))
}

/** How far a quantity day went past its target, 0–100 (200% of the target and more is 100). */
function overPercent(goal: GoalPublic, mark: GoalDayMark | null): number {
  if (!mark || goal.tracking_kind !== 'quantity' || !goal.target_amount || mark.amount == null) return 0
  const over = mark.amount - goal.target_amount
  return over > 0 ? Math.min(100, Math.round((over / goal.target_amount) * 100)) : 0
}

/** The week's plan for a goal: its days per week, but never more than the days it is active. */
function weekPlan(goal: GoalPublic, weekDays: string[]): number {
  const activeDays = weekDays.filter((day) => isActiveOn(goal, day)).length
  return Math.min(goal.times_per_week, activeDays)
}

type MarkTarget = { goal: GoalPublic; day: string }

/**
 * A calm home for goals and small wins (GP-44, GP-46): the week's goals with marks per
 * day, a gentle weekly plan, and the entries written as "what worked out".
 */
export function MyPage() {
  const { user } = useAuth()
  const { locale, t } = useLocale()
  const { scores } = useMoodPreferences()
  const timeZone = user?.timezone ?? 'UTC'
  const dateLocale = intlLocale(locale)
  const today = todayKey(timeZone)
  const displayName = user?.display_name ?? null
  const [weekRef, setWeekRef] = useState(today)
  const week = getIsoWeekBounds(weekRef, timeZone)
  const isCurrentWeek = week.period_start <= today && today < week.period_end
  const weekDays = useMemo(
    () => Array.from({ length: 7 }, (_, index) => shiftDateKey(week.period_start, index)),
    [week.period_start],
  )

  const [goals, setGoals] = useState<GoalPublic[]>([])
  const [wins, setWins] = useState<MoodEntryPublic[]>([])
  // A win shows up at once while it saves; a failed save reopens the drawer with the text.
  const [pendingWin, setPendingWin] = useState<WinDraft | null>(null)
  const [winRestore, setWinRestore] = useState<{ draft: WinDraft; error: string } | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [markTarget, setMarkTarget] = useState<MarkTarget | null>(null)
  const [markLevel, setMarkLevel] = useState<GoalCheckinLevel>('partial')
  const [markAmount, setMarkAmount] = useState('')
  // A quantity day that already has some progress takes another step by default (GP-50).
  const [markMode, setMarkMode] = useState<'add' | 'set'>('set')
  const [markError, setMarkError] = useState<string | null>(null)
  const [isMarking, setIsMarking] = useState(false)
  const [winOpen, setWinOpen] = useState(false)
  const [body, setBody] = useState<BodySettings | null>(null)
  const [bodySettingsOpen, setBodySettingsOpen] = useState(false)
  const isGuest = isGuestDiaryMode()

  useEffect(() => {
    if (isGuest) return
    void getBodySettings()
      .then(setBody)
      .catch(() => setBody(null))
  }, [isGuest])

  // The current week shows the latest wins; a past week shows only its own.
  const winsFrom = isCurrentWeek ? undefined : week.recorded_from
  const winsTo = isCurrentWeek ? undefined : week.recorded_to
  const loadWins = useCallback(async () => {
    const response = await listMoodEntries({
      is_win: true,
      limit: WINS_SHOWN,
      recorded_from: winsFrom,
      recorded_to: winsTo,
    })
    setWins(response.items)
  }, [winsFrom, winsTo])

  useEffect(() => {
    void loadWins().catch(() => setWins([]))
  }, [loadWins])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setIsLoading(true)
      try {
        const goalList = await listGoals({ progressOn: weekRef })
        if (cancelled) return
        setGoals(goalList.items)
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
  }, [weekRef, locale, t])

  const weekGoals = goals.filter((goal) => weekDays.some((day) => isActiveOn(goal, day)))
  usePageAmbientGlow(weekGoals.map((goal) => goal.color))

  const plan = weekGoals.reduce(
    (total, goal) => {
      const goalPlan = weekPlan(goal, weekDays)
      return {
        planned: total.planned + goalPlan,
        done: total.done + Math.min(goal.completed_this_week, goalPlan),
      }
    },
    { planned: 0, done: 0 },
  )
  const daysLeft = isCurrentWeek ? weekDays.filter((day) => day >= today).length : 0
  const planLine = (() => {
    if (plan.planned === 0) return null
    if (plan.done >= plan.planned) return t('myPage.planDone')
    if (!isCurrentWeek) {
      return t('myPage.planPast', { done: plan.done, planned: plan.planned })
    }
    return t('myPage.planLeft', {
      days: tp(locale, daysLeft, {
        one: 'myPage.daysOne',
        few: 'myPage.daysFew',
        many: 'myPage.daysMany',
      }),
      marks: tp(locale, plan.planned - plan.done, {
        one: 'myPage.marksOne',
        few: 'myPage.marksFew',
        many: 'myPage.marksMany',
      }),
    })
  })()

  const replaceGoal = (updated: GoalPublic) => {
    setGoals((current) => current.map((goal) => (goal.id === updated.id ? updated : goal)))
  }

  const canMark = (goal: GoalPublic, day: string) => day <= today && isActiveOn(goal, day)

  const openMark = (goal: GoalPublic, day: string) => {
    const mark = markOn(goal, day)
    setMarkTarget({ goal, day })
    setMarkLevel(mark?.level === 'full' ? 'full' : 'partial')
    const hasAmount = goal.tracking_kind === 'quantity' && (mark?.amount ?? 0) > 0
    setMarkMode(hasAmount ? 'add' : 'set')
    setMarkAmount('')
    setMarkError(null)
  }

  const markGoal = markTarget?.goal ?? null
  const isQuantity = markGoal?.tracking_kind === 'quantity'
  const amountValue = Number.parseInt(markAmount, 10)
  const amountValid = Number.isInteger(amountValue) && amountValue >= 1
  const markDone = markTarget ? (markOn(markTarget.goal, markTarget.day)?.amount ?? 0) : 0
  const isAdding = isQuantity && markMode === 'add'

  const saveMark = async (clear: boolean) => {
    if (!markTarget) return
    const { goal, day } = markTarget
    setIsMarking(true)
    setMarkError(null)
    try {
      const updated = clear
        ? await deleteGoalCheckin(goal.id, day)
        : await setGoalCheckin(
            goal.id,
            day,
            goal.tracking_kind === 'quantity'
              ? { amount: amountValue, add: markMode === 'add' }
              : { level: markLevel },
          )
      // A mark on another week answers with that week; keep the one on screen.
      if (week.period_start <= day && day < week.period_end) replaceGoal(updated)
      setMarkTarget(null)
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

  const goalHint = (goal: GoalPublic) => {
    const goalPlan = weekPlan(goal, weekDays)
    const parts = [t('myPage.goalPlan', { done: goal.completed_this_week, planned: goalPlan })]
    if (goal.tracking_kind === 'quantity' && goal.target_amount) {
      parts.push(
        goal.min_amount
          ? t('myPage.countsFrom', { min: goal.min_amount, target: goal.target_amount, unit: goal.unit ?? '' })
          : t('myPage.dailyTarget', { target: goal.target_amount, unit: goal.unit ?? '' }),
      )
    } else if (goal.partial_label) {
      parts.push(t('myPage.partialHint', { label: goal.partial_label }))
    }
    return parts.join(' · ')
  }

  return (
    <section className="page page-my">
      <EmailVerificationBanner />

      <header className="page-header my-header">
        <div>
          <h1>{t('myPage.title')}</h1>
          <div className="my-week-nav">
            <button
              type="button"
              className="my-week-arrow"
              aria-label={t('myPage.prevWeek')}
              onClick={() => setWeekRef(shiftDateKey(week.period_start, -7))}
            >
              ‹
            </button>
            <span className="my-week muted">
              {formatWeekHeading(week.period_start, week.period_end, dateLocale)}
            </span>
            <button
              type="button"
              className="my-week-arrow"
              aria-label={t('myPage.nextWeek')}
              disabled={isCurrentWeek}
              onClick={() => setWeekRef(shiftDateKey(week.period_start, 7))}
            >
              ›
            </button>
            {!isCurrentWeek ? (
              <button type="button" className="link-button" onClick={() => setWeekRef(today)}>
                {t('myPage.thisWeek')}
              </button>
            ) : null}
          </div>
        </div>
      </header>

      {isCurrentWeek ? (
        <p className="my-hello">
          {displayName && pickCompanionVariant(`${today}:myHello`, 2) === 1
            ? t('myPage.helloNamed', { name: displayName })
            : t('myPage.hello')}
        </p>
      ) : null}
      <PageErrorAlert error={error} />

      <section className="card my-card" aria-labelledby="my-goals-title">
        <div className="my-card-head">
          <h2 id="my-goals-title">
            {isCurrentWeek ? t('myPage.goalsTitle') : t('myPage.goalsTitlePast')}
          </h2>
          <Link to="/goals" className="my-card-link">
            {t('myPage.allGoals')}
          </Link>
        </div>
        {!isLoading && planLine ? <p className="my-plan">{planLine}</p> : null}
        {isLoading ? (
          <p className="muted">{t('common.loading')}</p>
        ) : weekGoals.length === 0 ? (
          <p className="my-empty">
            {t('myPage.goalsEmpty')}{' '}
            <Link to="/goals">{t('myPage.addGoal')}</Link>
          </p>
        ) : (
          <ul className="my-goal-list">
            {weekGoals.map((goal) => {
              const todayMark = isCurrentWeek ? markOn(goal, today) : null
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
                    <span className="my-goal-hint">{goalHint(goal)}</span>
                    <span className="my-goal-days" style={{ ['--goal-color' as string]: goal.color }}>
                      {weekDays.map((day) => {
                        const label = weekdayShort(day, dateLocale)
                        // Days outside the goal's dates are not "missed"; they stay quietly grey.
                        if (!isActiveOn(goal, day)) {
                          return (
                            <span key={day} className="my-day is-before" aria-hidden>
                              {label}
                            </span>
                          )
                        }
                        const mark = markOn(goal, day)
                        const className = [
                          'my-day',
                          mark ? `is-${mark.level}` : '',
                          goal.tracking_kind === 'quantity' && mark ? 'is-amount' : '',
                          overPercent(goal, mark) > 0 ? 'is-over' : '',
                          day === today ? 'is-today' : '',
                        ]
                          .filter(Boolean)
                          .join(' ')
                        const style = {
                          ['--fill' as string]: `${fillPercent(goal, mark)}%`,
                          ['--over' as string]: `${overPercent(goal, mark)}%`,
                        }
                        if (!canMark(goal, day)) {
                          return (
                            <span key={day} className={className} style={style}>
                              {label}
                            </span>
                          )
                        }
                        return (
                          <button
                            key={day}
                            type="button"
                            className={className}
                            style={style}
                            title={formatCalendarDate(day, dateLocale)}
                            aria-label={t('myPage.markDayAria', {
                              label: goal.label,
                              date: formatDay(day, dateLocale, { weekday: 'long', day: 'numeric', month: 'long' }),
                            })}
                            onClick={() => openMark(goal, day)}
                          >
                            {label}
                          </button>
                        )
                      })}
                    </span>
                  </div>
                  {isCurrentWeek && canMark(goal, today) ? (
                    <button
                      type="button"
                      className={`my-goal-mark${todayMark ? ` is-${todayMark.level}` : ''}`}
                      style={{ ['--goal-color' as string]: goal.color }}
                      aria-label={t('myPage.markAria', { label: goal.label })}
                      onClick={() => openMark(goal, today)}
                    >
                      ✓
                    </button>
                  ) : null}
                </li>
              )
            })}
          </ul>
        )}
      </section>

      {body && (body.show_weight || body.show_food || body.show_sleep) ? (
        <BodyCard
          settings={body}
          today={today}
          timeZone={timeZone}
          weekDays={weekDays}
          isCurrentWeek={isCurrentWeek}
          goals={goals}
          onSettingsChange={setBody}
          onGoalChange={replaceGoal}
          onOpenSettings={() => setBodySettingsOpen(true)}
        />
      ) : null}

      <section className="card my-card" aria-labelledby="my-wins-title">
        <div className="my-card-head">
          <h2 id="my-wins-title">{t('myPage.winsTitle')}</h2>
          {wins.length > 0 ? (
            <Link to="/?wins=1" className="my-card-link">
              {t('myPage.allWins')}
            </Link>
          ) : null}
        </div>
        {wins.length === 0 && !pendingWin ? (
          <p className="my-empty">
            {isCurrentWeek ? t('myPage.winsEmpty') : t('myPage.winsEmptyPast')}
          </p>
        ) : (
          <ul className="my-win-list">
            {pendingWin ? (
              <li>
                <span className="my-win is-pending" aria-busy="true">
                  <span className="my-win-star" aria-hidden>
                    ★
                  </span>
                  <span className="my-win-body">
                    <span className="my-win-text">{pendingWin.note}</span>
                    <span className="my-win-date">
                      <span
                        className="my-win-mood"
                        style={{ backgroundColor: pendingWin.color }}
                        aria-hidden
                      />
                      {t('common.saving')}
                    </span>
                  </span>
                </span>
              </li>
            ) : null}
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

      {body && !body.show_weight && !body.show_food && !body.show_sleep ? (
        <button type="button" className="link-button body-offer" onClick={() => setBodySettingsOpen(true)}>
          {t('body.offer')}
        </button>
      ) : null}

      <button type="button" className="my-write" onClick={() => setWinOpen(true)}>
        {t('myPage.write')}
      </button>

      <EditorDrawer
        open={markTarget !== null}
        title={markGoal?.label ?? ''}
        description={
          markTarget
            ? formatDay(markTarget.day, dateLocale, { weekday: 'long', day: 'numeric', month: 'long' })
            : undefined
        }
        accentColors={markGoal ? [markGoal.color] : []}
        onClose={() => {
          if (!isMarking) setMarkTarget(null)
        }}
        footer={
          <div className="button-row">
            <button
              type="button"
              className="button my-primary"
              disabled={isMarking || (isQuantity && !amountValid)}
              onClick={() => void saveMark(false)}
            >
              <StableButtonLabel
                active={isMarking ? t('common.saving') : isAdding ? t('myPage.addStep') : t('myPage.mark')}
                labels={[t('myPage.mark'), t('myPage.addStep'), t('common.saving')]}
              />
            </button>
            {markTarget && markOn(markTarget.goal, markTarget.day) ? (
              <button
                type="button"
                className="button button-secondary"
                disabled={isMarking}
                onClick={() => void saveMark(true)}
              >
                {t('myPage.unmark')}
              </button>
            ) : null}
          </div>
        }
      >
        <PageErrorAlert error={markError} />
        {markGoal && isQuantity ? (
          <div className="my-amount">
            {isAdding ? (
              <p className="my-amount-done">
                {t('myPage.amountDone', {
                  done: markDone,
                  target: markGoal.target_amount ?? 0,
                  unit: markGoal.unit ?? '',
                })}
              </p>
            ) : null}
            <label className="form-label" htmlFor="my-amount-input">
              {isAdding ? t('myPage.amountAddLabel') : t('myPage.amountLabel')}
            </label>
            <div className="my-amount-row">
              <input
                id="my-amount-input"
                className="form-input"
                type="number"
                inputMode="numeric"
                min={1}
                step={1}
                value={markAmount}
                onChange={(event) => setMarkAmount(event.target.value.replace(/[^0-9]/g, ''))}
              />
              <span className="muted">
                {isAdding
                  ? markGoal.unit ?? ''
                  : t('myPage.amountOf', { target: markGoal.target_amount ?? 0, unit: markGoal.unit ?? '' })}
              </span>
            </div>
            {isAdding && amountValid ? (
              <span className="my-level-hint">
                {t('myPage.amountWillBe', {
                  total: markDone + amountValue,
                  target: markGoal.target_amount ?? 0,
                  unit: markGoal.unit ?? '',
                })}
              </span>
            ) : null}
            <span className="my-level-hint">
              {markGoal.min_amount
                ? t('myPage.amountCountsFrom', { min: markGoal.min_amount, unit: markGoal.unit ?? '' })
                : t('myPage.amountCountsFull')}
            </span>
            {markDone > 0 ? (
              <button
                type="button"
                className="link-button my-amount-mode"
                onClick={() => {
                  const next = markMode === 'add' ? 'set' : 'add'
                  setMarkMode(next)
                  setMarkAmount(next === 'set' ? String(markDone) : '')
                }}
              >
                {markMode === 'add' ? t('myPage.amountFixTotal') : t('myPage.amountAddInstead')}
              </button>
            ) : null}
          </div>
        ) : (
          <div
            className="my-levels"
            role="radiogroup"
            aria-label={t('myPage.markAria', { label: markGoal?.label ?? '' })}
          >
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
        )}
        <p className="my-gentle muted">{t('myPage.noPenalty')}</p>
      </EditorDrawer>

      {body ? (
        <BodySettingsDrawer
          open={bodySettingsOpen}
          settings={body}
          goals={goals}
          onClose={() => setBodySettingsOpen(false)}
          onSettingsChange={setBody}
        />
      ) : null}

      <WinDrawer
        open={winOpen}
        restore={winRestore}
        onClose={() => {
          setWinOpen(false)
          setWinRestore(null)
        }}
        onSave={(draft) => {
          // Close right away: on a sleepy server the save can take a few seconds.
          setWinOpen(false)
          setWinRestore(null)
          setPendingWin(draft)
          createMoodEntry({
            score: draft.score,
            recorded_at: instantToIsoInTimezone(new Date(), timeZone),
            note: draft.note,
            tag_ids: draft.tagIds,
            goal_ids: [],
            is_win: true,
          })
            .then((entry) => {
              if (isCurrentWeek) setWins((current) => [entry, ...current].slice(0, WINS_SHOWN))
            })
            .catch((err: unknown) => {
              setWinRestore({ draft, error: formatApiError(err, t, 'errors.failedSave') })
              setWinOpen(true)
            })
            .finally(() => setPendingWin(null))
        }}
        scores={scores}
      />
    </section>
  )
}

type WinDraft = { note: string; score: number; color: string; tagIds: string[] }

type WinDrawerProps = {
  open: boolean
  scores: ReturnType<typeof useMoodPreferences>['scores']
  restore: { draft: WinDraft; error: string } | null
  onClose: () => void
  onSave: (draft: WinDraft) => void
}

function WinDrawer({ open, scores, restore, onClose, onSave }: WinDrawerProps) {
  const { locale, t } = useLocale()
  const options = getMoodScoreOptions(locale, scores)
  const [text, setText] = useState('')
  const [score, setScore] = useState<number | null>(null)
  const [tagIds, setTagIds] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setText(restore?.draft.note ?? '')
      setScore(restore?.draft.score ?? null)
      setTagIds(restore?.draft.tagIds ?? [])
      setError(restore?.error ?? null)
    }
  }, [open, restore])

  const canSave = text.trim().length > 0 && score !== null

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!canSave || score === null) return
    const color = options.find((option) => option.score === score)?.color ?? ''
    onSave({ note: text.trim(), score, color, tagIds })
  }

  return (
    <EditorDrawer
      open={open}
      title={t('myPage.winTitle')}
      onClose={onClose}
      footer={
        <div className="button-row">
          <button type="submit" form="my-win-form" className="button my-primary" disabled={!canSave}>
            {t('common.save')}
          </button>
        </div>
      }
    >
      <form id="my-win-form" className="form my-win-form" onSubmit={handleSubmit}>
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
        {open ? (
          <QuickTagPicker
            selectedIds={tagIds}
            onToggle={(tagId) =>
              setTagIds((current) =>
                current.includes(tagId)
                  ? current.filter((id) => id !== tagId)
                  : [...current, tagId],
              )
            }
          />
        ) : null}
        <p className="my-level-hint">{t('myPage.winHint')}</p>
      </form>
    </EditorDrawer>
  )
}
