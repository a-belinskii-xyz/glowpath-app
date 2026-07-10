import { FormEvent, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { resetPassword } from '../api/auth'
import { Alert } from '../components/Alert'
import { AuthFooterLink } from '../components/AuthCardLayout'
import { FormField } from '../components/FormField'

export function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''

  const [newPassword, setNewPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setSuccess(null)

    if (!token) {
      setError('Reset token is missing from the link')
      return
    }

    if (newPassword !== passwordConfirm) {
      setError('Passwords do not match')
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
      setTimeout(() => navigate('/login'), 1500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Password reset failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!token) {
    return (
      <>
        <h1>Reset password</h1>
        <Alert variant="error">Invalid or missing reset token. Request a new link.</Alert>
        <AuthFooterLink to="/forgot-password">Request reset link</AuthFooterLink>
      </>
    )
  }

  return (
    <>
      <h1>Reset password</h1>
      <p className="muted">Choose a new password for your account.</p>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {success ? <Alert variant="success">{success}</Alert> : null}

      <form className="form" onSubmit={handleSubmit}>
        <FormField
          id="new_password"
          label="New password"
          type="password"
          autoComplete="new-password"
          minLength={8}
          required
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
        />
        <FormField
          id="password_confirm"
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          minLength={8}
          required
          value={passwordConfirm}
          onChange={(event) => setPasswordConfirm(event.target.value)}
        />
        <button className="button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Saving…' : 'Reset password'}
        </button>
      </form>

      <AuthFooterLink to="/login">Back to login</AuthFooterLink>
    </>
  )
}
