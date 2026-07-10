import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { verifyEmail } from '../api/auth'
import { Alert } from '../components/Alert'

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!token) {
      setError('Verification token is missing from the link')
      setIsLoading(false)
      return
    }

    const run = async () => {
      try {
        const response = await verifyEmail(token)
        setMessage(response.message)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Verification failed')
      } finally {
        setIsLoading(false)
      }
    }

    void run()
  }, [token])

  return (
    <section className="page narrow">
      <h1>Verify email</h1>

      {isLoading ? <p className="muted">Verifying your email…</p> : null}
      {error ? <Alert variant="error">{error}</Alert> : null}
      {message ? <Alert variant="success">{message}</Alert> : null}

      {!isLoading ? (
        <p className="auth-footer">
          <Link to="/login">Go to login</Link>
        </p>
      ) : null}
    </section>
  )
}
