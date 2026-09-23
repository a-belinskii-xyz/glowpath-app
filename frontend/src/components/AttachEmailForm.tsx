import { FormEvent, useState } from 'react'

import { attachEmail } from '../api/auth'
import { FormField } from './FormField'
import { PageErrorAlert } from './PageErrorAlert'
import { StableButtonLabel } from './StableButtonLabel'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { formatApiError } from '../lib/errors'

export function AttachEmailForm() {
  const { t } = useLocale()
  const { refreshUser } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    if (password !== passwordConfirm) {
      setError(t('errors.passwordsMismatch'))
      return
    }
    setIsSubmitting(true)
    try {
      await attachEmail({
        email,
        password,
        password_confirm: passwordConfirm,
      })
      await refreshUser()
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedAttachEmail'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form className="form profile-attach-email" onSubmit={(event) => void handleSubmit(event)}>
      <h2 className="profile-settings-subheading">{t('profile.attachEmailTitle')}</h2>
      <p className="profile-section-lead">{t('profile.attachEmailLead')}</p>
      <PageErrorAlert error={error} />
      <FormField
        id="attach-email"
        label={t('common.email')}
        type="email"
        autoComplete="email"
        required
        value={email}
        onChange={(event) => setEmail(event.target.value)}
      />
      <FormField
        id="attach-password"
        label={t('common.password')}
        type="password"
        autoComplete="new-password"
        required
        minLength={8}
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />
      <FormField
        id="attach-password-confirm"
        label={t('common.confirmPassword')}
        type="password"
        autoComplete="new-password"
        required
        minLength={8}
        value={passwordConfirm}
        onChange={(event) => setPasswordConfirm(event.target.value)}
      />
      <button className="button" type="submit" disabled={isSubmitting}>
        <StableButtonLabel
          active={isSubmitting ? t('profile.attachEmailSaving') : t('profile.attachEmail')}
          labels={[t('profile.attachEmail'), t('profile.attachEmailSaving')]}
        />
      </button>
    </form>
  )
}
