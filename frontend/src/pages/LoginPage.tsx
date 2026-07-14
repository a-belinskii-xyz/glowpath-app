import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { getGoogleLoginUrl } from '../api/auth'
import { Alert } from '../components/Alert'
import { AuthFooterLink } from '../components/AuthCardLayout'
import { FormField } from '../components/FormField'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { ApiError } from '../lib/errors'

export function LoginPage() {
  const navigate = useNavigate()
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
      navigate('/')
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError(t('errors.emailNotVerified'))
      } else {
        setError(err instanceof Error ? err.message : t('errors.loginFailed'))
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <h1>{t('auth.logInTitle')}</h1>
      <p className="muted">{t('auth.logInSubtitle')}</p>

      {error ? <Alert variant="error">{error}</Alert> : null}

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
        <button className="button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? t('auth.signingIn') : t('auth.signIn')}
        </button>
      </form>

      <div className="divider">{t('common.or')}</div>

      <a className="button button-secondary button-block" href={getGoogleLoginUrl()}>
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
