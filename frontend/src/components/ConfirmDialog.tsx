import { useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'

import { useLocale } from '../context/LocaleContext'
import { Alert } from './Alert'

export type ConfirmDialogProps = {
  open: boolean
  title: string
  message: string
  confirmLabel: string
  cancelLabel?: string
  /** Visual tone for destructive actions. */
  variant?: 'danger' | 'default'
  isBusy?: boolean
  error?: string | null
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  cancelLabel,
  variant = 'danger',
  isBusy = false,
  error = null,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const { t } = useLocale()
  const titleId = useId()
  const messageId = useId()
  const confirmRef = useRef<HTMLButtonElement>(null)
  const resolvedCancel = cancelLabel ?? t('common.cancel')

  useEffect(() => {
    if (!open) {
      return
    }
    const previous = document.activeElement as HTMLElement | null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    confirmRef.current?.focus()

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isBusy) {
        event.preventDefault()
        event.stopImmediatePropagation()
        onCancel()
      }
    }
    document.addEventListener('keydown', onKeyDown, true)
    return () => {
      document.removeEventListener('keydown', onKeyDown, true)
      document.body.style.overflow = previousOverflow
      previous?.focus?.()
    }
  }, [open, isBusy, onCancel])

  if (!open) {
    return null
  }

  return createPortal(
    <div
      className={`confirm-dialog-backdrop${variant === 'danger' ? ' confirm-dialog-backdrop--danger' : ''}`}
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isBusy) {
          onCancel()
        }
      }}
    >
      <div
        className={`card confirm-dialog${variant === 'danger' ? ' confirm-dialog--danger' : ''}`}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={messageId}
      >
        <h2 id={titleId} className="confirm-dialog-title">
          {title}
        </h2>
        <p id={messageId} className="confirm-dialog-message">
          {message}
        </p>
        {error ? <Alert variant="error">{error}</Alert> : null}
        <div className="button-row confirm-dialog-actions">
          <button
            type="button"
            className="button button-secondary"
            disabled={isBusy}
            onClick={onCancel}
          >
            {resolvedCancel}
          </button>
          <button
            ref={confirmRef}
            type="button"
            className={variant === 'danger' ? 'button button-danger' : 'button'}
            disabled={isBusy}
            onClick={onConfirm}
          >
            {isBusy ? t('common.saving') : confirmLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
