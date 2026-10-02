import { useCallback, useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { getTelegramBrowserLoginUrl } from '../api/auth'
import { getTelegramEntryPoint } from '../api/telegram'
import { Alert } from '../components/Alert'
import { TelegramBotLogin } from '../components/TelegramBotLogin'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { isGuestDiaryMode } from '../lib/guestMode'
import { detectTimezone } from '../lib/timezones'
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

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { completeLogin } = useAuth()
  const { t } = useLocale()
  const [entryPoint, setEntryPoint] = useState<TelegramEntryPointPublic | null>(null)
  const returnTo = postLoginPath(location.state as LoginLocationState | null)

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
    <>
      <h1>{t('auth.logInTitle')}</h1>
      <p className="muted">{t('auth.telegramPrimary')}</p>

      {isGuestDiaryMode() ? (
        <Alert variant="info">{t('guest.loginWarning')}</Alert>
      ) : null}

      <div className="auth-oauth-actions">
        {entryPoint?.bot_login ? <TelegramBotLogin onTokens={handleTokens} /> : null}

        {entryPoint?.browser_login ? (
          <a
            className="button button-secondary button-block"
            href={getTelegramBrowserLoginUrl(detectTimezone())}
            onClick={() => {
              if (returnTo !== '/') {
                sessionStorage.setItem(AUTH_RETURN_TO_KEY, returnTo)
              }
            }}
          >
            {t('auth.continueWithTelegram')}
          </a>
        ) : null}

        {/* The Mini App can't see entries kept in this browser, so a guest signs in here. */}
        {entryPoint?.bot_url && !isGuestDiaryMode() ? (
          <a className="button button-secondary button-block" href={entryPoint.bot_url}>
            {t('auth.openInTelegram')}
          </a>
        ) : null}
      </div>
    </>
  )
}
