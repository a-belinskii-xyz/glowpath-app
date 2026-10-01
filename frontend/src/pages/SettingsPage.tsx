import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { BellIcon, LockIcon, NavProfileIcon, PaletteIcon, SettingsIcon } from '../components/icons'
import { ShortcutLink } from '../components/ShortcutLink'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { isGuestDiaryMode } from '../lib/guestMode'

export function SettingsPage() {
  const { t } = useLocale()
  const { scores } = useMoodPreferences()
  usePageAmbientGlow(Object.values(scores).map((style) => style.color))
  // Guests only have a local diary: reminders, theme sync and account need a real account.
  const guestShell = isGuestDiaryMode()

  return (
    <section className="page">
      <EmailVerificationBanner />
      <header className="page-header">
        <h1>{t('settings.title')}</h1>
      </header>
      <nav className="profile-shortcuts" aria-label={t('settings.title')}>
        <ShortcutLink
          to="/settings/diary"
          icon={<SettingsIcon />}
          title={t('trackerSettings.title')}
          lead={t('settings.diaryLink')}
        />
        {guestShell ? null : (
          <>
            <ShortcutLink
              to="/settings/notifications"
              icon={<BellIcon />}
              title={t('profile.notificationsTitle')}
              lead={t('profile.notificationsLink')}
            />
            <ShortcutLink
              to="/settings/appearance"
              icon={<PaletteIcon />}
              title={t('profile.appearanceTitle')}
              lead={t('profile.appearanceLink')}
            />
            <ShortcutLink
              to="/settings/account"
              icon={<NavProfileIcon />}
              title={t('settings.accountTitle')}
              lead={t('settings.accountLink')}
            />
          </>
        )}
        <ShortcutLink
          to="/privacy"
          icon={<LockIcon />}
          title={t('settings.privacyTitle')}
          lead={t('settings.privacyLink')}
        />
      </nav>
    </section>
  )
}
