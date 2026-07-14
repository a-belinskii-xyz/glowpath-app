import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Alert } from '../components/Alert'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'

function parseHashTokens(): { accessToken: string; refreshToken: string } | null {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  const accessToken = params.get('access_token')
  const refreshToken = params.get('refresh_token')

  if (!accessToken || !refreshToken) {
    return null
  }

  return { accessToken, refreshToken }
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
        await completeLogin(tokens.accessToken, tokens.refreshToken)
        navigate('/', { replace: true })
      } catch (err) {
        setError(err instanceof Error ? err.message : t('errors.googleFailed'))
      }
    }

    void run()
  }, [completeLogin, navigate, t])

  return (
    <section className="page narrow">
      <h1>{t('auth.googleTitle')}</h1>
      {error ? <Alert variant="error">{error}</Alert> : <p className="muted">{t('auth.googleCompleting')}</p>}
    </section>
  )
}
