import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { verifyEmail } from '../api/auth'
import { Alert } from '../components/Alert'
import { useLocale } from '../context/LocaleContext'

export function VerifyEmailPage() {
  const { t } = useLocale()
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
      } catch (err) {
        setError(err instanceof Error ? err.message : t('errors.verificationFailed'))
      } finally {
        setIsLoading(false)
      }
    }

    void run()
  }, [token, t])

  return (
    <section className="page narrow">
      <h1>{t('auth.verifyTitle')}</h1>

      {isLoading ? <p className="muted">{t('auth.verifying')}</p> : null}
      {error ? <Alert variant="error">{error}</Alert> : null}
      {message ? <Alert variant="success">{message}</Alert> : null}

      {!isLoading ? (
        <p className="auth-footer">
          <Link to="/login">{t('auth.goToLogin')}</Link>
        </p>
      ) : null}
    </section>
  )
}
