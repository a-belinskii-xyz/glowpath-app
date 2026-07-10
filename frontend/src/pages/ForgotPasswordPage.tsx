import { FormEvent, useState } from 'react'

import { forgotPassword } from '../api/auth'
import { Alert } from '../components/Alert'
import { AuthFooterLink } from '../components/AuthCardLayout'
import { FormField } from '../components/FormField'

export function ForgotPasswordPage() {
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
      const response = await forgotPassword(email)
      setMessage(response.message)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <h1>Forgot password</h1>
      <p className="muted">We will email you a reset link if the account exists.</p>

      {error ? <Alert variant="error">{error}</Alert> : null}
      {message ? <Alert variant="success">{message}</Alert> : null}

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
        <button className="button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Sending…' : 'Send reset link'}
        </button>
      </form>

      <AuthFooterLink to="/login">Back to login</AuthFooterLink>
    </>
  )
}
