import { FormEvent, useState } from 'react'

import { resendVerification } from '../api/auth'
import { Alert } from '../components/Alert'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { AuthFooterLink } from '../components/AuthCardLayout'
import { FormField } from '../components/FormField'
import { useLocale } from '../context/LocaleContext'
import { formatApiError } from '../lib/errors'

export function ResendVerificationPage() {
  const { t } = useLocale()
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setMessage(null)
    setIsSubmitting(true)

    try {
      const response = await resendVerification(email)
      setMessage(response.message)
    } catch (err) {
      setError(formatApiError(err, t, 'errors.requestFailed'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <h1>{t('auth.resendTitle')}</h1>
      <p className="muted">{t('auth.resendSubtitle')}</p>

      <PageErrorAlert error={error} />
      {message ? <Alert variant="success">{message}</Alert> : null}

      <form className="form" onSubmit={handleSubmit}>
        <FormField
          id="email"
          label={t('common.email')}
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <button className="button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? t('auth.sending') : t('auth.resendEmail')}
        </button>
      </form>

      <AuthFooterLink to="/login">{t('common.backToLogin')}</AuthFooterLink>
    </>
  )
}
