import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { deleteMoodEntry, getMoodEntry, patchMoodEntry } from '../api/moodEntries'
import { Alert } from '../components/Alert'
import { AttachmentAudio } from '../components/AttachmentAudio'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { EntryAttachmentThumbs } from '../components/EntryAttachmentThumbs'
import { MarkdownNote } from '../components/MarkdownNote'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { intlLocale } from '../i18n/t'
import { ApiError } from '../lib/errors'
import { formatDayHeading, formatTime } from '../lib/datetime'
import type { MoodEntryPublic } from '../types/mood'

export function EntryDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { locale, t } = useLocale()
  const timeZone = user?.timezone ?? 'UTC'
  const dateLocale = intlLocale(locale)

  const [entry, setEntry] = useState<MoodEntryPublic | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isTogglingFavorite, setIsTogglingFavorite] = useState(false)

  useEffect(() => {
    if (!id) {
      setError(t('errors.entryIdMissing'))
      setIsLoading(false)
      return
    }

    const load = async () => {
      setIsLoading(true)
      try {
        const loaded = await getMoodEntry(id)
        setEntry(loaded)
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError(t('errors.verifyToViewEntry'))
        } else {
          setError(err instanceof Error ? err.message : t('errors.failedLoadEntry'))
        }
      } finally {
        setIsLoading(false)
      }
    }

    void load()
  }, [id, locale, t])

  const handleDelete = async () => {
    if (!entry || !window.confirm(t('confirm.deleteEntry'))) {
      return
    }
    setIsDeleting(true)
    setError(null)
    try {
      await deleteMoodEntry(entry.id)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.failedDeleteEntry'))
      setIsDeleting(false)
    }
  }

  const handleToggleFavorite = async () => {
    if (!entry || isTogglingFavorite) {
      return
    }
    const nextFavorite = !entry.is_favorite
    const previous = entry
    setEntry({ ...entry, is_favorite: nextFavorite })
    setIsTogglingFavorite(true)
    setError(null)
    try {
      const updated = await patchMoodEntry(entry.id, { is_favorite: nextFavorite })
      setEntry(updated)
    } catch (err) {
      setEntry(previous)
      setError(err instanceof Error ? err.message : t('errors.failedSaveEntry'))
    } finally {
      setIsTogglingFavorite(false)
    }
  }

  const audioAttachment = entry?.attachments.find((attachment) => attachment.kind === 'audio')

  return (
    <section className="page">
      <EmailVerificationBanner />
      <header className="page-header">
        <h1>{t('entries.moodEntry')}</h1>
        <Link className="button button-secondary" to="/">
          {t('common.backToEntries')}
        </Link>
      </header>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {isLoading ? <p className="muted">{t('common.loadingEntry')}</p> : null}

      {entry ? (
        <article className="entry-detail">
          <div className="entry-detail-hero">
            <span className="entry-detail-emoji" aria-hidden="true">
              {entry.score_emoji}
            </span>
            <div>
              <p className="entry-detail-score">
                {entry.is_favorite ? (
                  <span className="entry-favorite-mark" aria-hidden="true">
                    ★
                  </span>
                ) : null}
                {entry.score_label}
              </p>
              <p className="muted">
                {formatDayHeading(entry.recorded_at, timeZone, dateLocale)} ·{' '}
                {formatTime(entry.recorded_at, timeZone, dateLocale)}
              </p>
            </div>
          </div>

          {entry.note ? (
            <MarkdownNote content={entry.note} className="entry-detail-note" />
          ) : null}

          {entry.tags.length > 0 ? (
            <div className="entry-tags">
              {entry.tags.map((tag) => (
                <span key={tag.id} className="entry-tag">
                  {tag.label}
                </span>
              ))}
            </div>
          ) : null}

          {entry.goals.length > 0 ? (
            <div className="entry-tags entry-goals">
              {entry.goals.map((goal) => (
                <span key={goal.id} className="entry-tag entry-goal">
                  {goal.label}
                </span>
              ))}
            </div>
          ) : null}

          {audioAttachment ? (
            <AttachmentAudio entryId={entry.id} attachment={audioAttachment} />
          ) : null}

          <EntryAttachmentThumbs
            entryId={entry.id}
            attachments={entry.attachments}
            showAudioCount={false}
          />

          <div className="button-row">
            <button
              type="button"
              className={`button button-secondary${entry.is_favorite ? ' is-active' : ''}`}
              onClick={() => void handleToggleFavorite()}
              disabled={isTogglingFavorite}
              aria-pressed={entry.is_favorite}
            >
              {entry.is_favorite ? t('entries.removeFavorite') : t('entries.addFavorite')}
            </button>
            <Link className="button" to={`/entries/${entry.id}/edit`}>
              {t('common.edit')}
            </Link>
            <button
              type="button"
              className="button button-danger"
              onClick={() => void handleDelete()}
              disabled={isDeleting}
            >
              {isDeleting ? t('common.deleting') : t('common.delete')}
            </button>
          </div>
        </article>
      ) : null}
    </section>
  )
}
