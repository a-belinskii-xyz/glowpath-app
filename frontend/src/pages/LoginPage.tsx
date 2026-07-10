import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { getGoogleLoginUrl } from '../api/auth'
import { Alert } from '../components/Alert'
import { AuthFooterLink } from '../components/AuthCardLayout'
import { FormField } from '../components/FormField'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../lib/errors'

export function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
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
        setError('Email is not verified yet. Resend the verification email and try again.')
      } else {
        setError(err instanceof Error ? err.message : 'Login failed')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <h1>Log in</h1>
      <p className="muted">Use your email and password, or continue with Google.</p>

      {error ? <Alert variant="error">{error}</Alert> : null}

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
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <button className="button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      <div className="divider">or</div>

      <a className="button button-secondary button-block" href={getGoogleLoginUrl()}>
        Continue with Google
      </a>

      <AuthFooterLink to="/forgot-password">Forgot password?</AuthFooterLink>
      <AuthFooterLink to="/resend-verification">Resend verification email</AuthFooterLink>
      <p className="auth-footer">
        No account? <Link to="/register">Register</Link>
      </p>
    </>
  )
}
