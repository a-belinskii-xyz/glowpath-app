import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { EmailVerificationBanner } from './EmailVerificationBanner'
import { ChevronLeftIcon } from './icons'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'

/** Shared chrome for a single settings category: back link, title, lead. */
export function SettingsSection({
  title,
  lead,
  children,
}: {
  title: string
  lead?: string
  children: ReactNode
}) {
  const { t } = useLocale()
  const { scores } = useMoodPreferences()
  usePageAmbientGlow(Object.values(scores).map((style) => style.color))

  return (
    <section className="page">
      <EmailVerificationBanner />
      <Link to="/settings" className="settings-back-link">
        <ChevronLeftIcon aria-hidden="true" />
        {t('settings.title')}
      </Link>
      <header className="page-header">
        <h1>{title}</h1>
      </header>
      {lead ? <p className="muted settings-lead">{lead}</p> : null}
      {children}
    </section>
  )
}
