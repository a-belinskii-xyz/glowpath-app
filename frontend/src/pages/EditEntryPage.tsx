import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getMoodEntry } from '../api/moodEntries'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { MoodEntryForm } from '../components/MoodEntryForm'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { ApiError, formatApiError } from '../lib/errors'
import { entriesListPathForInstant } from '../lib/datetime'
import { getMoodScoreColor } from '../lib/moodScale'
import type { MoodEntryPublic } from '../types/mood'

export function EditEntryPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const { locale, t } = useLocale()
  const { scores } = useMoodPreferences()
  const timeZone = user?.timezone ?? 'UTC'
  const [entry, setEntry] = useState<MoodEntryPublic | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  usePageAmbientGlow(
    entry
      ? [
          getMoodScoreColor(entry.score, scores),
          ...entry.tags.map((tag) => tag.color),
          ...entry.goals.map((goal) => goal.color),
        ]
      : Object.values(scores).map((style) => style.color),
  )

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
          setError(t('errors.verifyToEditEntries'))
        } else {
          setError(formatApiError(err, t, 'errors.failedLoadEntry'))
        }
      } finally {
        setIsLoading(false)
      }
    }

    void load()
  }, [id, locale, t])

  const backToEntries = entry
    ? entriesListPathForInstant(entry.recorded_at, timeZone, entry.id)
    : '/'

  return (
    <section className="page page-entry-create">
      <EmailVerificationBanner />
      <header className="page-header page-header-compact">
        <Link className="button button-secondary button-small" to={backToEntries}>
          {t('common.backToEntries')}
        </Link>
        <h1 className="visually-hidden">{t('entries.editMoodEntry')}</h1>
      </header>

      <PageErrorAlert error={error} />
      {isLoading ? <p className="muted">{t('common.loadingEntry')}</p> : null}
      {entry ? <MoodEntryForm mode="edit" initialEntry={entry} /> : null}
    </section>
  )
}
