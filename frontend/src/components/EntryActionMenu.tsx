import { useEffect, useRef, useState } from 'react'

import { Link } from 'react-router-dom'

import { ConfirmDialog } from './ConfirmDialog'
import { useLocale } from '../context/LocaleContext'
import type { MoodEntryPublic } from '../types/mood'

type EntryActionMenuProps = {
  entry: MoodEntryPublic
  onDelete: (entryId: string) => void
  onToggleFavorite: (entryId: string, isFavorite: boolean) => void
}

export function EntryActionMenu({ entry, onDelete, onToggleFavorite }: EntryActionMenuProps) {
  const { t } = useLocale()
  const [isOpen, setIsOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
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

  const handleDeleteClick = () => {
    setIsOpen(false)
    setConfirmDelete(true)
  }

  const handleToggleFavorite = () => {
    onToggleFavorite(entry.id, !entry.is_favorite)
    setIsOpen(false)
  }

  return (
    <div className="entry-overflow" ref={containerRef}>
      {confirmDelete ? (
        <ConfirmDialog
          open
          title={t('confirm.deleteEntryTitle')}
          message={t('confirm.deleteEntry')}
          confirmLabel={t('common.delete')}
          onCancel={() => setConfirmDelete(false)}
          onConfirm={() => {
            setConfirmDelete(false)
            onDelete(entry.id)
          }}
        />
      ) : null}
      <button
        type="button"
        className="entry-overflow-trigger"
        aria-label={t('entryActions.ariaLabel')}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
      >
        <span aria-hidden="true">⋮</span>
      </button>
      {isOpen ? (
        <div className="entry-overflow-menu" role="menu" aria-label={t('entryActions.ariaLabel')}>
          <Link
            className="entry-overflow-item"
            role="menuitem"
            to={`/entries/${entry.id}`}
            onClick={() => setIsOpen(false)}
          >
            {t('common.open')}
          </Link>
          <Link
            className="entry-overflow-item"
            role="menuitem"
            to={`/entries/${entry.id}/edit`}
            onClick={() => setIsOpen(false)}
          >
            {t('common.edit')}
          </Link>
          <button
            type="button"
            className="entry-overflow-item"
            role="menuitem"
            onClick={handleToggleFavorite}
          >
            {entry.is_favorite ? t('entries.removeFavorite') : t('entries.addFavorite')}
          </button>
          <button
            type="button"
            className="entry-overflow-item entry-overflow-item-danger"
            role="menuitem"
            onClick={handleDeleteClick}
          >
            {t('common.delete')}
          </button>
        </div>
      ) : null}
    </div>
  )
}
