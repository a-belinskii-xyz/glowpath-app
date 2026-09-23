import { useState } from 'react'

import { AttachmentImage } from './AttachmentImage'
import { DragHandle } from './DragHandle'
import { IconButton } from './IconButton'
import { DeleteIcon } from './icons'
import { useLocale } from '../context/LocaleContext'
import { moveItem } from '../lib/listReorder'

export type CollagePhotoDraft = {
  key: string
  name: string
  preview:
    | { type: 'url'; url: string }
    | { type: 'attachment'; entryId: string; attachmentId: string }
}

type PhotoCollageEditorProps = {
  photos: CollagePhotoDraft[]
  onChange: (next: CollagePhotoDraft[]) => void
  onRemove: (key: string) => void
}

function swapItems<T>(items: T[], fromIndex: number, toIndex: number): T[] {
  if (
    fromIndex < 0 ||
    toIndex < 0 ||
    fromIndex >= items.length ||
    toIndex >= items.length ||
    fromIndex === toIndex
  ) {
    return items
  }
  const next = [...items]
  const left = next[fromIndex]
  const right = next[toIndex]
  if (left === undefined || right === undefined) {
    return items
  }
  next[fromIndex] = right
  next[toIndex] = left
  return next
}

export function PhotoCollageEditor({ photos, onChange, onRemove }: PhotoCollageEditorProps) {
  const { t } = useLocale()
  const [draggingKey, setDraggingKey] = useState<string | null>(null)
  const [dropTargetKey, setDropTargetKey] = useState<string | null>(null)

  if (photos.length === 0) {
    return null
  }

  const movePhoto = (key: string, direction: 'up' | 'down') => {
    const fromIndex = photos.findIndex((photo) => photo.key === key)
    if (fromIndex < 0) {
      return
    }
    const toIndex = direction === 'up' ? fromIndex - 1 : fromIndex + 1
    const next = moveItem(photos, fromIndex, toIndex)
    if (next !== photos) {
      onChange(next)
    }
  }

  const clearDrag = () => {
    setDraggingKey(null)
    setDropTargetKey(null)
  }

  const handleDropOn = (targetKey: string) => {
    if (!draggingKey || draggingKey === targetKey) {
      clearDrag()
      return
    }
    const fromIndex = photos.findIndex((photo) => photo.key === draggingKey)
    const toIndex = photos.findIndex((photo) => photo.key === targetKey)
    clearDrag()
    if (fromIndex < 0 || toIndex < 0) {
      return
    }
    onChange(swapItems(photos, fromIndex, toIndex))
  }

  return (
    <div className="photo-collage-editor">
      <p className="form-label">{t('entries.photoCollage')}</p>
      <p className="muted photo-collage-editor-hint">{t('entries.photoCollageHint')}</p>
      <div
        className="entry-photo-collage photo-collage-editor-grid"
        data-count={Math.min(photos.length, 5)}
      >
        {photos.map((photo, index) => {
          const isDragging = draggingKey === photo.key
          const isDropTarget = dropTargetKey === photo.key && draggingKey !== photo.key

          return (
            <div
              key={photo.key}
              className={[
                'entry-photo-collage-item',
                'photo-collage-editor-item',
                isDragging ? 'is-dragging' : '',
                isDropTarget ? 'is-drop-target' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              draggable
              onDragStart={(event) => {
                event.dataTransfer.effectAllowed = 'move'
                event.dataTransfer.setData('text/plain', photo.key)
                setDraggingKey(photo.key)
              }}
              onDragEnd={clearDrag}
              onDragOver={(event) => {
                if (!draggingKey || draggingKey === photo.key) {
                  return
                }
                event.preventDefault()
                event.dataTransfer.dropEffect = 'move'
                if (dropTargetKey !== photo.key) {
                  setDropTargetKey(photo.key)
                }
              }}
              onDragLeave={(event) => {
                const related = event.relatedTarget
                if (related instanceof Node && event.currentTarget.contains(related)) {
                  return
                }
                if (dropTargetKey === photo.key) {
                  setDropTargetKey(null)
                }
              }}
              onDrop={(event) => {
                event.preventDefault()
                handleDropOn(photo.key)
              }}
            >
              {photo.preview.type === 'url' ? (
                <img
                  className="entry-photo-collage-image"
                  src={photo.preview.url}
                  alt={photo.name}
                  draggable={false}
                />
              ) : (
                <AttachmentImage
                  className="entry-photo-collage-image"
                  entryId={photo.preview.entryId}
                  attachmentId={photo.preview.attachmentId}
                  alt={photo.name}
                />
              )}

              {isDropTarget ? (
                <span className="photo-collage-editor-swap-badge" aria-hidden>
                  ↔
                </span>
              ) : null}

              <div className="photo-collage-editor-toolbar">
                <span className="photo-collage-editor-mobile-handle">
                  <DragHandle
                    label={t('entries.reorderPhoto', { name: photo.name })}
                    onMoveUp={index > 0 ? () => movePhoto(photo.key, 'up') : undefined}
                    onMoveDown={
                      index < photos.length - 1
                        ? () => movePhoto(photo.key, 'down')
                        : undefined
                    }
                    onDragStart={() => setDraggingKey(photo.key)}
                    onDragEnd={clearDrag}
                  />
                </span>
                <IconButton
                  label={t('common.remove')}
                  variant="danger"
                  size="sm"
                  className="photo-collage-editor-remove"
                  onClick={(event) => {
                    event.preventDefault()
                    event.stopPropagation()
                    onRemove(photo.key)
                  }}
                  onPointerDown={(event) => event.stopPropagation()}
                  onDragStart={(event) => event.preventDefault()}
                >
                  <DeleteIcon />
                </IconButton>
              </div>
              <span className="photo-collage-editor-index" aria-hidden>
                {index + 1}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
