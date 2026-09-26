import { NotificationSettingsForm } from '../components/NotificationSettingsForm'
import { SettingsSection } from '../components/SettingsSection'
import { TelegramLinkForm } from '../components/TelegramLinkForm'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'

export function NotificationSettingsPage() {
  const { t } = useLocale()
  const { user, isTelegram } = useAuth()

  if (!user) {
    return null
  }

  const telegramLead = isTelegram
    ? t('profile.telegramLeadMiniApp')
    : user.telegram_linked
      ? t('profile.telegramLeadConnected')
      : t('profile.telegramLead')

  return (
    <SettingsSection title={t('profile.notificationsTitle')}>
      <div className="settings-stack">
        <section aria-labelledby="settings-telegram-heading">
          <h2 id="settings-telegram-heading" className="profile-settings-subheading">
            {t('profile.telegramTitle')}
          </h2>
          <p className="profile-section-lead">{telegramLead}</p>
          <TelegramLinkForm />
        </section>
        <NotificationSettingsForm timezone={user.timezone} />
      </div>
    </SettingsSection>
  )
}
