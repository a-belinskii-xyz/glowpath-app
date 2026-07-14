import { Link } from 'react-router-dom'

import { Alert } from './Alert'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'

export function EmailVerificationBanner() {
  const { user } = useAuth()
  const { t } = useLocale()

  if (!user || user.email_verified) {
    return null
  }

  return (
    <Alert variant="info">
      {t('verifyBanner.message')}{' '}
      <Link to="/resend-verification">{t('verifyBanner.resend')}</Link>
    </Alert>
  )
}
