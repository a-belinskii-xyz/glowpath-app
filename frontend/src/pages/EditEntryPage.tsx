import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getMoodEntry } from '../api/moodEntries'
import { Alert } from '../components/Alert'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { MoodEntryForm } from '../components/MoodEntryForm'
import { ApiError } from '../lib/errors'
import type { MoodEntryPublic } from '../types/mood'

export function EditEntryPage() {
  const { id } = useParams<{ id: string }>()
  const [entry, setEntry] = useState<MoodEntryPublic | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

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
          setError('Verify your email before editing mood entries.')
        } else {
          setError(err instanceof Error ? err.message : 'Failed to load entry')
        }
      } finally {
        setIsLoading(false)
      }
    }

    void load()
  }, [id])

  return (
    <section className="page">
      <EmailVerificationBanner />
      <header className="page-header">
        <h1>Edit mood entry</h1>
        <Link className="button button-secondary" to="/">
          Back to entries
        </Link>
      </header>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {isLoading ? <p className="muted">Loading entry…</p> : null}
      {entry ? <MoodEntryForm mode="edit" initialEntry={entry} /> : null}
    </section>
  )
}
