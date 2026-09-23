import { Link, useSearchParams } from 'react-router-dom'

import { MoodEntryForm } from '../components/MoodEntryForm'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { useAuth } from '../context/AuthContext'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import {
  datetimeLocalForDate,
  nowDatetimeLocal,
  todayKey,
} from '../lib/datetime'

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/
const SCORE_RE = /^[1-5]$/
/** Default local time for entries on a past (or non-today) calendar day. */
const DEFAULT_ENTRY_HOUR = 20

export function CreateEntryPage() {
  const { t } = useLocale()
  const { user } = useAuth()
  const { scores } = useMoodPreferences()
  const [searchParams] = useSearchParams()
  const dateParam = searchParams.get('date')
  const scoreParam = searchParams.get('score')
  const timeZone = user?.timezone ?? 'UTC'
  const initialRecordedAtLocal =
    dateParam && DATE_RE.test(dateParam)
      ? dateParam === todayKey(timeZone)
        ? nowDatetimeLocal(timeZone)
        : datetimeLocalForDate(dateParam, DEFAULT_ENTRY_HOUR)
      : undefined
  const initialScore =
    scoreParam && SCORE_RE.test(scoreParam) ? Number(scoreParam) : undefined
  usePageAmbientGlow(Object.values(scores).map((style) => style.color))

  return (
    <section className="page page-entry-create">
      <EmailVerificationBanner />
      <header className="page-header page-header-compact">
        <Link className="button button-secondary button-small web-back-link" to="/">
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
