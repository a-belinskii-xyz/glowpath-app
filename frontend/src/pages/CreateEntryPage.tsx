import { Link, useSearchParams } from 'react-router-dom'

import { MoodEntryForm } from '../components/MoodEntryForm'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { useLocale } from '../context/LocaleContext'
import { datetimeLocalForDate } from '../lib/datetime'

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/

export function CreateEntryPage() {
  const { t } = useLocale()
  const [searchParams] = useSearchParams()
  const dateParam = searchParams.get('date')
  const initialRecordedAtLocal =
    dateParam && DATE_RE.test(dateParam) ? datetimeLocalForDate(dateParam, 20) : undefined

  return (
    <section className="page">
      <EmailVerificationBanner />
      <header className="page-header">
        <h1>{t('entries.newMoodEntry')}</h1>
        <Link className="button button-secondary" to="/">
          {t('common.backToEntries')}
        </Link>
      </header>
      <MoodEntryForm mode="create" initialRecordedAtLocal={initialRecordedAtLocal} />
    </section>
  )
}
