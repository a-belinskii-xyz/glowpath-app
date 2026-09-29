import { useEffect, useState } from 'react'

import { getAchievementsSummary } from '../api/achievements'
import { getWallet } from '../api/wallet'
import { GuestProfilePreview } from '../components/GuestAccountPreviews'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { LockIcon, NavMarketIcon, SettingsIcon, SparkleIcon, TrophyIcon } from '../components/icons'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { ShortcutLink } from '../components/ShortcutLink'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { formatApiError } from '../lib/errors'
import { isGuestDiaryMode } from '../lib/guestMode'

export function ProfilePage() {
  const { user, logout, isTelegram } = useAuth()
  const { locale, t } = useLocale()
  const { scores } = useMoodPreferences()
  usePageAmbientGlow(Object.values(scores).map((style) => style.color))
  const [walletBalance, setWalletBalance] = useState<number | null>(null)
  const [walletError, setWalletError] = useState<string | null>(null)
  const [isLoadingWallet, setIsLoadingWallet] = useState(false)

  const marketplaceEnabled = Boolean(user?.features?.icon_marketplace)
  const achievementsEnabled = Boolean(user?.features?.achievements)
  const walletEnabled = marketplaceEnabled || achievementsEnabled
  const [achievementSummary, setAchievementSummary] = useState<{
    unlocked: number
    total_visible: number
  } | null>(null)

  useEffect(() => {
    if (!user || !walletEnabled) {
      setWalletBalance(null)
      setWalletError(null)
      return
    }

    let cancelled = false
    setIsLoadingWallet(true)
    setWalletError(null)
    void getWallet()
      .then((wallet) => {
        if (!cancelled) {
          setWalletBalance(wallet.balance)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setWalletBalance(null)
          setWalletError(formatApiError(err, t, 'errors.requestFailed'))
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingWallet(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [user, walletEnabled, t])

  useEffect(() => {
    if (!user || !achievementsEnabled) {
      setAchievementSummary(null)
      return
    }
    let cancelled = false
    void getAchievementsSummary()
      .then((summary) => {
        if (!cancelled) {
          setAchievementSummary({
            unlocked: summary.unlocked,
            total_visible: summary.total_visible,
          })
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAchievementSummary(null)
        }
      })
    return () => {
      cancelled = true
    }
  }, [user, achievementsEnabled])

  const settingsLink = (
    <ShortcutLink
      to="/settings"
      icon={<SettingsIcon />}
      title={t('settings.title')}
      lead={isGuestDiaryMode() ? t('settings.diaryLink') : t('settings.hubLink')}
    />
  )

  if (isGuestDiaryMode()) {
    return (
      <section className="page page-profile">
        <header className="page-header">
          <h1>{t('profile.title')}</h1>
        </header>
        <GuestProfilePreview />
        <nav className="profile-shortcuts profile-hub-links" aria-label={t('profile.title')}>
          <ShortcutLink
            to="/achievements"
            icon={<TrophyIcon />}
            title={t('nav.achievements')}
            lead={t('profile.achievementsLink')}
          />
          <ShortcutLink
            to="/market"
            icon={<NavMarketIcon />}
            title={t('nav.market')}
            lead={t('market.lead')}
          />
          {settingsLink}
        </nav>
      </section>
    )
  }

  if (!user) {
    return null
  }

  const balanceLabel =
    walletBalance === null
      ? '—'
      : new Intl.NumberFormat(locale === 'ru' ? 'ru-RU' : 'en-US').format(walletBalance)

  return (
    <section className="page page-profile">
      <EmailVerificationBanner />
      <header className="page-header">
        <h1>{t('profile.title')}</h1>
      </header>

      <PageErrorAlert error={walletError} />

      <div className="card profile-account">
        <div className="profile-account-row">
          <div className="profile-account-email">
            <span className="profile-account-label">{t('common.email')}</span>
            <div className="profile-account-email-value">
              <span className="profile-account-email-text">
                {user.email ?? t('profile.signedInWithTelegram')}
              </span>
              {user.email ? (
                <span
                  className={`status-pill${user.email_verified ? ' status-pill--ok' : ' status-pill--warn'}`}
                >
                  {user.email_verified
                    ? t('profile.emailVerifiedShort')
                    : t('profile.emailUnverifiedShort')}
                </span>
              ) : (
                <span className="status-pill status-pill--ok">{t('profile.telegramLinkedShort')}</span>
              )}
            </div>
          </div>
          {walletEnabled ? (
            <div className="profile-wallet">
              <span className="profile-account-label">{t('profile.walletBalance')}</span>
              <p
                className="profile-account-value profile-account-value--static profile-wallet-value"
                aria-live="polite"
              >
                {isLoadingWallet ? t('profile.walletLoading') : balanceLabel}
                {!isLoadingWallet && walletBalance !== null ? (
                  <span className="profile-wallet-unit">{t('profile.walletTokens')}</span>
                ) : null}
              </p>
              <p className="profile-field-hint">{t('profile.walletHint')}</p>
            </div>
          ) : null}
        </div>
      </div>

      <nav className="profile-shortcuts profile-hub-links" aria-label={t('profile.title')}>
        {achievementsEnabled ? (
          <ShortcutLink
            to="/achievements"
            icon={<TrophyIcon />}
            title={t('nav.achievements')}
            lead={
              achievementSummary
                ? t('achievements.progress', {
                    unlocked: achievementSummary.unlocked,
                    total: achievementSummary.total_visible,
                  })
                : t('profile.achievementsLink')
            }
          />
        ) : null}
        {marketplaceEnabled ? (
          <ShortcutLink
            to="/market"
            icon={<NavMarketIcon />}
            title={t('nav.market')}
            lead={t('market.lead')}
          />
        ) : null}
        <ShortcutLink
          to="/plans"
          icon={<SparkleIcon />}
          title={t('nav.plans')}
          lead={
            user.plan && user.plan !== 'free'
              ? t('plans.youAreOn', {
                  plan: t(`plans.${user.plan}.name` as 'plans.plus.name'),
                })
              : t('profile.plansLink')
          }
        />
        {settingsLink}
        {user.is_staff ? (
          <ShortcutLink
            to="/staff"
            icon={<LockIcon />}
            title={t('staff.title')}
            lead={t('staff.profileLink')}
          />
        ) : null}
      </nav>

      {isTelegram ? null : (
        <div className="profile-logout">
          <button type="button" className="button button-secondary profile-logout-button" onClick={logout}>
            {t('nav.logOut')}
          </button>
          <p className="profile-field-hint">{t('profile.logOutHint')}</p>
        </div>
      )}
    </section>
  )
}
