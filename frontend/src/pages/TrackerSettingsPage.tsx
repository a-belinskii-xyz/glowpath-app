import { memo, useState } from 'react'
import { Navigate, useSearchParams } from 'react-router-dom'

import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { EntryComposerSettingsForm } from '../components/EntryComposerSettingsForm'
import { MoodPreferencesForm } from '../components/MoodPreferencesForm'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { TemplatesPage } from './TemplatesPage'

type TrackerTab = 'moods' | 'templates' | 'layout'

function resolveTab(value: string | null): TrackerTab {
  if (value === 'templates') {
    return 'templates'
  }
  if (value === 'layout') {
    return 'layout'
  }
  return 'moods'
}

function TrackerSettingsPanels({
  tab,
  onTabChange,
}: {
  tab: TrackerTab
  onTabChange: (tab: TrackerTab) => void
}) {
  const { t } = useLocale()

  return (
    <>
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
          onClick={() => onTabChange('moods')}
        >
          {t('trackerSettings.tabMoods')}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'layout'}
          className={`segmented-control-option${tab === 'layout' ? ' is-active' : ''}`}
          onClick={() => onTabChange('layout')}
        >
          {t('trackerSettings.tabLayout')}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'templates'}
          className={`segmented-control-option${tab === 'templates' ? ' is-active' : ''}`}
          onClick={() => onTabChange('templates')}
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
      ) : tab === 'layout' ? (
        <section aria-labelledby="tracker-layout-heading">
          <h2 id="tracker-layout-heading" className="visually-hidden">
            {t('trackerSettings.tabLayout')}
          </h2>
          <EntryComposerSettingsForm />
        </section>
      ) : (
        <TemplatesPage embedded />
      )}
    </>
  )
}

const TrackerSettingsLocalContent = memo(function TrackerSettingsLocalContent() {
  const [tab, setTab] = useState<TrackerTab>('moods')
  return <TrackerSettingsPanels tab={tab} onTabChange={setTab} />
})

function TrackerSettingsUrlContent() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = resolveTab(searchParams.get('tab'))

  const setTab = (next: TrackerTab) => {
    if (next === 'moods') {
      setSearchParams({}, { replace: true })
      return
    }
    setSearchParams({ tab: next }, { replace: true })
  }

  return <TrackerSettingsPanels tab={tab} onTabChange={setTab} />
}

export function TrackerSettingsContent({ syncUrl = false }: { syncUrl?: boolean }) {
  return syncUrl ? <TrackerSettingsUrlContent /> : <TrackerSettingsLocalContent />
}

export function TrackerSettingsPage() {
  const { t } = useLocale()
  const { scores } = useMoodPreferences()
  usePageAmbientGlow(Object.values(scores).map((style) => style.color))

  return (
    <section className="page">
      <EmailVerificationBanner />
      <header className="page-header">
        <h1>{t('trackerSettings.title')}</h1>
      </header>
      <p className="muted">{t('trackerSettings.lead')}</p>
      <TrackerSettingsContent syncUrl />
    </section>
  )
}

export function TemplatesRedirect() {
  return <Navigate to="/tracker-settings?tab=templates" replace />
}
