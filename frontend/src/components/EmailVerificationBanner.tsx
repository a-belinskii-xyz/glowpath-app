import { useState } from 'react'

import { resendVerification } from '../api/auth'
import { Alert } from './Alert'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { formatApiError } from '../lib/errors'

export function EmailVerificationBanner() {
  const { user, refreshUser } = useAuth()
  const { t } = useLocale()
  const [isSending, setIsSending] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  if (!user || user.email_verified) {
    return null
  }

  const handleResend = async () => {
    setError(null)
    setMessage(null)
    setIsSending(true)
    try {
      const response = await resendVerification(user.email)
      if (response.status === 'already_verified') {
        await refreshUser()
        return
      }
      setMessage(t('verifyBanner.sent'))
    } catch (err) {
      setError(formatApiError(err, t, 'errors.requestFailed'))
    } finally {
      setIsSending(false)
    }
  }

  return (
    <>
      {error ? <Alert variant="error">{error}</Alert> : null}
      {message ? (
        <Alert variant="success">{message}</Alert>
      ) : (
        <Alert variant="info">
          {t('verifyBanner.message')}{' '}
          <button
            type="button"
            className="link-button"
            disabled={isSending}
            onClick={() => void handleResend()}
          >
            {isSending ? t('verifyBanner.sending') : t('verifyBanner.resend')}
          </button>
        </Alert>
      )}
    </>
  )
}
