import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { MoodPreferencesForm } from '../components/MoodPreferencesForm'
import { NotificationSettingsForm } from '../components/NotificationSettingsForm'
import { TelegramLinkForm } from '../components/TelegramLinkForm'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { intlLocale } from '../i18n/t'
import { LOCALE_OPTIONS, type ApiLocale } from '../lib/locale'

function formatDate(value: string | null, locale: string, emptyLabel: string): string {
  if (!value) {
    return emptyLabel
  }
  return new Date(value).toLocaleString(locale)
}

export function ProfilePage() {
  const { user, refreshUser } = useAuth()
  const { locale, setLocale, t } = useLocale()

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

      <dl className="profile-list">
        <div>
          <dt>{t('common.email')}</dt>
          <dd>{user.email}</dd>
        </div>
        <div>
          <dt>{t('profile.userId')}</dt>
          <dd>
            <code>{user.id}</code>
          </dd>
        </div>
        <div>
          <dt>{t('common.timezone')}</dt>
          <dd>{user.timezone}</dd>
        </div>
        <div>
          <dt>
            <label htmlFor="profile-locale">{t('common.language')}</label>
          </dt>
          <dd>
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
          </dd>
        </div>
        <div>
          <dt>{t('profile.emailVerified')}</dt>
          <dd>{user.email_verified ? t('common.yes') : t('common.no')}</dd>
        </div>
        <div>
          <dt>{t('profile.verifiedAt')}</dt>
          <dd>{formatDate(user.email_verified_at, intlLocale(locale), t('common.emptyDate'))}</dd>
        </div>
      </dl>

      <section className="profile-section" aria-labelledby="profile-mood-preferences-heading">
        <h2 id="profile-mood-preferences-heading">{t('profile.moodPreferencesTitle')}</h2>
        <p className="profile-section-lead">{t('profile.moodPreferencesLead')}</p>
        <MoodPreferencesForm />
      </section>

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
