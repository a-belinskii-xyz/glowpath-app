import { useEffect, useRef, useState, type ReactNode } from 'react'

import { useLocale } from '../context/LocaleContext'
import { IconButton } from './IconButton'
import { MoreIcon } from './icons'

export type PopupMenuItem = {
  id: string
  label: string
  onSelect: () => void
  danger?: boolean
}

type PopupMenuProps = {
  ariaLabel: string
  items: PopupMenuItem[]
  trigger?: ReactNode
}

export function PopupMenu({ ariaLabel, items, trigger }: PopupMenuProps) {
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
      {trigger ? (
        <button
          type="button"
          className="popup-menu-trigger"
          aria-label={ariaLabel}
          aria-haspopup="menu"
          aria-expanded={isOpen}
          onClick={() => setIsOpen((open) => !open)}
        >
          {trigger}
        </button>
      ) : (
        <IconButton
          label={ariaLabel}
          variant="ghost"
          size="sm"
          aria-haspopup="menu"
          aria-expanded={isOpen}
          onClick={() => setIsOpen((open) => !open)}
        >
          <MoreIcon />
        </IconButton>
      )}
      {isOpen ? (
        <div className="entry-overflow-menu popup-menu-panel" role="menu" aria-label={ariaLabel}>
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`entry-overflow-item${item.danger ? ' entry-overflow-item-danger' : ''}`}
              role="menuitem"
              onClick={() => {
                setIsOpen(false)
                item.onSelect()
              }}
            >
              {item.label}
            </button>
          ))}
          {items.length === 0 ? (
            <span className="entry-overflow-item" role="menuitem" aria-disabled="true">
              {t('common.close')}
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
