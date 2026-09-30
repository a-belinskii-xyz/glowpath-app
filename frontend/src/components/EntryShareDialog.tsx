import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

import { sendEntryShareImageToTelegram } from '../api/moodEntries'
import { Alert } from './Alert'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { useColorScheme } from '../hooks/useColorScheme'
import { intlLocale } from '../i18n/t'
import { renderEntryShareImage, shareImageFileName } from '../lib/entryShareImage'
import { isGuestDiaryMode } from '../lib/guestMode'
import { entryMoodColor, entryMoodStyle } from '../lib/moodScale'
import { canShareFile, downloadBlob, shareFile } from '../lib/shareFile'
import { hapticNotification, isTelegramMiniApp } from '../platform/telegram'
import type { MoodEntryPublic } from '../types/mood'

type EntryShareDialogProps = {
  entry: MoodEntryPublic
  timeZone: string
  onClose: () => void
}

type Rendered = { file: File; previewUrl: string }

export function EntryShareDialog({ entry, timeZone, onClose }: EntryShareDialogProps) {
  const { locale, t } = useLocale()
  const { scores } = useMoodPreferences()
  const colorScheme = useColorScheme()
  const titleId = useId()
  const closeRef = useRef<HTMLButtonElement>(null)
  const [rendered, setRendered] = useState<Rendered | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [isSending, setIsSending] = useState(false)

  const inTelegram = useMemo(() => isTelegramMiniApp(), [])
  const canSendToChat = inTelegram && !isGuestDiaryMode()

  useEffect(() => {
    let cancelled = false
    let previewUrl: string | null = null
    setRendered(null)
    setError(null)
    renderEntryShareImage({
      entry,
      moodColor: entryMoodColor(entry, scores),
      moodIcon: entryMoodStyle(entry, scores, locale),
      timeZone,
      dateLocale: intlLocale(locale),
      scheme: colorScheme,
      brand: t('brand'),
    })
      .then((blob) => {
        if (cancelled) {
          return
        }
        const file = new File([blob], shareImageFileName(entry, timeZone), { type: 'image/png' })
        previewUrl = URL.createObjectURL(blob)
        setRendered({ file, previewUrl })
      })
      .catch(() => {
        if (!cancelled) {
          setError(t('shareImage.renderFailed'))
        }
      })
    return () => {
      cancelled = true
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [entry, scores, locale, timeZone, colorScheme, t])

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    const previous = document.activeElement as HTMLElement | null
    document.body.style.overflow = 'hidden'
    closeRef.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        event.stopImmediatePropagation()
        onClose()
      }
    }
    document.addEventListener('keydown', onKeyDown, true)
    return () => {
      document.removeEventListener('keydown', onKeyDown, true)
      document.body.style.overflow = previousOverflow
      previous?.focus?.({ preventScroll: true })
    }
  }, [onClose])

  const shareable = rendered ? canShareFile(rendered.file) : false

  const handleShare = async () => {
    if (!rendered) {
      return
    }
    setError(null)
    setNotice(null)
    try {
      await shareFile(rendered.file)
    } catch {
      setError(t('shareImage.shareFailed'))
    }
  }

  const handleDownload = () => {
    if (!rendered) {
      return
    }
    setError(null)
    setNotice(null)
    downloadBlob(rendered.file, rendered.file.name)
  }

  const handleSendToChat = async () => {
    if (!rendered || isSending) {
      return
    }
    setIsSending(true)
    setError(null)
    setNotice(null)
    try {
      await sendEntryShareImageToTelegram(entry.id, rendered.file)
      hapticNotification('success')
      setNotice(t('shareImage.sentToChat'))
    } catch {
      hapticNotification('error')
      setError(t('shareImage.sendFailed'))
    } finally {
      setIsSending(false)
    }
  }

  // Inside Telegram the share sheet is often missing and <a download> is ignored,
  // so the bot chat is the primary route there; on the web, download is the fallback.
  const showDownload = !inTelegram || !canSendToChat
  const primary: 'share' | 'chat' | 'download' = shareable
    ? 'share'
    : canSendToChat
      ? 'chat'
      : 'download'

  return createPortal(
    <div
      className="confirm-dialog-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose()
        }
      }}
    >
      <div
        className="card confirm-dialog share-image-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <h2 id={titleId} className="confirm-dialog-title">
          {t('shareImage.title')}
        </h2>
        <div className="share-image-preview" aria-busy={!rendered && !error}>
          {rendered ? (
            <img src={rendered.previewUrl} alt={t('shareImage.previewAlt')} />
          ) : !error ? (
            <span className="share-image-preview-loading muted">{t('shareImage.rendering')}</span>
          ) : null}
        </div>
        {error ? <Alert variant="error">{error}</Alert> : null}
        {notice ? <Alert variant="success">{notice}</Alert> : null}
        <div className="share-image-actions">
          {shareable ? (
            <button
              type="button"
              className={primary === 'share' ? 'button' : 'button button-secondary'}
              disabled={!rendered}
              onClick={() => void handleShare()}
            >
              {t('shareImage.share')}
            </button>
          ) : null}
          {canSendToChat ? (
            <button
              type="button"
              className={primary === 'chat' ? 'button' : 'button button-secondary'}
              disabled={!rendered || isSending}
              onClick={() => void handleSendToChat()}
            >
              {isSending ? t('shareImage.sending') : t('shareImage.sendToChat')}
            </button>
          ) : null}
          {showDownload ? (
            <button
              type="button"
              className={primary === 'download' ? 'button' : 'button button-secondary'}
              disabled={!rendered}
              onClick={handleDownload}
            >
              {t('shareImage.download')}
            </button>
          ) : null}
          <button
            ref={closeRef}
            type="button"
            className="button button-secondary"
            onClick={onClose}
          >
            {t('common.close')}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
