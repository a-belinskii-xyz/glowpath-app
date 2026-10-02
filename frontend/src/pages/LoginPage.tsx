import { useCallback, useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { getTelegramBrowserLoginUrl } from '../api/auth'
import { getTelegramEntryPoint } from '../api/telegram'
import { Alert } from '../components/Alert'
import { TelegramBotLogin } from '../components/TelegramBotLogin'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { getGuestLocalEntryCount } from '../lib/guestImport'
import { isGuestDiaryMode } from '../lib/guestMode'
import { detectTimezone } from '../lib/timezones'
import { isTelegramMiniApp } from '../platform/telegram'
import type { TelegramEntryPointPublic } from '../types/telegram'

const AUTH_RETURN_TO_KEY = 'auth_return_to'

type LoginLocationState = {
  from?: { pathname: string; search: string }
}

function postLoginPath(state: LoginLocationState | null): string {
  const from = state?.from
  if (!from?.pathname || from.pathname === '/login') {
    return '/'
  }
  return `${from.pathname}${from.search}`
}

/** Guest landing and `/login`: one card for Telegram, one for signing in on the website. */
export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { completeLogin } = useAuth()
  const { t } = useLocale()
  const [entryPoint, setEntryPoint] = useState<TelegramEntryPointPublic | null>(null)
  const returnTo = postLoginPath(location.state as LoginLocationState | null)
  const [guestEntryCount, setGuestEntryCount] = useState(0)
  // Inside the Mini App the user is already in Telegram. A guest with entries signs in on the
  // website instead: the Mini App can't see entries kept in this browser.
  const showTelegramCard =
    Boolean(entryPoint?.bot_url) && !isTelegramMiniApp() && guestEntryCount === 0

  useEffect(() => {
    if (!isGuestDiaryMode()) return
    void getGuestLocalEntryCount().then(setGuestEntryCount)
  }, [])

  useEffect(() => {
    let cancelled = false
    void getTelegramEntryPoint()
      .then((payload) => {
        if (!cancelled) {
          setEntryPoint(payload)
        }
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [])

  const handleTokens = useCallback(
    async (accessToken: string, refreshToken: string, userCreated: boolean) => {
      await completeLogin(accessToken, refreshToken, userCreated)
      navigate(returnTo, { replace: true })
    },
    [completeLogin, navigate, returnTo],
  )

  return (
    <section className="page telegram-first-landing">
      <h1>{t('brand')}</h1>
      <p className="muted">{t('home.entryLead')}</p>

      {isGuestDiaryMode() ? (
        <Alert variant="info">{t('guest.loginWarning')}</Alert>
      ) : null}

      <div className="entry-cards">
        {showTelegramCard && entryPoint?.bot_url ? (
          <div className="card entry-card">
            <h2>
              <span className="entry-card-icon" aria-hidden="true">
                ✈️
              </span>
              {t('home.telegramTitle')}
            </h2>
            <p className="muted">{t('home.telegramText')}</p>
            <div className="entry-card-actions">
              <a className="button button-block" href={entryPoint.bot_url}>
                {t('auth.openBot')}
              </a>
            </div>
          </div>
        ) : null}

        {entryPoint?.bot_login || entryPoint?.browser_login ? (
          <div className="card entry-card">
            <h2>
              <span className="entry-card-icon" aria-hidden="true">
                🖥️
              </span>
              {t('home.websiteTitle')}
            </h2>
            <p className="muted">{t('home.websiteText')}</p>
            <div className="entry-card-actions">
              {entryPoint.bot_login ? <TelegramBotLogin onTokens={handleTokens} /> : null}
              {entryPoint.browser_login ? (
                <a
                  className={
                    entryPoint.bot_login
                      ? 'entry-card-alt'
                      : 'button button-secondary button-block'
                  }
                  href={getTelegramBrowserLoginUrl(detectTimezone())}
                  onClick={() => {
                    if (returnTo !== '/') {
                      sessionStorage.setItem(AUTH_RETURN_TO_KEY, returnTo)
                    }
                  }}
                >
                  {t('auth.signInWithTelegramLogin')}
                </a>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  )
}
