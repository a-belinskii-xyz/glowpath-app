import { Navigate, useSearchParams } from 'react-router-dom'

import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { MoodPreferencesForm } from '../components/MoodPreferencesForm'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { TemplatesPage } from './TemplatesPage'

type TrackerTab = 'moods' | 'templates'

function resolveTab(value: string | null): TrackerTab {
  return value === 'templates' ? 'templates' : 'moods'
}

export function TrackerSettingsPage() {
  const { t } = useLocale()
  const { scores } = useMoodPreferences()
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = resolveTab(searchParams.get('tab'))
  usePageAmbientGlow(Object.values(scores).map((style) => style.color))

  const setTab = (next: TrackerTab) => {
    setSearchParams(next === 'moods' ? {} : { tab: next }, { replace: true })
  }

  return (
    <section className="page">
      <EmailVerificationBanner />
      <header className="page-header">
        <h1>{t('trackerSettings.title')}</h1>
      </header>
      <p className="muted">{t('trackerSettings.lead')}</p>

      <div
        className="segmented-control tracker-settings-tabs"
        role="tablist"
        aria-label={t('trackerSettings.tabsLabel')}
      >
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'moods'}
          className={`segmented-control-option${tab === 'moods' ? ' is-active' : ''}`}
          onClick={() => setTab('moods')}
        >
          {t('trackerSettings.tabMoods')}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'templates'}
          className={`segmented-control-option${tab === 'templates' ? ' is-active' : ''}`}
          onClick={() => setTab('templates')}
        >
          {t('trackerSettings.tabTemplates')}
        </button>
      </div>

      {tab === 'moods' ? (
        <section aria-labelledby="tracker-moods-heading">
          <h2 id="tracker-moods-heading" className="visually-hidden">
            {t('trackerSettings.tabMoods')}
          </h2>
          <p className="profile-section-lead">{t('profile.moodPreferencesLead')}</p>
          <MoodPreferencesForm />
        </section>
      ) : (
        <TemplatesPage embedded />
      )}
    </section>
  )
}

export function TemplatesRedirect() {
  return <Navigate to="/tracker-settings?tab=templates" replace />
}
