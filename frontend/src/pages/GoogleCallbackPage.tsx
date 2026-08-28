import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { PageErrorAlert } from '../components/PageErrorAlert'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { formatApiError } from '../lib/errors'

function parseHashTokens(): { accessToken: string; refreshToken: string; userCreated: boolean } | null {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  const accessToken = params.get('access_token')
  const refreshToken = params.get('refresh_token')

  if (!accessToken || !refreshToken) {
    return null
  }

  return {
    accessToken,
    refreshToken,
    userCreated: params.get('user_created') === '1',
  }
}

export function GoogleCallbackPage() {
  const navigate = useNavigate()
  const { completeLogin } = useAuth()
  const { t } = useLocale()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const tokens = parseHashTokens()
    if (!tokens) {
      setError(t('errors.googleNoTokens'))
      return
    }

    const run = async () => {
      try {
        await completeLogin(tokens.accessToken, tokens.refreshToken, tokens.userCreated)
        const returnTo = sessionStorage.getItem('auth_return_to')
        sessionStorage.removeItem('auth_return_to')
        navigate(returnTo && returnTo !== '/login' ? returnTo : '/', { replace: true })
      } catch (err) {
        setError(formatApiError(err, t, 'errors.googleFailed'))
      }
    }

    void run()
  }, [completeLogin, navigate, t])

  return (
    <section className="page narrow">
      <h1>{t('auth.googleTitle')}</h1>
      {error ? <PageErrorAlert error={error} /> : <p className="muted">{t('auth.googleCompleting')}</p>}
    </section>
  )
}
