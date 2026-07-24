import { useEffect, useState, type CSSProperties } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { deleteMoodEntry, getMoodEntry, patchMoodEntry } from '../api/moodEntries'
import { Alert } from '../components/Alert'
import { AttachmentAudio } from '../components/AttachmentAudio'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { EntryAttachmentThumbs } from '../components/EntryAttachmentThumbs'
import { GoalIcon } from '../components/GoalIcon'
import { HeartIcon } from '../components/HeartIcon'
import { MarkdownNote } from '../components/MarkdownNote'
import { MoodScoreIcon } from '../components/MoodScoreIcon'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { intlLocale } from '../i18n/t'
import { ApiError } from '../lib/errors'
import { formatDayHeading, formatTime, entriesListPathForInstant } from '../lib/datetime'
import { getMoodScoreColor, getMoodScoreStyle } from '../lib/moodScale'
import type { MoodEntryPublic } from '../types/mood'

function EditIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M4 20h4.5L19.2 9.3a1.5 1.5 0 0 0 0-2.12L16.82 4.8a1.5 1.5 0 0 0-2.12 0L4 15.5V20z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      <path
        d="M13.5 6.5l4 4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  )
}

function DeleteIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M5 7h14M10 11v6M14 11v6M9 7l1-2h4l1 2M7 7l1 12a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2l1-12"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function EntryDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { locale, t } = useLocale()
  const { scores } = useMoodPreferences()
  const timeZone = user?.timezone ?? 'UTC'
  const dateLocale = intlLocale(locale)

  const [entry, setEntry] = useState<MoodEntryPublic | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
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
    if (!entry) {
      return
    }
    setConfirmDelete(false)
    setIsDeleting(true)
    setError(null)
    try {
      await deleteMoodEntry(entry.id)
      navigate(entriesListPathForInstant(entry.recorded_at, timeZone))
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
  const backToEntries = entry
    ? entriesListPathForInstant(entry.recorded_at, timeZone, entry.id)
    : '/'

  return (
    <section className="page">
      <EmailVerificationBanner />
      <header className="page-header">
        <h1>{t('entries.moodEntry')}</h1>
        <Link className="button button-secondary" to={backToEntries}>
          {t('common.backToEntries')}
        </Link>
      </header>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {confirmDelete && entry ? (
        <ConfirmDialog
          open
          title={t('confirm.deleteEntryTitle')}
          message={t('confirm.deleteEntry')}
          confirmLabel={t('common.delete')}
          isBusy={isDeleting}
          onCancel={() => setConfirmDelete(false)}
          onConfirm={() => void handleDelete()}
        />
      ) : null}
      {isLoading ? <p className="muted">{t('common.loadingEntry')}</p> : null}

      {entry ? (
        <article className="entry-detail">
          <div className="entry-detail-with-actions">
            <div className="entry-detail-main">
              <div className="entry-detail-hero">
                <MoodScoreIcon
                  style={getMoodScoreStyle(entry.score, scores)}
                  className="entry-detail-emoji"
                  fallbackScore={entry.score}
                />
                <div>
                  <p className="entry-detail-score">{entry.score_label}</p>
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
                      <GoalIcon
                        style={{
                          color: goal.color,
                          icon_type: goal.icon_type,
                          icon: goal.icon,
                        }}
                        className="entry-goal-icon"
                      />
                      {goal.label}
                    </span>
                  ))}
                </div>
              ) : null}

              {audioAttachment ? (
                <AttachmentAudio
                  entryId={entry.id}
                  attachment={audioAttachment}
                  accentColor={getMoodScoreColor(entry.score, scores)}
                />
              ) : null}

              <EntryAttachmentThumbs
                entryId={entry.id}
                attachments={entry.attachments}
                showAudioCount={false}
              />
            </div>

            <div className="entry-detail-actions" role="toolbar" aria-label={t('entryActions.ariaLabel')}>
              <button
                type="button"
                className={`entry-icon-button${entry.is_favorite ? ' is-favorite' : ''}`}
                style={
                  entry.is_favorite
                    ? ({
                        '--entry-favorite-color': getMoodScoreColor(entry.score, scores),
                      } as CSSProperties)
                    : undefined
                }
                onClick={() => void handleToggleFavorite()}
                disabled={isTogglingFavorite}
                aria-pressed={entry.is_favorite}
                aria-label={
                  entry.is_favorite ? t('entries.removeFavorite') : t('entries.addFavorite')
                }
                title={
                  entry.is_favorite ? t('entries.removeFavorite') : t('entries.addFavorite')
                }
              >
                <HeartIcon filled={entry.is_favorite} />
              </button>
              <Link
                className="entry-icon-button"
                to={`/entries/${entry.id}/edit`}
                aria-label={t('common.edit')}
                title={t('common.edit')}
              >
                <EditIcon />
              </Link>
              <button
                type="button"
                className="entry-icon-button entry-icon-button-danger"
                onClick={() => setConfirmDelete(true)}
                disabled={isDeleting}
                aria-label={isDeleting ? t('common.deleting') : t('common.delete')}
                title={isDeleting ? t('common.deleting') : t('common.delete')}
              >
                <DeleteIcon />
              </button>
            </div>
          </div>
        </article>
      ) : null}
    </section>
  )
}
