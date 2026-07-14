import { useEffect, useRef, useState, type ReactNode } from 'react'

import { useLocale } from '../context/LocaleContext'

type PopupMenuProps = {
  label: ReactNode
  ariaLabel: string
  onEdit: () => void
  onDelete: () => void
}

export function PopupMenu({ label, ariaLabel, onEdit, onDelete }: PopupMenuProps) {
  const { t } = useLocale()
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

  return (
    <div className="popup-menu" ref={containerRef}>
      <button
        type="button"
        className="popup-menu-trigger"
        aria-label={ariaLabel}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
      >
        {label}
      </button>
      {isOpen ? (
        <div className="entry-overflow-menu popup-menu-panel" role="menu" aria-label={ariaLabel}>
          <button
            type="button"
            className="entry-overflow-item"
            role="menuitem"
            onClick={() => {
              setIsOpen(false)
              onEdit()
            }}
          >
            {t('common.edit')}
          </button>
          <button
            type="button"
            className="entry-overflow-item entry-overflow-item-danger"
            role="menuitem"
            onClick={() => {
              setIsOpen(false)
              onDelete()
            }}
          >
            {t('common.delete')}
          </button>
        </div>
      ) : null}
    </div>
  )
}
