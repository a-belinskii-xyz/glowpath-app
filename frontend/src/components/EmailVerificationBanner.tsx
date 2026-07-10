import { Link } from 'react-router-dom'

import { Alert } from './Alert'
import { useAuth } from '../context/AuthContext'

export function EmailVerificationBanner() {
  const { user } = useAuth()

  if (!user || user.email_verified) {
    return null
  }

  return (
    <Alert variant="info">
      Verify your email to create and view mood entries.{' '}
      <Link to="/resend-verification">Resend verification email</Link>
    </Alert>
  )
}
