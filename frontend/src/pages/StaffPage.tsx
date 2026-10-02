import { Navigate, useSearchParams } from 'react-router-dom'

import { StaffMetricsPanel } from '../components/staff/StaffMetricsPanel'
import { StaffPacksPanel } from '../components/staff/StaffPacksPanel'
import { StaffPresetsPanel } from '../components/staff/StaffPresetsPanel'
import { StaffTokensPanel } from '../components/staff/StaffTokensPanel'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'

type StaffTab = 'tokens' | 'packs' | 'presets' | 'metrics'

const TABS = [
  { id: 'tokens', labelKey: 'staff.tabTokens' },
  { id: 'packs', labelKey: 'staff.tabPacks' },
  { id: 'presets', labelKey: 'staff.tabPresets' },
  { id: 'metrics', labelKey: 'staff.tabMetrics' },
] as const satisfies readonly { id: StaffTab; labelKey: string }[]

function resolveTab(value: string | null): StaffTab {
  return TABS.some((tab) => tab.id === value) ? (value as StaffTab) : 'tokens'
}

export function StaffPage() {
  const { user } = useAuth()
  const { t } = useLocale()
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = resolveTab(searchParams.get('tab'))
  usePageAmbientGlow(['#60a5fa', '#a78bfa'])

  if (!user?.is_staff) {
    return <Navigate to="/profile" replace />
  }

  const setTab = (next: StaffTab) => {
    setSearchParams(next === 'tokens' ? {} : { tab: next }, { replace: true })
  }

  return (
    <section className="page page-staff">
      <header className="page-header">
        <h1>{t('staff.title')}</h1>
      </header>
      <p className="muted settings-lead">{t('staff.lead')}</p>
      <div className="segmented-control staff-tabs" role="tablist" aria-label={t('staff.tabsLabel')}>
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
      {tab === 'tokens' ? (
        <StaffTokensPanel />
      ) : tab === 'packs' ? (
        <StaffPacksPanel />
      ) : tab === 'presets' ? (
        <StaffPresetsPanel />
      ) : (
        <StaffMetricsPanel />
      )}
    </section>
  )
}
