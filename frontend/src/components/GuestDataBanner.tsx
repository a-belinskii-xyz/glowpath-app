import { Link } from 'react-router-dom'
import { useCallback, useEffect, useState } from 'react'

import { useGuestExperiment } from '../context/GuestExperimentContext'
import { useLocale } from '../context/LocaleContext'
import { getGuestEntryCount, subscribeGuestEntryCount } from '../guest/store'
import {
  dismissGuestBanner,
  guestBannerSnoozeRemainingMs,
  isGuestBannerVisible,
} from '../lib/guestBannerDismiss'
import { isGuestDiaryMode } from '../lib/guestMode'
import { isTelegramMiniApp } from '../platform/telegram'

export function GuestDataBanner() {
  const { t, tp } = useLocale()
  const { guestLocalDiary, guestOnboardingCompleted } = useGuestExperiment()
  const [entryCount, setEntryCount] = useState(0)
  const [visible, setVisible] = useState(false)

  const syncVisibility = useCallback((count: number) => {
    setVisible(isGuestBannerVisible(count))
  }, [])

  useEffect(() => {
    if (isTelegramMiniApp() || !isGuestDiaryMode()) {
      return
    }
    void getGuestEntryCount().then((count) => {
      setEntryCount(count)
      syncVisibility(count)
    })
    return subscribeGuestEntryCount((count) => {
      setEntryCount(count)
      syncVisibility(count)
    })
  }, [guestLocalDiary, syncVisibility])

  useEffect(() => {
    if (!isGuestDiaryMode() || !guestOnboardingCompleted || visible) {
      return
    }
    const remaining = guestBannerSnoozeRemainingMs()
    if (remaining === null || remaining <= 0) {
      syncVisibility(entryCount)
      return
    }
    const timer = window.setTimeout(() => {
      syncVisibility(entryCount)
    }, remaining)
    return () => {
      window.clearTimeout(timer)
    }
  }, [entryCount, guestOnboardingCompleted, syncVisibility, visible])

  const handleDismiss = () => {
    dismissGuestBanner(entryCount)
    setVisible(false)
  }

  if (isTelegramMiniApp() || !isGuestDiaryMode() || !guestOnboardingCompleted || !visible) {
    return null
  }

  return (
    <div className="guest-data-banner" role="status">
      <div className="guest-data-banner__body">
        <p className="guest-data-banner__title">
          {tp(entryCount, {
            one: 'guest.banner.titleOne',
            few: 'guest.banner.titleFew',
            many: 'guest.banner.titleMany',
          })}
        </p>
        <p>{t('guest.banner.offer')}</p>
        <ul className="guest-data-banner__benefits">
          <li>{t('guest.banner.benefitSafe')}</li>
          <li>{t('guest.banner.benefitTelegram')}</li>
          <li>{t('guest.banner.benefitReminders')}</li>
          <li>{t('guest.banner.benefitFeatures')}</li>
        </ul>
      </div>
      <div className="guest-data-banner__actions">
        <Link to="/login" className="guest-data-banner__cta">
          {t('guest.banner.signIn')}
        </Link>
        <button
          type="button"
          className="guest-data-banner__dismiss"
          onClick={handleDismiss}
          aria-label={t('guest.banner.dismiss')}
        >
          ×
        </button>
      </div>
    </div>
  )
}
