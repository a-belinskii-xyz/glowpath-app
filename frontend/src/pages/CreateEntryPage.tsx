import { Link, useSearchParams } from 'react-router-dom'

import { MoodEntryForm } from '../components/MoodEntryForm'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { datetimeLocalForDate } from '../lib/datetime'

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/
const SCORE_RE = /^[1-5]$/

export function CreateEntryPage() {
  const { t } = useLocale()
  const { scores } = useMoodPreferences()
  const [searchParams] = useSearchParams()
  const dateParam = searchParams.get('date')
  const scoreParam = searchParams.get('score')
  const initialRecordedAtLocal =
    dateParam && DATE_RE.test(dateParam) ? datetimeLocalForDate(dateParam, 20) : undefined
  const initialScore =
    scoreParam && SCORE_RE.test(scoreParam) ? Number(scoreParam) : undefined
  usePageAmbientGlow(Object.values(scores).map((style) => style.color))

  return (
    <section className="page page-entry-create">
      <EmailVerificationBanner />
      <header className="page-header page-header-compact">
        <Link className="button button-secondary button-small" to="/">
          {t('common.backToEntries')}
        </Link>
        <h1 className="visually-hidden">{t('entries.newMoodEntry')}</h1>
      </header>
      <MoodEntryForm
        mode="create"
        initialRecordedAtLocal={initialRecordedAtLocal}
        initialScore={initialScore}
      />
    </section>
  )
}
