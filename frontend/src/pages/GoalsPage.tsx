import { type DragEvent, type FormEvent, useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  createGoal,
  deleteGoal,
  listGoals,
  patchGoal,
  reorderGoals,
} from '../api/goals'
import { Alert } from '../components/Alert'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { DragHandle } from '../components/DragHandle'
import { EditorDrawer } from '../components/EditorDrawer'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { FormField } from '../components/FormField'
import { GoalIcon } from '../components/GoalIcon'
import { GoalIconEditor } from '../components/GoalIconEditor'
import { IconButton } from '../components/IconButton'
import { ArrowDownIcon, ArrowUpIcon, DeleteIcon, EditIcon } from '../components/icons'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { moodGlowFilter, moodSubtleFill } from '../design'
import { todayKey } from '../lib/datetime'
import { ApiError } from '../lib/errors'
import {
  dropEdgeFromClientY,
  dropIndexForEdge,
  moveItem,
  moveItemById,
  type DropEdge,
} from '../lib/listReorder'
import { isValidHexColor } from '../lib/moodScale'
import { DEFAULT_GOAL_STYLE, type GoalPublic } from '../types/goal'

type EditorMode = { kind: 'create' } | { kind: 'edit'; goal: GoalPublic }

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
  const [dropTarget, setDropTarget] = useState<{ id: string; edge: DropEdge } | null>(null)
  const [pendingDelete, setPendingDelete] = useState<GoalPublic | null>(null)

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

  const closeEditor = useCallback(() => {
    setEditor(null)
    setName('')
    setDraftColor(DEFAULT_GOAL_STYLE.color)
    setDraftEmoji(DEFAULT_GOAL_STYLE.icon)
  }, [])

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
    if (!isValidHexColor(draftColor)) {
      setError(t('goalsPage.invalidColor'))
      return
    }
    const emoji = draftEmoji.trim()
    const usingUpload = editor.kind === 'edit' && editor.goal.icon_type === 'upload'
    if (!usingUpload && !emoji) {
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
          color: draftColor,
          ...(usingUpload ? {} : { icon_type: 'emoji' as const, icon: emoji }),
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

  const persistOrder = async (next: GoalPublic[], previous: GoalPublic[]) => {
    setGoals(next)
    try {
      const response = await reorderGoals({ ordered_ids: next.map((item) => item.id) })
      setGoals(response.items)
    } catch (err) {
      setGoals(previous)
      setError(err instanceof Error ? err.message : t('errors.failedReorderGoals'))
    }
  }

  const clearDrag = () => {
    setDraggingId(null)
    setDropTarget(null)
  }

  const handleDrop = async (targetId: string, edge: DropEdge) => {
    if (!draggingId || draggingId === targetId) {
      clearDrag()
      return
    }
    const fromIndex = goals.findIndex((item) => item.id === draggingId)
    const targetIndex = goals.findIndex((item) => item.id === targetId)
    clearDrag()
    if (fromIndex < 0 || targetIndex < 0) return
    const toIndex = dropIndexForEdge(fromIndex, targetIndex, edge)
    if (toIndex === fromIndex) return
    await persistOrder(moveItem(goals, fromIndex, toIndex), goals)
  }

  const handleMove = async (goalId: string, direction: 'up' | 'down') => {
    const next = moveItemById(goals, goalId, direction)
    if (next === goals) return
    await persistOrder(next, goals)
  }

  const editorTitle =
    editor?.kind === 'create'
      ? t('goalsPage.addGoal')
      : editor?.kind === 'edit'
        ? t('goalsPage.editGoal', { label: editor.goal.label })
        : null
  const selectedGoalId = editor?.kind === 'edit' ? editor.goal.id : null
  const drawerColors = goals.map((goal) => goal.color)

  return (
    <section className="page">
      <EmailVerificationBanner />

      <header className="page-header">
        <h1>{t('goalsPage.title')}</h1>
        <button type="button" className="button" onClick={() => openEditor({ kind: 'create' })}>
          {t('goalsPage.addGoal')}
        </button>
      </header>

      <div className="limit-pills" aria-label={t('goalsPage.hint', { limit: visibleLimit, count: visibleCount })}>
        <span className="limit-pill">
          {t('goalsPage.hintCompact', { limit: visibleLimit, count: visibleCount })}
        </span>
        <span className="limit-pill">
          {t('goalsPage.statsHintCompact', { limit: statsLimit, count: statsCount })}
        </span>
      </div>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {pendingDelete ? (
        <ConfirmDialog
          open
          title={t('confirm.deleteGoalTitle')}
          message={t('confirm.deleteGoal', { label: pendingDelete.label })}
          confirmLabel={t('common.delete')}
          onCancel={() => setPendingDelete(null)}
          onConfirm={() => {
            const goal = pendingDelete
            setPendingDelete(null)
            void handleDelete(goal)
          }}
        />
      ) : null}
      {isLoading ? <p className="muted">{t('common.loadingGoals')}</p> : null}

      <EditorDrawer
        open={Boolean(editor && editorTitle)}
        title={editorTitle ?? ''}
        onClose={closeEditor}
        accentColors={drawerColors}
        footer={
          <div className="button-row">
            <button
              type="submit"
              form="goal-editor-form"
              className="button"
              disabled={isSaving}
            >
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
        }
      >
        <form
          id="goal-editor-form"
          className="form appearance-form-drawer"
          onSubmit={(event) => void handleSubmit(event)}
        >
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
          <div className="form-field-row">
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
          </div>
          <GoalIconEditor
            color={draftColor}
            onColorChange={setDraftColor}
            emoji={draftEmoji}
            onEmojiChange={setDraftEmoji}
            goal={editor?.kind === 'edit' ? editor.goal : undefined}
            onGoalChange={
              editor?.kind === 'edit'
                ? (updated) => {
                    setEditor({ kind: 'edit', goal: updated })
                    setGoals((current) =>
                      current.map((item) => (item.id === updated.id ? updated : item)),
                    )
                    if (updated.icon_type === 'emoji') {
                      setDraftEmoji(updated.icon)
                    }
                    setDraftColor(updated.color)
                  }
                : undefined
            }
            disabled={isSaving}
          />
        </form>
      </EditorDrawer>

      <div className="goals-list">
        {goals.map((goal, index) => (
          <article
            key={goal.id}
            className={[
              'card',
              'goal-card',
              draggingId === goal.id ? 'is-dragging' : '',
              selectedGoalId === goal.id ? 'is-selected' : '',
              dropTarget?.id === goal.id ? `is-drop-${dropTarget.edge}` : '',
            ]
              .filter(Boolean)
              .join(' ')}
            onDragOver={(event: DragEvent) => {
              if (!draggingId || draggingId === goal.id) return
              event.preventDefault()
              const edge = dropEdgeFromClientY(event.clientY, event.currentTarget)
              setDropTarget((current) =>
                current?.id === goal.id && current.edge === edge
                  ? current
                  : { id: goal.id, edge },
              )
            }}
            onDragLeave={(event: DragEvent) => {
              if (!event.currentTarget.contains(event.relatedTarget as Node)) {
                setDropTarget((current) => (current?.id === goal.id ? null : current))
              }
            }}
            onDrop={(event: DragEvent) => {
              event.preventDefault()
              const edge =
                dropTarget?.id === goal.id
                  ? dropTarget.edge
                  : dropEdgeFromClientY(event.clientY, event.currentTarget)
              void handleDrop(goal.id, edge)
            }}
          >
            <header className="goal-card-header">
              <div className="goal-card-title-row">
                <span
                  className="goal-card-icon-wrap"
                  style={{
                    background: moodSubtleFill(goal.color),
                    filter: moodGlowFilter(goal.color, 'xs'),
                  }}
                >
                  <GoalIcon
                    style={{
                      color: goal.color,
                      icon_type: goal.icon_type,
                      icon: goal.icon,
                    }}
                    className="goal-card-icon"
                  />
                </span>
                <h2>{goal.label}</h2>
                <div className="list-row-actions">
                  <IconButton
                    label={t('common.edit')}
                    size="sm"
                    onClick={() => openEditor({ kind: 'edit', goal })}
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    label={t('goalsPage.moveUp')}
                    size="sm"
                    disabled={index === 0}
                    onClick={() => void handleMove(goal.id, 'up')}
                  >
                    <ArrowUpIcon />
                  </IconButton>
                  <IconButton
                    label={t('goalsPage.moveDown')}
                    size="sm"
                    disabled={index === goals.length - 1}
                    onClick={() => void handleMove(goal.id, 'down')}
                  >
                    <ArrowDownIcon />
                  </IconButton>
                  <IconButton
                    label={t('common.delete')}
                    size="sm"
                    variant="danger"
                    onClick={() => setPendingDelete(goal)}
                  >
                    <DeleteIcon />
                  </IconButton>
                  <DragHandle
                    label={t('goalsPage.dragGoal', { label: goal.label })}
                    onDragStart={() => {
                      setDraggingId(goal.id)
                      setDropTarget(null)
                    }}
                    onDragEnd={clearDrag}
                    onMoveUp={() => void handleMove(goal.id, 'up')}
                    onMoveDown={() => void handleMove(goal.id, 'down')}
                  />
                </div>
              </div>
              <div className="goal-card-toggles">
                <label className="tag-visibility-toggle" title={t('goalsPage.showOnEntry')}>
                  <input
                    type="checkbox"
                    checked={goal.show_on_entry}
                    disabled={
                      togglingGoalId === goal.id || (!goal.show_on_entry && atVisibleLimit)
                    }
                    onChange={() => void handleToggleShowOnEntry(goal)}
                  />
                  <span>{t('goalsPage.showOnEntryShort')}</span>
                </label>
                <label className="tag-visibility-toggle" title={t('goalsPage.showInStats')}>
                  <input
                    type="checkbox"
                    checked={goal.show_in_stats}
                    disabled={
                      togglingGoalId === goal.id || (!goal.show_in_stats && atStatsLimit)
                    }
                    onChange={() => void handleToggleShowInStats(goal)}
                  />
                  <span>{t('goalsPage.showInStatsShort')}</span>
                </label>
              </div>
            </header>
            <div className="goal-card-meta">
              <p className="muted goal-meta">
                {goal.ends_on
                  ? t('goalsPage.dateRangeLabel', {
                      start: goal.starts_on,
                      end: goal.ends_on,
                    })
                  : t('goalsPage.startsOnLabel', { date: goal.starts_on })}
              </p>
              <p className="goal-week-progress">
                {t('goalsPage.weekProgress', {
                  done: goal.completed_this_week,
                  target: goal.times_per_week,
                })}
              </p>
            </div>
          </article>
        ))}
      </div>

      <p className="muted">
        <Link to="/">{t('common.backToEntries')}</Link>
      </p>
    </section>
  )
}
