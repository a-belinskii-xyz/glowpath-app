import { useEffect, useState, type CSSProperties } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { deleteMoodEntry, getMoodEntry, getMoodInsights, patchMoodEntry } from '../api/moodEntries'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { AttachmentAudio } from '../components/AttachmentAudio'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { EntryAttachmentThumbs } from '../components/EntryAttachmentThumbs'
import { GoalIcon } from '../components/GoalIcon'
import { HeartIcon } from '../components/HeartIcon'
import { IconButton, IconLinkButton } from '../components/IconButton'
import { DeleteIcon, EditIcon } from '../components/icons'
import { MarkdownNote } from '../components/MarkdownNote'
import { MoodScoreIcon } from '../components/MoodScoreIcon'
import { PatternInsights } from '../components/PatternInsights'
import { TagIcon } from '../components/TagIcon'
import { useAuth } from '../context/AuthContext'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { moodGlowFilter, moodSubtleFill } from '../design'
import { intlLocale } from '../i18n/t'
import { ApiError, formatApiError } from '../lib/errors'
import { formatDayHeading, formatTime, entriesListPathForInstant } from '../lib/datetime'
import { entryMoodColor, entryMoodStyle } from '../lib/moodScale'
import type { MoodEntryPublic, MoodInsightsResponse } from '../types/mood'

function isSameInstant(left: string, right: string, slackMs = 60_000) {
  return Math.abs(new Date(left).getTime() - new Date(right).getTime()) < slackMs
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
  const [insights, setInsights] = useState<MoodInsightsResponse | null>(null)
  const [isInsightsLoading, setIsInsightsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [isTogglingFavorite, setIsTogglingFavorite] = useState(false)

  const ambientColors = entry
    ? [
        entryMoodColor(entry, scores),
        ...entry.tags.map((tag) => tag.color),
        ...entry.goals.map((goal) => goal.color),
      ]
    : Object.values(scores).map((style) => style.color)
  usePageAmbientGlow(ambientColors)

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
          setError(formatApiError(err, t, 'errors.failedLoadEntry'))
        }
      } finally {
        setIsLoading(false)
      }
    }

    void load()
  }, [id, locale, t])

  useEffect(() => {
    if (!id || !user?.email_verified) {
      setInsights(null)
      return
    }
    let cancelled = false
    setIsInsightsLoading(true)
    void getMoodInsights({ limit: 1, focus_entry_id: id })
      .then((response) => {
        if (!cancelled) {
          setInsights(response)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setInsights(null)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsInsightsLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [id, locale, user?.email_verified])

  const handleDelete = async () => {
    if (!entry) {
      return
    }
    setIsDeleting(true)
    setError(null)
    try {
      await deleteMoodEntry(entry.id)
      setConfirmDelete(false)
      navigate(entriesListPathForInstant(entry.recorded_at, timeZone))
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedDeleteEntry'))
    } finally {
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
      setError(formatApiError(err, t, 'errors.failedSaveEntry'))
    } finally {
      setIsTogglingFavorite(false)
    }
  }

  const audioAttachment = entry?.attachments.find((attachment) => attachment.kind === 'audio')
  const backToEntries = entry
    ? entriesListPathForInstant(entry.recorded_at, timeZone, entry.id)
    : '/'
  const showCreated = Boolean(entry && !isSameInstant(entry.created_at, entry.recorded_at))
  const showUpdated = Boolean(
    entry &&
      entry.updated_at !== entry.created_at &&
      !isSameInstant(entry.updated_at, entry.recorded_at),
  )

  return (
    <section className="page page-entry-detail">
      <EmailVerificationBanner />
      <header className="page-header">
        <h1>{t('entries.moodEntry')}</h1>
        <div className="page-header-actions">
          {entry ? (
            <div
              className="entry-detail-header-actions"
              role="toolbar"
              aria-label={t('entryActions.ariaLabel')}
            >
              <IconButton
                label={
                  entry.is_favorite ? t('entries.removeFavorite') : t('entries.addFavorite')
                }
                className={entry.is_favorite ? 'is-favorite' : undefined}
                style={
                  entry.is_favorite
                    ? ({
                        '--entry-favorite-color': entryMoodColor(entry, scores),
                      } as CSSProperties)
                    : undefined
                }
                onClick={() => void handleToggleFavorite()}
                disabled={isTogglingFavorite}
                aria-pressed={entry.is_favorite}
              >
                <HeartIcon filled={entry.is_favorite} />
              </IconButton>
              <IconLinkButton
                label={t('common.edit')}
                to={`/entries/${entry.id}/edit`}
              >
                <EditIcon />
              </IconLinkButton>
              <IconButton
                label={isDeleting ? t('common.deleting') : t('common.delete')}
                variant="danger"
                disabled={isDeleting}
                onClick={() => setConfirmDelete(true)}
              >
                <DeleteIcon />
              </IconButton>
            </div>
          ) : null}
          <Link className="button button-secondary" to={backToEntries}>
            {t('common.backToEntries')}
          </Link>
        </div>
      </header>

      <PageErrorAlert error={confirmDelete ? null : error} />
      {confirmDelete && entry ? (
        <ConfirmDialog
          open
          title={t('confirm.deleteEntryTitle')}
          message={t('confirm.deleteEntry')}
          confirmLabel={t('common.delete')}
          isBusy={isDeleting}
          error={error}
          onCancel={() => {
            if (isDeleting) return
            setConfirmDelete(false)
            setError(null)
          }}
          onConfirm={() => void handleDelete()}
        />
      ) : null}
      {isLoading ? <p className="muted">{t('common.loadingEntry')}</p> : null}

      {entry ? (
        <article className="entry-detail">
          <div className="entry-detail-main">
            <div className="entry-detail-block entry-detail-hero">
              <span
                style={{
                  filter: moodGlowFilter(entryMoodColor(entry, scores)),
                }}
              >
                <MoodScoreIcon
                  style={entryMoodStyle(entry, scores)}
                  className="entry-detail-emoji"
                  fallbackScore={entry.score}
                />
              </span>
              <p className="entry-detail-heading">
                <span className="entry-detail-score">{entry.score_label}</span>
                <span className="muted entry-detail-recorded">
                  {' '}
                  — {formatDayHeading(entry.recorded_at, timeZone, dateLocale)} ·{' '}
                  {formatTime(entry.recorded_at, timeZone, dateLocale)}
                </span>
              </p>
            </div>

            {entry.note || audioAttachment || entry.attachments.some((a) => a.kind === 'photo') ? (
              <div className="entry-detail-block entry-detail-body">
                {entry.note ? (
                  <MarkdownNote content={entry.note} className="entry-detail-note" />
                ) : null}

                <EntryAttachmentThumbs
                  entryId={entry.id}
                  attachments={entry.attachments}
                  showAudioCount={false}
                  variant="collage"
                />

                {audioAttachment ? (
                  <AttachmentAudio
                    entryId={entry.id}
                    attachment={audioAttachment}
                    accentColor={entryMoodColor(entry, scores)}
                  />
                ) : null}
              </div>
            ) : null}

            <div className="entry-detail-block entry-detail-footer">
              {entry.tags.length > 0 ? (
                <div className="entry-tags">
                  {entry.tags.map((tag) => (
                    <span
                      key={tag.id}
                      className="entry-tag"
                      style={{
                        background: moodSubtleFill(tag.color),
                        color: tag.color,
                      }}
                    >
                      <TagIcon
                        style={{
                          color: tag.color,
                          icon_type: tag.icon_type,
                          icon: tag.icon,
                        }}
                        className="entry-tag-icon"
                      />
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

              {showCreated || showUpdated ? (
                <p className="muted entry-detail-meta">
                  {showCreated
                    ? t('entries.createdAt', {
                        date: `${formatDayHeading(entry.created_at, timeZone, dateLocale)} ${formatTime(entry.created_at, timeZone, dateLocale)}`,
                      })
                    : null}
                  {showCreated && showUpdated ? ' · ' : null}
                  {showUpdated
                    ? t('entries.updatedAt', {
                        date: `${formatDayHeading(entry.updated_at, timeZone, dateLocale)} ${formatTime(entry.updated_at, timeZone, dateLocale)}`,
                      })
                    : null}
                </p>
              ) : null}
            </div>
          </div>
        </article>
      ) : null}

      {entry && user?.email_verified ? (
        <PatternInsights insights={insights} isLoading={isInsightsLoading} compact />
      ) : null}
    </section>
  )
}
