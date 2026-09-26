import { Navigate, useLocation, useSearchParams } from 'react-router-dom'

import { EntryComposerSettingsForm } from '../components/EntryComposerSettingsForm'
import { MoodPreferencesForm } from '../components/MoodPreferencesForm'
import { SettingsSection } from '../components/SettingsSection'
import { useLocale } from '../context/LocaleContext'
import { TagsPage } from './TagsPage'
import { TemplatesPage } from './TemplatesPage'

type DiaryTab = 'moods' | 'tags' | 'templates' | 'layout'

const TABS = [
  { id: 'moods', labelKey: 'trackerSettings.tabMoods' },
  { id: 'tags', labelKey: 'trackerSettings.tabTags' },
  { id: 'templates', labelKey: 'trackerSettings.tabTemplates' },
  { id: 'layout', labelKey: 'trackerSettings.tabLayout' },
] as const satisfies readonly { id: DiaryTab; labelKey: string }[]

function resolveTab(value: string | null): DiaryTab {
  return TABS.some((tab) => tab.id === value) ? (value as DiaryTab) : 'moods'
}

export function DiarySettingsPage() {
  const { t } = useLocale()
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = resolveTab(searchParams.get('tab'))

  const setTab = (next: DiaryTab) => {
    setSearchParams(next === 'moods' ? {} : { tab: next }, { replace: true })
  }

  return (
    <SettingsSection title={t('trackerSettings.title')} lead={t('trackerSettings.lead')}>
      <div
        className="segmented-control tracker-settings-tabs"
        role="tablist"
        aria-label={t('trackerSettings.tabsLabel')}
      >
        {TABS.map(({ id, labelKey }) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            className={`segmented-control-option${tab === id ? ' is-active' : ''}`}
            onClick={() => setTab(id)}
          >
            {t(labelKey)}
          </button>
        ))}
      </div>

      {tab === 'moods' ? (
        <section aria-labelledby="tracker-moods-heading">
          <h2 id="tracker-moods-heading" className="visually-hidden">
            {t('trackerSettings.tabMoods')}
          </h2>
          <p className="profile-section-lead">{t('profile.moodPreferencesLead')}</p>
          <MoodPreferencesForm />
        </section>
      ) : tab === 'tags' ? (
        <TagsPage />
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
    </SettingsSection>
  )
}

function DiaryTabRedirect({ tab }: { tab?: DiaryTab }) {
  const location = useLocation()
  const search = tab ? `?tab=${tab}` : location.search
  return <Navigate to={`/settings/diary${search}`} replace />
}

/** Legacy `/tracker-settings?tab=…` links (bookmarks, older bot messages). */
export function TrackerSettingsRedirect() {
  return <DiaryTabRedirect />
}

export function TemplatesRedirect() {
  return <DiaryTabRedirect tab="templates" />
}

export function TagsRedirect() {
  return <DiaryTabRedirect tab="tags" />
}
