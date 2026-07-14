import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { deleteMoodEntry, getMoodEntry } from '../api/moodEntries'
import { Alert } from '../components/Alert'
import { AttachmentAudio } from '../components/AttachmentAudio'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { EntryAttachmentThumbs } from '../components/EntryAttachmentThumbs'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../lib/errors'
import { formatDayHeading, formatTime } from '../lib/datetime'
import type { MoodEntryPublic } from '../types/mood'

export function EntryDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const timeZone = user?.timezone ?? 'UTC'

  const [entry, setEntry] = useState<MoodEntryPublic | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    if (!id) {
      setError('Entry id is missing')
      setIsLoading(false)
      return
    }

    const load = async () => {
      try {
        const loaded = await getMoodEntry(id)
        setEntry(loaded)
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError('Verify your email before viewing mood entries.')
        } else {
          setError(err instanceof Error ? err.message : 'Failed to load entry')
        }
      } finally {
        setIsLoading(false)
      }
    }

    void load()
  }, [id])

  const handleDelete = async () => {
    if (!entry || !window.confirm('Delete this mood entry?')) {
      return
    }
    setIsDeleting(true)
    setError(null)
    try {
      await deleteMoodEntry(entry.id)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete entry')
      setIsDeleting(false)
    }
  }

  const audioAttachment = entry?.attachments.find((attachment) => attachment.kind === 'audio')

  return (
    <section className="page">
      <EmailVerificationBanner />
      <header className="page-header">
        <h1>Mood entry</h1>
        <Link className="button button-secondary" to="/">
          Back to entries
        </Link>
      </header>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {isLoading ? <p className="muted">Loading entry…</p> : null}

      {entry ? (
        <article className="entry-detail">
          <div className="entry-detail-hero">
            <span className="entry-detail-emoji" aria-hidden="true">
              {entry.score_emoji}
            </span>
            <div>
              <p className="entry-detail-score">{entry.score_label}</p>
              <p className="muted">
                {formatDayHeading(entry.recorded_at, timeZone)} · {formatTime(entry.recorded_at, timeZone)}
              </p>
            </div>
          </div>

          {entry.note ? <p className="entry-detail-note">{entry.note}</p> : null}

          {entry.tags.length > 0 ? (
            <div className="entry-tags">
              {entry.tags.map((tag) => (
                <span key={tag.id} className="entry-tag">
                  {tag.label}
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
            <Link className="button" to={`/entries/${entry.id}/edit`}>
              Edit
            </Link>
            <button
              type="button"
              className="button button-danger"
              onClick={() => void handleDelete()}
              disabled={isDeleting}
            >
              {isDeleting ? 'Deleting…' : 'Delete'}
            </button>
          </div>
        </article>
      ) : null}
    </section>
  )
}
