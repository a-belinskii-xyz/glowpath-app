import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'

import { Alert } from '../components/Alert'
import { AuthFooterLink } from '../components/AuthCardLayout'
import { FormField } from '../components/FormField'
import { useAuth } from '../context/AuthContext'

function detectTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Minsk'
  } catch {
    return 'Europe/Minsk'
  }
}

export function RegisterPage() {
  const { register } = useAuth()
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
      setError('Passwords do not match')
      return
    }

    setIsSubmitting(true)

    try {
      const message = await register({ email, password, password_confirm: passwordConfirm, timezone })
      setSuccess(message)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <h1>Create account</h1>
      <p className="muted">We will send a verification link to your email.</p>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {success ? <Alert variant="success">{success}</Alert> : null}

      <form className="form" onSubmit={handleSubmit}>
        <FormField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <FormField
          id="password"
          label="Password"
          type="password"
          autoComplete="new-password"
          minLength={8}
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
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
        <FormField
          id="timezone"
          label="Timezone"
          type="text"
          readOnly
          value={timezone}
          hint="Detected from your browser"
        />
        <button className="button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Creating account…' : 'Register'}
        </button>
      </form>

      <AuthFooterLink to="/login">Already have an account? Log in</AuthFooterLink>
      <p className="auth-footer">
        Need a new link? <Link to="/resend-verification">Resend verification</Link>
      </p>
    </>
  )
}
