import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getMoodEntry } from '../api/moodEntries'
import { Alert } from '../components/Alert'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { MoodEntryForm } from '../components/MoodEntryForm'
import { useLocale } from '../context/LocaleContext'
import { ApiError } from '../lib/errors'
import type { MoodEntryPublic } from '../types/mood'

export function EditEntryPage() {
  const { id } = useParams<{ id: string }>()
  const { locale, t } = useLocale()
  const [entry, setEntry] = useState<MoodEntryPublic | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

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
          setError(err instanceof Error ? err.message : t('errors.failedLoadEntry'))
        }
      } finally {
        setIsLoading(false)
      }
    }

    void load()
  }, [id, locale, t])

  return (
    <section className="page">
      <EmailVerificationBanner />
      <header className="page-header">
        <h1>{t('entries.editMoodEntry')}</h1>
        <Link className="button button-secondary" to="/">
          {t('common.backToEntries')}
        </Link>
      </header>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {isLoading ? <p className="muted">{t('common.loadingEntry')}</p> : null}
      {entry ? <MoodEntryForm mode="edit" initialEntry={entry} /> : null}
    </section>
  )
}
