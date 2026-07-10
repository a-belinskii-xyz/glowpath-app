import { FormEvent, useState } from 'react'

import { resendVerification } from '../api/auth'
import { Alert } from '../components/Alert'
import { AuthFooterLink } from '../components/AuthCardLayout'
import { FormField } from '../components/FormField'

export function ResendVerificationPage() {
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
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <h1>Resend verification</h1>
      <p className="muted">Send a new verification email to your inbox.</p>

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
          {isSubmitting ? 'Sending…' : 'Resend email'}
        </button>
      </form>

      <AuthFooterLink to="/login">Back to login</AuthFooterLink>
    </>
  )
}
