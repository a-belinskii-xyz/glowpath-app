import { GuestLockedPreview, GuestRegistrationCallout } from './GuestRegistrationLock'
import { BellIcon, ChevronRightIcon, PaletteIcon, SettingsIcon, TrophyIcon } from './icons'
import { useLocale } from '../context/LocaleContext'
import { LOCALE_OPTIONS } from '../lib/locale'
import { timezoneSelectOptions } from '../lib/timezones'

type GuestFeatureKey = 'gallery' | 'market' | 'achievements' | 'profile'

export function guestFeatureMessage(t: (key: string) => string, feature: GuestFeatureKey): string {
  return t(`guest.locked.${feature}.body`)
}

export function GuestProfilePreview() {
  const { t, locale } = useLocale()
  const timezoneOptions = timezoneSelectOptions(locale)

  return (
    <GuestLockedPreview message={guestFeatureMessage(t, 'profile')}>
      <div className="card profile-account">
        <div className="profile-account-row">
          <div className="profile-account-email">
            <span className="profile-account-label">{t('common.email')}</span>
            <div className="profile-account-email-value">
              <span className="profile-account-email-text">user@example.com</span>
              <span className="status-pill status-pill--warn">{t('profile.emailUnverifiedShort')}</span>
            </div>
          </div>
        </div>
        <div className="profile-account-grid">
          <div>
            <label className="profile-account-label" htmlFor="guest-profile-timezone">
              {t('common.timezone')}
            </label>
            <select id="guest-profile-timezone" className="form-input profile-locale-select" defaultValue={timezoneOptions[0]} disabled>
              {timezoneOptions.slice(0, 8).map((zone) => (
                <option key={zone} value={zone}>
                  {zone}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="profile-account-label" htmlFor="guest-profile-locale">
              {t('common.language')}
            </label>
            <select id="guest-profile-locale" className="form-input profile-locale-select" defaultValue={locale} disabled>
              {LOCALE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
      <div className="profile-shortcuts">
        <div className="profile-shortcut" aria-hidden="true">
          <span className="profile-shortcut-icon" aria-hidden="true">
            <TrophyIcon />
          </span>
          <span className="profile-shortcut-copy">
            <span className="profile-shortcut-title">{t('nav.achievements')}</span>
            <span className="profile-shortcut-lead">{t('profile.achievementsLink')}</span>
          </span>
          <ChevronRightIcon className="profile-shortcut-chevron" />
        </div>
        <div className="profile-shortcut">
          <span className="profile-shortcut-icon" aria-hidden="true">
            <SettingsIcon />
          </span>
          <span className="profile-shortcut-copy">
            <span className="profile-shortcut-title">{t('nav.trackerSettings')}</span>
            <span className="profile-shortcut-lead">{t('profile.trackerSettingsLink')}</span>
          </span>
          <ChevronRightIcon className="profile-shortcut-chevron" />
        </div>
        <div className="profile-shortcut">
          <span className="profile-shortcut-icon" aria-hidden="true">
            <BellIcon />
          </span>
          <span className="profile-shortcut-copy">
            <span className="profile-shortcut-title">{t('profile.notificationsTitle')}</span>
            <span className="profile-shortcut-lead">{t('profile.notificationsLink')}</span>
          </span>
          <ChevronRightIcon className="profile-shortcut-chevron" />
        </div>
        <div className="profile-shortcut">
          <span className="profile-shortcut-icon" aria-hidden="true">
            <PaletteIcon />
          </span>
          <span className="profile-shortcut-copy">
            <span className="profile-shortcut-title">{t('profile.appearanceTitle')}</span>
            <span className="profile-shortcut-lead">{t('profile.appearanceLink')}</span>
          </span>
          <ChevronRightIcon className="profile-shortcut-chevron" />
        </div>
      </div>
    </GuestLockedPreview>
  )
}

export function GuestMarketPreview() {
  const { t } = useLocale()

  return (
    <GuestLockedPreview message={guestFeatureMessage(t, 'market')}>
      <header className="page-header page-header-compact market-header">
        <div className="market-header-copy">
          <h1>{t('market.title')}</h1>
          <p className="market-lead">{t('market.lead')}</p>
        </div>
        <div className="market-balance">
          <span className="market-balance-label">{t('market.balance')}</span>
          <strong className="market-balance-value">
            0<span className="market-balance-unit">{t('profile.walletTokens')}</span>
          </strong>
        </div>
      </header>
      <label className="market-search">
        <span className="visually-hidden">{t('market.search')}</span>
        <input
          className="form-input"
          type="search"
          disabled
          placeholder={t('market.searchPlaceholder')}
        />
      </label>
      <div className="market-tag-chips">
        <span className="market-tag-chip is-active">{t('market.allTags')}</span>
        <span className="market-tag-chip">{t('market.filterTags')}</span>
      </div>
      <p className="market-empty">{t('market.empty')}</p>
    </GuestLockedPreview>
  )
}

export function GuestAchievementsPreview() {
  const { t } = useLocale()

  return (
    <GuestLockedPreview message={guestFeatureMessage(t, 'achievements')}>
      <div className="achievements-layout">
        <aside className="achievements-aside">
          <div className="achievements-stat">
            <span className="achievements-stat-copy">
              <span className="achievements-stat-label">{t('achievements.statUnlocked')}</span>
              <span className="achievements-stat-value">0/0</span>
            </span>
          </div>
        </aside>
        <div className="achievements-main">
          <div className="segmented-control">
            <span className="segmented-control-option is-active">{t('achievements.filterAll')}</span>
            <span className="segmented-control-option">{t('achievements.filterInProgress')}</span>
            <span className="segmented-control-option">{t('achievements.filterUnlocked')}</span>
          </div>
          <p className="muted">{t('achievements.empty')}</p>
        </div>
      </div>
    </GuestLockedPreview>
  )
}

export function GuestGalleryCallout() {
  const { t } = useLocale()
  return <GuestRegistrationCallout message={guestFeatureMessage(t, 'gallery')} />
}
