import { FormEvent, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { getGoogleLoginUrl } from '../api/auth'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { AuthFooterLink } from '../components/AuthCardLayout'
import { FormField } from '../components/FormField'
import { StableButtonLabel } from '../components/StableButtonLabel'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { ApiError, formatApiError } from '../lib/errors'

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
      <p className="muted">{t('auth.logInSubtitle')}</p>

      <PageErrorAlert error={error} />

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

      <div className="divider">{t('common.or')}</div>

      <a
        className="button button-secondary button-block"
        href={getGoogleLoginUrl()}
        onClick={() => {
          const returnTo = postLoginPath(location.state as LoginLocationState | null)
          if (returnTo !== '/') {
            sessionStorage.setItem(AUTH_RETURN_TO_KEY, returnTo)
          }
        }}
      >
        {t('auth.continueWithGoogle')}
      </a>

      <AuthFooterLink to="/forgot-password">{t('auth.forgotPassword')}</AuthFooterLink>
      <AuthFooterLink to="/resend-verification">{t('auth.resendVerification')}</AuthFooterLink>
      <p className="auth-footer">
        {t('auth.noAccount')} <Link to="/register">{t('nav.register')}</Link>
      </p>
    </>
  )
}
