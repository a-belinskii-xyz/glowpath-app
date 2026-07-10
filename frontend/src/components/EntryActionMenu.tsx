import { useEffect, useRef } from 'react'

import { Link } from 'react-router-dom'

import type { MoodEntryPublic } from '../types/mood'
import { formatTime } from '../lib/datetime'

type EntryActionMenuProps = {
  entry: MoodEntryPublic
  timeZone: string
  onClose: () => void
  onDelete: (entryId: string) => void
}

export function EntryActionMenu({ entry, timeZone, onClose, onDelete }: EntryActionMenuProps) {
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      if (dialogRef.current && !dialogRef.current.contains(event.target as Node)) {
        onClose()
      }
    }
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKey)
    }
  }, [onClose])

  const handleDelete = () => {
    if (window.confirm('Delete this mood entry?')) {
      onDelete(entry.id)
    }
    onClose()
  }

  return (
    <div className="entry-menu-backdrop">
      <div className="entry-menu" ref={dialogRef} role="dialog" aria-label="Entry actions">
        <div className="entry-menu-header">
          <span className="entry-menu-score">
            {entry.score_emoji} {entry.score_label}
          </span>
          <span className="muted">{formatTime(entry.recorded_at, timeZone)}</span>
        </div>
        {entry.note ? <p className="entry-menu-note">{entry.note}</p> : null}
        <div className="entry-menu-actions">
          <Link className="button button-secondary" to={`/entries/${entry.id}/edit`} onClick={onClose}>
            Edit
          </Link>
          <button type="button" className="button button-danger" onClick={handleDelete}>
            Delete
          </button>
          <button type="button" className="button button-secondary" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
