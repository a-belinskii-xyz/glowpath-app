import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { verifyEmail } from '../api/auth'
import { Alert } from '../components/Alert'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { formatApiError } from '../lib/errors'

export function VerifyEmailPage() {
  const { t } = useLocale()
  const { isAuthenticated, isLoading: isAuthLoading, refreshUser } = useAuth()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!token) {
      setError(t('errors.verifyTokenMissing'))
      setIsLoading(false)
      return
    }

    const run = async () => {
      try {
        const response = await verifyEmail(token)
        setMessage(response.message)
        try {
          await refreshUser()
        } catch {
          // Guest verification still succeeds even if there is no session.
        }
      } catch (err) {
        setError(formatApiError(err, t, 'errors.verificationFailed'))
      } finally {
        setIsLoading(false)
      }
    }

    void run()
  }, [token, t, refreshUser])

  return (
    <section className="page narrow">
      <h1>{t('auth.verifyTitle')}</h1>

      {isLoading ? <p className="muted">{t('auth.verifying')}</p> : null}
      <PageErrorAlert error={error} />
      {message ? <Alert variant="success">{message}</Alert> : null}

      {!isLoading && !isAuthLoading ? (
        <p className="auth-footer">
          {isAuthenticated ? (
            <Link to="/">{t('auth.goToApp')}</Link>
          ) : (
            <Link to="/login">{t('auth.goToLogin')}</Link>
          )}
        </p>
      ) : null}
    </section>
  )
}
