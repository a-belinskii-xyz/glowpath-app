import { FormEvent, useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'

import { resetPassword } from '../api/auth'
import { Alert } from '../components/Alert'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { AuthFooterLink } from '../components/AuthCardLayout'
import { FormField } from '../components/FormField'
import { StableButtonLabel } from '../components/StableButtonLabel'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { formatApiError } from '../lib/errors'

export function ResetPasswordPage() {
  const navigate = useNavigate()
  const { t } = useLocale()
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''

  const [newPassword, setNewPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const afterResetPath = isAuthenticated ? '/profile' : '/login'

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setSuccess(null)

    if (!token) {
      setError(t('errors.resetTokenMissing'))
      return
    }

    if (newPassword !== passwordConfirm) {
      setError(t('errors.passwordsMismatch'))
      return
    }

    setIsSubmitting(true)

    try {
      const response = await resetPassword({
        token,
        new_password: newPassword,
        password_confirm: passwordConfirm,
      })
      setSuccess(response.message)
      setTimeout(() => navigate(afterResetPath), 1500)
    } catch (err) {
      setError(formatApiError(err, t, 'errors.passwordResetFailed'))
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!token) {
    if (isAuthLoading) {
      return <p className="muted">{t('common.loading')}</p>
    }
    if (isAuthenticated) {
      return <Navigate to="/profile" replace />
    }
    return (
      <>
        <h1>{t('auth.resetTitle')}</h1>
        <Alert variant="error">{t('auth.invalidResetToken')}</Alert>
        <AuthFooterLink to="/forgot-password">{t('auth.requestResetLink')}</AuthFooterLink>
      </>
    )
  }

  return (
    <>
      <h1>{t('auth.resetTitle')}</h1>
      <p className="muted">{t('auth.resetSubtitle')}</p>

      <PageErrorAlert error={error} />
      {success ? <Alert variant="success">{success}</Alert> : null}

      <form className="form" onSubmit={handleSubmit}>
        <FormField
          id="new_password"
          label={t('auth.newPassword')}
          type="password"
          autoComplete="new-password"
          minLength={8}
          required
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
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
        <button className="button button-block" type="submit" disabled={isSubmitting}>
          <StableButtonLabel
            active={isSubmitting ? t('common.saving') : t('auth.resetPassword')}
            labels={[t('auth.resetPassword'), t('common.saving')]}
          />
        </button>
      </form>

      {isAuthLoading ? null : isAuthenticated ? (
        <AuthFooterLink to="/profile">{t('common.backToProfile')}</AuthFooterLink>
      ) : (
        <AuthFooterLink to="/login">{t('common.backToLogin')}</AuthFooterLink>
      )}
    </>
  )
}
