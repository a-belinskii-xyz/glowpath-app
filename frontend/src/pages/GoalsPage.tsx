import { type DragEvent, type FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  createGoal,
  deleteGoal,
  listGoals,
  patchGoal,
  reorderGoals,
} from '../api/goals'
import { Alert } from '../components/Alert'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { FormField } from '../components/FormField'
import { GoalIcon } from '../components/GoalIcon'
import { GoalIconEditor } from '../components/GoalIconEditor'
import { PopupMenu } from '../components/PopupMenu'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { moodGlowFilter } from '../design'
import { ApiError } from '../lib/errors'
import { todayKey } from '../lib/datetime'
import { isValidHexColor } from '../lib/moodScale'
import { DEFAULT_GOAL_STYLE, type GoalPublic } from '../types/goal'

type EditorMode = { kind: 'create' } | { kind: 'edit'; goal: GoalPublic }

function moveItem<T>(items: T[], fromIndex: number, toIndex: number): T[] {
  const next = [...items]
  const [item] = next.splice(fromIndex, 1)
  next.splice(toIndex, 0, item)
  return next
}

export function GoalsPage() {
  const { user } = useAuth()
  const { locale, t } = useLocale()
  const timeZone = user?.timezone ?? 'UTC'

  const [goals, setGoals] = useState<GoalPublic[]>([])
  const [visibleLimit, setVisibleLimit] = useState(3)
  const [statsLimit, setStatsLimit] = useState(5)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [editor, setEditor] = useState<EditorMode | null>(null)
  const [name, setName] = useState('')
  const [timesPerWeek, setTimesPerWeek] = useState(7)
  const [startsOn, setStartsOn] = useState(todayKey(timeZone))
  const [endsOn, setEndsOn] = useState('')
  const [draftColor, setDraftColor] = useState(DEFAULT_GOAL_STYLE.color)
  const [draftEmoji, setDraftEmoji] = useState(DEFAULT_GOAL_STYLE.icon)
  const [isSaving, setIsSaving] = useState(false)
  const [togglingGoalId, setTogglingGoalId] = useState<string | null>(null)
  const [draggingId, setDraggingId] = useState<string | null>(null)

  const reload = async () => {
    const response = await listGoals()
    setGoals(response.items)
    setVisibleLimit(response.entry_visible_goal_limit)
    setStatsLimit(response.stats_visible_goal_limit)
  }

  const visibleCount = goals.filter((goal) => goal.show_on_entry).length
  const atVisibleLimit = visibleCount >= visibleLimit
  const statsCount = goals.filter((goal) => goal.show_in_stats).length
  const atStatsLimit = statsCount >= statsLimit

  useEffect(() => {
    const load = async () => {
      setIsLoading(true)
      try {
        await reload()
        setError(null)
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError(t('errors.verifyToViewGoals'))
        } else {
          setError(err instanceof Error ? err.message : t('errors.failedLoadGoals'))
        }
      } finally {
        setIsLoading(false)
      }
    }
    void load()
  }, [locale, t])

  const openEditor = (mode: EditorMode) => {
    setError(null)
    setEditor(mode)
    if (mode.kind === 'create') {
      setName('')
      setTimesPerWeek(7)
      setStartsOn(todayKey(timeZone))
      setEndsOn('')
      setDraftColor(DEFAULT_GOAL_STYLE.color)
      setDraftEmoji(DEFAULT_GOAL_STYLE.icon)
    } else {
      setName(mode.goal.label)
      setTimesPerWeek(mode.goal.times_per_week)
      setStartsOn(mode.goal.starts_on)
      setEndsOn(mode.goal.ends_on ?? '')
      setDraftColor(mode.goal.color)
      setDraftEmoji(mode.goal.icon_type === 'emoji' ? mode.goal.icon : DEFAULT_GOAL_STYLE.icon)
    }
  }

  const closeEditor = () => {
    setEditor(null)
    setName('')
    setDraftColor(DEFAULT_GOAL_STYLE.color)
    setDraftEmoji(DEFAULT_GOAL_STYLE.icon)
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!editor) return

    const trimmed = name.trim()
    if (!trimmed) {
      setError(t('goalsPage.nameRequired'))
      return
    }
    if (timesPerWeek < 1 || timesPerWeek > 7) {
      setError(t('goalsPage.timesPerWeekRequired'))
      return
    }
    if (!startsOn) {
      setError(t('goalsPage.startsOnRequired'))
      return
    }
    if (endsOn && endsOn < startsOn) {
      setError(t('goalsPage.endsOnBeforeStarts'))
      return
    }
    if (editor.kind === 'create' && !isValidHexColor(draftColor)) {
      setError(t('goalsPage.invalidColor'))
      return
    }
    const emoji = draftEmoji.trim()
    if (editor.kind === 'create' && !emoji) {
      setError(t('goalsPage.emojiRequired'))
      return
    }

    const existingLabels = editor.kind === 'edit' ? editor.goal.labels : {}
    const labels = { ...existingLabels, [locale]: trimmed }

    setIsSaving(true)
    setError(null)
    try {
      if (editor.kind === 'create') {
        await createGoal({
          labels,
          times_per_week: timesPerWeek,
          starts_on: startsOn,
          ends_on: endsOn || null,
          show_on_entry: !atVisibleLimit,
          show_in_stats: !atStatsLimit,
          color: draftColor,
          icon_type: 'emoji',
          icon: emoji,
        })
      } else {
        await patchGoal(editor.goal.id, {
          labels,
          times_per_week: timesPerWeek,
          starts_on: startsOn,
          ends_on: endsOn || null,
        })
      }
      await reload()
      closeEditor()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.failedSave'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (goal: GoalPublic) => {
    if (!window.confirm(t('confirm.deleteGoal', { label: goal.label }))) return
    setError(null)
    try {
      await deleteGoal(goal.id)
      await reload()
      if (editor?.kind === 'edit' && editor.goal.id === goal.id) {
        closeEditor()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.failedDeleteGoal'))
    }
  }

  const handleToggleShowOnEntry = async (goal: GoalPublic) => {
    const next = !goal.show_on_entry
    if (next && atVisibleLimit) {
      setError(t('goalsPage.visibilityLimit', { limit: visibleLimit }))
      return
    }
    setTogglingGoalId(goal.id)
    setError(null)
    try {
      const updated = await patchGoal(goal.id, { show_on_entry: next })
      setGoals((current) => current.map((item) => (item.id === updated.id ? updated : item)))
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.failedUpdateVisibility'))
    } finally {
      setTogglingGoalId(null)
    }
  }

  const handleToggleShowInStats = async (goal: GoalPublic) => {
    const next = !goal.show_in_stats
    if (next && atStatsLimit) {
      setError(t('goalsPage.statsVisibilityLimit', { limit: statsLimit }))
      return
    }
    setTogglingGoalId(goal.id)
    setError(null)
    try {
      const updated = await patchGoal(goal.id, { show_in_stats: next })
      setGoals((current) => current.map((item) => (item.id === updated.id ? updated : item)))
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.failedUpdateVisibility'))
    } finally {
      setTogglingGoalId(null)
    }
  }

  const handleDrop = async (targetId: string) => {
    if (!draggingId || draggingId === targetId) {
      setDraggingId(null)
      return
    }
    const fromIndex = goals.findIndex((item) => item.id === draggingId)
    const toIndex = goals.findIndex((item) => item.id === targetId)
    setDraggingId(null)
    if (fromIndex < 0 || toIndex < 0) return

    const previous = goals
    const next = moveItem(goals, fromIndex, toIndex)
    setGoals(next)
    try {
      const response = await reorderGoals({
        ordered_ids: next.map((item) => item.id),
      })
      setGoals(response.items)
    } catch (err) {
      setGoals(previous)
      setError(err instanceof Error ? err.message : t('errors.failedReorderGoals'))
    }
  }

  const editorTitle =
    editor?.kind === 'create'
      ? t('goalsPage.addGoal')
      : editor?.kind === 'edit'
        ? t('goalsPage.editGoal', { label: editor.goal.label })
        : null

  return (
    <section className="page">
      <EmailVerificationBanner />

      <header className="page-header">
        <h1>{t('goalsPage.title')}</h1>
        <button type="button" className="button" onClick={() => openEditor({ kind: 'create' })}>
          {t('goalsPage.addGoal')}
        </button>
      </header>

      <p className="muted tag-visibility-hint">
        {t('goalsPage.hint', { limit: visibleLimit, count: visibleCount })}
      </p>
      <p className="muted tag-visibility-hint">
        {t('goalsPage.statsHint', { limit: statsLimit, count: statsCount })}
      </p>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {isLoading ? <p className="muted">{t('common.loadingGoals')}</p> : null}

      {editor && editorTitle ? (
        <form className="card form tag-editor" onSubmit={(event) => void handleSubmit(event)}>
          <h2>{editorTitle}</h2>
          <FormField
            id="goal-name"
            label={t('common.name')}
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            autoFocus
            maxLength={64}
          />
          <label className="form-field">
            <span className="form-label">{t('goalsPage.timesPerWeek')}</span>
            <input
              className="form-input"
              type="number"
              min={1}
              max={7}
              value={timesPerWeek}
              onChange={(event) => setTimesPerWeek(Number(event.target.value))}
              required
            />
          </label>
          <label className="form-field">
            <span className="form-label">{t('goalsPage.startsOn')}</span>
            <input
              className="form-input"
              type="date"
              value={startsOn}
              onChange={(event) => setStartsOn(event.target.value)}
              required
            />
          </label>
          <label className="form-field">
            <span className="form-label">{t('goalsPage.endsOn')}</span>
            <input
              className="form-input"
              type="date"
              value={endsOn}
              min={startsOn || undefined}
              onChange={(event) => setEndsOn(event.target.value)}
            />
            <span className="form-hint">{t('goalsPage.endsOnHint')}</span>
          </label>
          {editor.kind === 'create' ? (
            <div className="goal-icon-create-fields">
              <div className="mood-preferences-preview">
                <span
                  className="mood-preferences-swatch"
                  style={{ backgroundColor: isValidHexColor(draftColor) ? draftColor : DEFAULT_GOAL_STYLE.color }}
                  aria-hidden
                />
                <span
                  style={{
                    filter: moodGlowFilter(
                      isValidHexColor(draftColor) ? draftColor : DEFAULT_GOAL_STYLE.color,
                    ),
                  }}
                >
                  <GoalIcon
                    style={{ color: draftColor, icon_type: 'emoji', icon: draftEmoji || '🎯' }}
                    className="mood-preferences-emoji"
                  />
                </span>
              </div>
              <div className="mood-preferences-controls">
                <input
                  className="mood-preferences-color-input"
                  type="color"
                  value={isValidHexColor(draftColor) ? draftColor : DEFAULT_GOAL_STYLE.color}
                  onChange={(event) => setDraftColor(event.target.value)}
                  aria-label={t('goalsPage.color')}
                />
                <input
                  className="form-input mood-preferences-hex-input"
                  type="text"
                  value={draftColor}
                  onChange={(event) => setDraftColor(event.target.value)}
                  pattern="^#[0-9A-Fa-f]{6}$"
                  spellCheck={false}
                  aria-label={t('goalsPage.hex')}
                />
              </div>
              <label className="form-field">
                <span className="form-label">{t('moodPreferences.iconTypeEmoji')}</span>
                <input
                  className="form-input mood-preferences-emoji-input"
                  type="text"
                  value={draftEmoji}
                  maxLength={8}
                  onChange={(event) => setDraftEmoji(event.target.value)}
                />
              </label>
              <p className="form-hint">{t('goalsPage.uploadAfterCreate')}</p>
            </div>
          ) : (
            <GoalIconEditor
              goal={editor.goal}
              onGoalChange={(updated) => {
                setEditor({ kind: 'edit', goal: updated })
                setGoals((current) =>
                  current.map((item) => (item.id === updated.id ? updated : item)),
                )
              }}
            />
          )}
          <div className="button-row">
            <button type="submit" className="button" disabled={isSaving}>
              {isSaving ? t('common.saving') : t('common.save')}
            </button>
            <button
              type="button"
              className="button button-secondary"
              onClick={closeEditor}
              disabled={isSaving}
            >
              {t('common.cancel')}
            </button>
          </div>
        </form>
      ) : null}

      <div className="goals-list">
        {goals.map((goal) => (
          <article
            key={goal.id}
            className={`card goal-card${draggingId === goal.id ? ' is-dragging' : ''}`}
            draggable
            onDragStart={() => setDraggingId(goal.id)}
            onDragOver={(event: DragEvent) => event.preventDefault()}
            onDrop={() => void handleDrop(goal.id)}
            onDragEnd={() => setDraggingId(null)}
          >
            <header className="goal-card-header">
              <PopupMenu
                label={
                  <h2 className="goal-card-title">
                    <GoalIcon
                      style={{
                        color: goal.color,
                        icon_type: goal.icon_type,
                        icon: goal.icon,
                      }}
                      className="goal-card-icon"
                    />
                    {goal.label}
                  </h2>
                }
                ariaLabel={t('goalsPage.actionsFor', { label: goal.label })}
                onEdit={() => openEditor({ kind: 'edit', goal })}
                onDelete={() => void handleDelete(goal)}
              />
              <span className="tag-drag-hint muted" aria-hidden="true">
                ⋮⋮
              </span>
            </header>
            <p className="goal-week-progress">
              {t('goalsPage.weekProgress', {
                done: goal.completed_this_week,
                target: goal.times_per_week,
              })}
            </p>
            <p className="muted goal-meta">
              {goal.ends_on
                ? t('goalsPage.dateRangeLabel', { start: goal.starts_on, end: goal.ends_on })
                : t('goalsPage.startsOnLabel', { date: goal.starts_on })}
            </p>
            <label className="tag-visibility-toggle">
              <input
                type="checkbox"
                checked={goal.show_on_entry}
                disabled={togglingGoalId === goal.id || (!goal.show_on_entry && atVisibleLimit)}
                onChange={() => void handleToggleShowOnEntry(goal)}
              />
              <span>{t('goalsPage.showOnEntry')}</span>
            </label>
            <label className="tag-visibility-toggle">
              <input
                type="checkbox"
                checked={goal.show_in_stats}
                disabled={togglingGoalId === goal.id || (!goal.show_in_stats && atStatsLimit)}
                onChange={() => void handleToggleShowInStats(goal)}
              />
              <span>{t('goalsPage.showInStats')}</span>
            </label>
          </article>
        ))}
      </div>

      <p className="muted">
        <Link to="/">{t('common.backToEntries')}</Link>
      </p>
    </section>
  )
}
