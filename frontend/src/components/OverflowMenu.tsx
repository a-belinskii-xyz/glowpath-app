import { useEffect, useRef, useState, type ReactNode } from 'react'

import { useLocale } from '../context/LocaleContext'

export type OverflowMenuItem = {
  label: string
  onClick: () => void
  disabled?: boolean
  danger?: boolean
}

type OverflowMenuProps = {
  items: OverflowMenuItem[]
  className?: string
  label?: string
  children?: ReactNode
}

export function OverflowMenu({ items, className = '', label, children }: OverflowMenuProps) {
  const { t } = useLocale()
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const ariaLabel = label ?? t('common.moreActions')

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
    <div className={`entry-overflow${className ? ` ${className}` : ''}`} ref={containerRef}>
      <button
        type="button"
        className="entry-overflow-trigger"
        aria-label={ariaLabel}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
      >
        {children ?? <span aria-hidden="true">⋮</span>}
      </button>
      {isOpen ? (
        <div className="entry-overflow-menu" role="menu" aria-label={ariaLabel}>
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              role="menuitem"
              className={`entry-overflow-item${item.danger ? ' entry-overflow-item-danger' : ''}`}
              disabled={item.disabled}
              onClick={() => {
                if (item.disabled) return
                setIsOpen(false)
                item.onClick()
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}
