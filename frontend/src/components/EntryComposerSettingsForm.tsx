import { type DragEvent, useCallback, useEffect, useRef, useState } from 'react'

import { patchMoodPreferences } from '../api/moodPreferences'
import { DragHandle } from './DragHandle'
import { IconButton } from './IconButton'
import { ArrowDownIcon, ArrowUpIcon } from './icons'
import { PageErrorAlert } from './PageErrorAlert'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import {
  composerLayoutToPreferences,
  type ResolvedComposerBlock,
} from '../lib/entryComposer'
import { ApiError, formatApiError } from '../lib/errors'
import {
  dropEdgeFromClientY,
  dropIndexForEdge,
  moveItem,
  type DropEdge,
} from '../lib/listReorder'

const SAVE_DELAY_MS = 400

export function EntryComposerSettingsForm() {
  const { t } = useLocale()
  const { composerLayout, isLoading, setPreferences } = useMoodPreferences()
  const [draft, setDraft] = useState<ResolvedComposerBlock[]>(composerLayout)
  const [error, setError] = useState<string | null>(null)
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [dropTarget, setDropTarget] = useState<{ id: string; edge: DropEdge } | null>(null)
  const saveTimerRef = useRef<number | null>(null)
  const draftRef = useRef(draft)

  useEffect(() => {
    setDraft(composerLayout)
    draftRef.current = composerLayout
  }, [composerLayout])

  useEffect(() => {
    return () => {
      if (saveTimerRef.current != null) {
        window.clearTimeout(saveTimerRef.current)
      }
    }
  }, [])

  const persist = useCallback(
    async (next: ResolvedComposerBlock[]) => {
      setError(null)
      try {
        const saved = await patchMoodPreferences({
          composer_blocks: composerLayoutToPreferences(next),
        })
        setPreferences(saved)
      } catch (err) {
        setDraft(draftRef.current)
        if (err instanceof ApiError && err.status === 403) {
          setError(t('errors.verifyToManageMoodPreferences'))
        } else {
          setError(formatApiError(err, t, 'errors.failedSave'))
        }
      }
    },
    [setPreferences, t],
  )

  const schedulePersist = useCallback(
    (next: ResolvedComposerBlock[]) => {
      draftRef.current = next
      setDraft(next)
      if (saveTimerRef.current != null) {
        window.clearTimeout(saveTimerRef.current)
      }
      saveTimerRef.current = window.setTimeout(() => {
        void persist(next)
      }, SAVE_DELAY_MS)
    },
    [persist],
  )

  const movable = draft.filter((block) => !block.pinned)
  const moodBlock = draft.find((block) => block.pinned)

  const toggleEnabled = (id: string) => {
    const block = draft.find((item) => item.id === id)
    if (!block || block.pinned) {
      return
    }
    schedulePersist(
      draft.map((item) =>
        item.id === id ? { ...item, enabled: !item.enabled } : item,
      ),
    )
  }

  const moveBlock = (id: string, direction: 'up' | 'down') => {
    const fromIndex = movable.findIndex((item) => item.id === id)
    if (fromIndex < 0) {
      return
    }
    const toIndex = direction === 'up' ? fromIndex - 1 : fromIndex + 1
    if (toIndex < 0 || toIndex >= movable.length) {
      return
    }
    const nextMovable = moveItem(movable, fromIndex, toIndex)
    schedulePersist(moodBlock ? [moodBlock, ...nextMovable] : nextMovable)
  }

  const clearDrag = () => {
    setDraggingId(null)
    setDropTarget(null)
  }

  const handleDropOn = (targetId: string, edge: DropEdge) => {
    if (!draggingId || draggingId === targetId) {
      clearDrag()
      return
    }
    const fromIndex = movable.findIndex((item) => item.id === draggingId)
    const targetIndex = movable.findIndex((item) => item.id === targetId)
    if (fromIndex < 0 || targetIndex < 0) {
      clearDrag()
      return
    }
    const toIndex = dropIndexForEdge(fromIndex, targetIndex, edge)
    const nextMovable = moveItem(movable, fromIndex, toIndex)
    clearDrag()
    schedulePersist(moodBlock ? [moodBlock, ...nextMovable] : nextMovable)
  }

  if (isLoading) {
    return <p className="muted">{t('common.loadingMoodPreferences')}</p>
  }

  return (
    <>
      <PageErrorAlert error={error} />
      <p className="muted entry-composer-lead">{t('entryComposer.lead')}</p>
      <ul className="entry-composer-list">
        {draft.map((block) => {
          const isPinned = block.pinned
          const movableIndex = movable.findIndex((item) => item.id === block.id)
          const isDragging = draggingId === block.id
          const dropEdge =
            dropTarget?.id === block.id && !isPinned ? dropTarget.edge : null
          return (
            <li
              key={block.id}
              className={[
                'entry-composer-row',
                isPinned ? 'is-pinned' : '',
                isDragging ? 'is-dragging' : '',
                dropEdge ? `is-drop-${dropEdge}` : '',
                !block.enabled && !isPinned ? 'is-disabled' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              onDragOver={(event: DragEvent) => {
                if (!draggingId || isPinned || draggingId === block.id) {
                  return
                }
                event.preventDefault()
                const edge = dropEdgeFromClientY(event.clientY, event.currentTarget)
                setDropTarget((current) =>
                  current?.id === block.id && current.edge === edge
                    ? current
                    : { id: block.id, edge },
                )
              }}
              onDrop={(event: DragEvent) => {
                if (!draggingId || isPinned) {
                  return
                }
                event.preventDefault()
                const edge =
                  dropTarget?.id === block.id
                    ? dropTarget.edge
                    : dropEdgeFromClientY(event.clientY, event.currentTarget)
                handleDropOn(block.id, edge)
              }}
            >
              <label className="entry-composer-toggle">
                <input
                  type="checkbox"
                  checked={block.enabled}
                  disabled={isPinned}
                  onChange={() => toggleEnabled(block.id)}
                />
                <span>
                  <span className="entry-composer-title">{t(block.labelKey)}</span>
                  {block.hintKey ? (
                    <span className="entry-composer-hint muted">{t(block.hintKey)}</span>
                  ) : null}
                </span>
              </label>
              {isPinned ? (
                <span className="entry-composer-locked muted">{t('entryComposer.required')}</span>
              ) : (
                <div className="list-row-actions entry-composer-actions">
                  <div className="list-row-actions-extra">
                    <IconButton
                      label={t('entryComposer.moveUp')}
                      size="sm"
                      disabled={movableIndex <= 0}
                      onClick={() => moveBlock(block.id, 'up')}
                    >
                      <ArrowUpIcon />
                    </IconButton>
                    <IconButton
                      label={t('entryComposer.moveDown')}
                      size="sm"
                      disabled={movableIndex < 0 || movableIndex >= movable.length - 1}
                      onClick={() => moveBlock(block.id, 'down')}
                    >
                      <ArrowDownIcon />
                    </IconButton>
                    <DragHandle
                      label={t('entryComposer.dragBlock', { label: t(block.labelKey) })}
                      onDragStart={() => {
                        setDraggingId(block.id)
                        setDropTarget(null)
                      }}
                      onDragEnd={clearDrag}
                      onMoveUp={() => moveBlock(block.id, 'up')}
                      onMoveDown={() => moveBlock(block.id, 'down')}
                    />
                  </div>
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </>
  )
}
