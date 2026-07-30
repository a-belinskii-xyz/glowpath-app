import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'

import { Alert } from '../components/Alert'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { AuthFooterLink } from '../components/AuthCardLayout'
import { FormField } from '../components/FormField'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { detectTimezone } from '../lib/timezones'
import { formatApiError } from '../lib/errors'

export function RegisterPage() {
  const { register } = useAuth()
  const { t } = useLocale()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [timezone] = useState(detectTimezone)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setSuccess(null)

    if (password !== passwordConfirm) {
      setError(t('errors.passwordsMismatch'))
      return
    }

    setIsSubmitting(true)

    try {
      const message = await register({ email, password, password_confirm: passwordConfirm, timezone })
      setSuccess(message)
    } catch (err) {
      setError(formatApiError(err, t, 'errors.registrationFailed'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <h1>{t('auth.createAccountTitle')}</h1>
      <p className="muted">{t('auth.createAccountSubtitle')}</p>

      <PageErrorAlert error={error} />
      {success ? <Alert variant="success">{success}</Alert> : null}

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
        <FormField
          id="password"
          label={t('common.password')}
          type="password"
          autoComplete="new-password"
          minLength={8}
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <FormField
          id="password_confirm"
          label={t('common.confirmPassword')}
          type="password"
          autoComplete="new-password"
          minLength={8}
          required
          value={passwordConfirm}
          onChange={(event) => setPasswordConfirm(event.target.value)}
        />
        <FormField
          id="timezone"
          label={t('common.timezone')}
          type="text"
          readOnly
          value={timezone}
          hint={t('auth.timezoneHint')}
        />
        <button className="button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? t('auth.creatingAccount') : t('nav.register')}
        </button>
      </form>

      <AuthFooterLink to="/login">{t('auth.alreadyHaveAccount')}</AuthFooterLink>
      <p className="auth-footer">
        {t('auth.needNewLink')}{' '}
        <Link to="/resend-verification">{t('auth.resendVerificationShort')}</Link>
      </p>
    </>
  )
}
