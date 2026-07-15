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
import { PopupMenu } from '../components/PopupMenu'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { ApiError } from '../lib/errors'
import { todayKey } from '../lib/datetime'
import type { GoalPublic } from '../types/goal'

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
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [editor, setEditor] = useState<EditorMode | null>(null)
  const [name, setName] = useState('')
  const [timesPerWeek, setTimesPerWeek] = useState(7)
  const [startsOn, setStartsOn] = useState(todayKey(timeZone))
  const [isSaving, setIsSaving] = useState(false)
  const [togglingGoalId, setTogglingGoalId] = useState<string | null>(null)
  const [draggingId, setDraggingId] = useState<string | null>(null)

  const reload = async () => {
    const response = await listGoals()
    setGoals(response.items)
    setVisibleLimit(response.entry_visible_goal_limit)
  }

  const visibleCount = goals.filter((goal) => goal.show_on_entry).length
  const atVisibleLimit = visibleCount >= visibleLimit

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
    } else {
      setName(mode.goal.label)
      setTimesPerWeek(mode.goal.times_per_week)
      setStartsOn(mode.goal.starts_on)
    }
  }

  const closeEditor = () => {
    setEditor(null)
    setName('')
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
          show_on_entry: !atVisibleLimit,
        })
      } else {
        await patchGoal(editor.goal.id, {
          labels,
          times_per_week: timesPerWeek,
          starts_on: startsOn,
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
                label={<h2>{goal.label}</h2>}
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
              {t('goalsPage.startsOnLabel', { date: goal.starts_on })}
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
          </article>
        ))}
      </div>

      <p className="muted">
        <Link to="/">{t('common.backToEntries')}</Link>
      </p>
    </section>
  )
}
