import { useEffect, useRef, useState } from 'react'

import { Link } from 'react-router-dom'

import type { MoodEntryPublic } from '../types/mood'

type EntryActionMenuProps = {
  entry: MoodEntryPublic
  onDelete: (entryId: string) => void
}

export function EntryActionMenu({ entry, onDelete }: EntryActionMenuProps) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) {
      return
    }

    const handleClick = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKey)
    }
  }, [isOpen])

  const handleDelete = () => {
    if (window.confirm('Delete this mood entry?')) {
      onDelete(entry.id)
    }
    setIsOpen(false)
  }

  return (
    <div className="entry-overflow" ref={containerRef}>
      <button
        type="button"
        className="entry-overflow-trigger"
        aria-label="Entry actions"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
      >
        <span aria-hidden="true">⋮</span>
      </button>
      {isOpen ? (
        <div className="entry-overflow-menu" role="menu" aria-label="Entry actions">
          <Link
            className="entry-overflow-item"
            role="menuitem"
            to={`/entries/${entry.id}`}
            onClick={() => setIsOpen(false)}
          >
            Open
          </Link>
          <Link
            className="entry-overflow-item"
            role="menuitem"
            to={`/entries/${entry.id}/edit`}
            onClick={() => setIsOpen(false)}
          >
            Edit
          </Link>
          <button
            type="button"
            className="entry-overflow-item entry-overflow-item-danger"
            role="menuitem"
            onClick={handleDelete}
          >
            Delete
          </button>
        </div>
      ) : null}
    </div>
  )
}
