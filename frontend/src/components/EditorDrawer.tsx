import { useEffect, useId, useMemo, useRef, type CSSProperties, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

import { useLocale } from '../context/LocaleContext'

type EditorDrawerProps = {
  open: boolean
  title: string
  description?: string
  children: ReactNode
  footer?: ReactNode
  onClose: () => void
  accentColors?: string[]
}

function focusableElements(container: HTMLElement | null): HTMLElement[] {
  if (!container) {
    return []
  }
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  )
}

export function EditorDrawer({
  open,
  title,
  description,
  children,
  footer,
  onClose,
  accentColors = [],
}: EditorDrawerProps) {
  const { t } = useLocale()
  const titleId = useId()
  const descriptionId = useId()
  const panelRef = useRef<HTMLDivElement>(null)
  // Callers often pass an inline onClose; re-running the focus effect on every render
  // would steal focus from a field while the user types.
  const onCloseRef = useRef(onClose)
  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])
  const backdropStyle = useMemo<CSSProperties>(() => {
    const fallback = ['#94a3b8', '#cbd5e1', '#e2e8f0', '#a5b4fc']
    const palette = accentColors.filter(Boolean)
    const colors = (palette.length > 0 ? palette : fallback).slice(0, 8)
    const seed = `${title}:${colors.join('|')}`
    const pick = (index: number) => colors[(seed.charCodeAt(index % seed.length) + index) % colors.length]
    return {
      '--editor-drawer-fog': `
        radial-gradient(circle at 16% 18%, ${pick(0)}44 0%, transparent 38%),
        radial-gradient(circle at 78% 22%, ${pick(1)}33 0%, transparent 34%),
        radial-gradient(circle at 68% 76%, ${pick(2)}40 0%, transparent 40%),
        radial-gradient(circle at 28% 72%, ${pick(3)}30 0%, transparent 36%)
      `,
    } as CSSProperties
  }, [accentColors, title])

  useEffect(() => {
    if (!open) {
      return
    }

    const previous = document.activeElement as HTMLElement | null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const focusFirst = () => {
      if (panelRef.current?.contains(document.activeElement)) {
        return
      }
      const [first] = focusableElements(panelRef.current)
      first?.focus()
    }
    const timeout = window.setTimeout(focusFirst, 0)

    const onKeyDown = (event: KeyboardEvent) => {
      // Yield to stacked modals (crop, confirm) opened above this drawer.
      const modals = document.querySelectorAll<HTMLElement>('[aria-modal="true"]')
      const topModal = modals.length > 0 ? modals[modals.length - 1] : null
      if (topModal && topModal !== panelRef.current) {
        return
      }

      if (event.key === 'Escape') {
        event.preventDefault()
        onCloseRef.current()
        return
      }

      if (event.key !== 'Tab') {
        return
      }

      const elements = focusableElements(panelRef.current)
      if (elements.length === 0) {
        return
      }
      const first = elements[0]
      const last = elements[elements.length - 1]
      const active = document.activeElement

      if (event.shiftKey) {
        if (active === first || !panelRef.current?.contains(active)) {
          event.preventDefault()
          last.focus()
        }
        return
      }

      if (active === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => {
      window.clearTimeout(timeout)
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
      previous?.focus?.({ preventScroll: true })
    }
  }, [open])

  if (!open) {
    return null
  }

  return createPortal(
    <div
      className="editor-drawer-backdrop"
      style={backdropStyle}
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose()
        }
      }}
    >
      <div
        ref={panelRef}
        className="editor-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
      >
        <div className="editor-drawer-header">
          <div className="editor-drawer-heading">
            <h2 id={titleId}>{title}</h2>
            {description ? (
              <p id={descriptionId} className="editor-drawer-description">
                {description}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            className="button button-secondary button-small"
            onClick={onClose}
          >
            {t('common.close')}
          </button>
        </div>
        <div className="editor-drawer-body">{children}</div>
        {footer ? <div className="editor-drawer-footer">{footer}</div> : null}
      </div>
    </div>,
    document.body,
  )
}
