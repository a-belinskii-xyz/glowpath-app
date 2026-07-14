import { Link, useSearchParams } from 'react-router-dom'

import { MoodEntryForm } from '../components/MoodEntryForm'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { datetimeLocalForDate } from '../lib/datetime'

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/

export function CreateEntryPage() {
  const [searchParams] = useSearchParams()
  const dateParam = searchParams.get('date')
  const initialRecordedAtLocal =
    dateParam && DATE_RE.test(dateParam) ? datetimeLocalForDate(dateParam, 20) : undefined

  return (
    <section className="page">
      <EmailVerificationBanner />
      <header className="page-header">
        <h1>New mood entry</h1>
        <Link className="button button-secondary" to="/">
          Back to entries
        </Link>
      </header>
      <MoodEntryForm mode="create" initialRecordedAtLocal={initialRecordedAtLocal} />
    </section>
  )
}
