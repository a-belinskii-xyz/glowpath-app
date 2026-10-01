import { FormEvent, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { Alert } from '../components/Alert'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { AuthFooterLink } from '../components/AuthCardLayout'
import { FormField } from '../components/FormField'
import { StableButtonLabel } from '../components/StableButtonLabel'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { isGuestDiaryMode } from '../lib/guestMode'
import { ApiError, formatApiError } from '../lib/errors'

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

// Hidden while sign-in is Telegram-only (GP-28); kept for accounts created with email.
export function EmailLoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()
  const { t } = useLocale()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await login({ email, password })
      navigate(postLoginPath(location.state as LoginLocationState | null), { replace: true })
    } catch (err) {
      if (err instanceof ApiError && (err.code === 'email_not_verified' || err.status === 403)) {
        setError(t('errors.emailNotVerified'))
      } else {
        setError(formatApiError(err, t, 'errors.loginFailed'))
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <h1>{t('auth.logInTitle')}</h1>

      <PageErrorAlert error={error} />
      {isGuestDiaryMode() ? (
        <Alert variant="warning">{t('guest.loginWarning')}</Alert>
      ) : null}

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
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <button className="button button-block" type="submit" disabled={isSubmitting}>
          <StableButtonLabel
            active={isSubmitting ? t('auth.signingIn') : t('auth.signIn')}
            labels={[t('auth.signIn'), t('auth.signingIn')]}
          />
        </button>
      </form>

      <AuthFooterLink to="/forgot-password">{t('auth.forgotPassword')}</AuthFooterLink>
      <AuthFooterLink to="/resend-verification">{t('auth.resendVerification')}</AuthFooterLink>
    </>
  )
}
