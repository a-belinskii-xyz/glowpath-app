import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { NotificationSettingsForm } from '../components/NotificationSettingsForm'
import { TelegramLinkForm } from '../components/TelegramLinkForm'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { LOCALE_OPTIONS, type ApiLocale } from '../lib/locale'

export function ProfilePage() {
  const { user, refreshUser } = useAuth()
  const { locale, setLocale, t } = useLocale()
  const { scores } = useMoodPreferences()
  usePageAmbientGlow(Object.values(scores).map((style) => style.color))

  if (!user) {
    return null
  }

  return (
    <section className="page">
      <EmailVerificationBanner />
      <div className="page-header">
        <h1>{t('profile.title')}</h1>
        <button type="button" className="button button-secondary" onClick={() => void refreshUser()}>
          {t('common.refresh')}
        </button>
      </div>

      <div className="card profile-account">
        <div className="profile-account-row">
          <div className="profile-account-email">
            <span className="profile-account-label">{t('common.email')}</span>
            <div className="profile-account-email-value">
              <span className="profile-account-email-text">{user.email}</span>
              <span
                className={`status-pill${user.email_verified ? ' status-pill--ok' : ' status-pill--warn'}`}
              >
                {user.email_verified
                  ? t('profile.emailVerifiedShort')
                  : t('profile.emailUnverifiedShort')}
              </span>
            </div>
          </div>
        </div>

        <div className="profile-account-grid">
          <div>
            <span className="profile-account-label">{t('common.timezone')}</span>
            <p className="profile-account-value--static">{user.timezone}</p>
          </div>
          <div>
            <label className="profile-account-label" htmlFor="profile-locale">
              {t('common.language')}
            </label>
            <select
              id="profile-locale"
              className="form-input profile-locale-select"
              value={locale}
              onChange={(event) => setLocale(event.target.value as ApiLocale)}
            >
              {LOCALE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <section className="profile-section" aria-labelledby="profile-telegram-heading">
        <h2 id="profile-telegram-heading">{t('profile.telegramTitle')}</h2>
        <p className="profile-section-lead">{t('profile.telegramLead')}</p>
        <TelegramLinkForm />
      </section>

      <section className="profile-section" aria-labelledby="profile-notifications-heading">
        <h2 id="profile-notifications-heading">{t('profile.notificationsTitle')}</h2>
        <p className="profile-section-lead">{t('profile.notificationsLead')}</p>
        <NotificationSettingsForm timezone={user.timezone} />
      </section>
    </section>
  )
}
