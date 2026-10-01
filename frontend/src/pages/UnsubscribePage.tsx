import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { unsubscribeFromEmails } from '../api/notificationSettings'
import { Alert } from '../components/Alert'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { useLocale } from '../context/LocaleContext'
import { formatApiError } from '../lib/errors'

// Asks before unsubscribing: mail scanners open links, so a bare GET must not change anything.
export function UnsubscribePage() {
  const { t } = useLocale()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isDone, setIsDone] = useState(false)
  const [error, setError] = useState<string | null>(token ? null : t('unsubscribe.missingToken'))

  const handleConfirm = async () => {
    setIsSubmitting(true)
    setError(null)
    try {
      await unsubscribeFromEmails(token)
      setIsDone(true)
    } catch (err) {
      setError(formatApiError(err, t, 'unsubscribe.failed'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="page narrow">
      <h1>{t('unsubscribe.title')}</h1>
      <PageErrorAlert error={error} />
      {isDone ? (
        <>
          <Alert variant="success">{t('unsubscribe.done')}</Alert>
          <p className="auth-footer">
            <Link to="/settings/notifications">{t('unsubscribe.toSettings')}</Link>
          </p>
        </>
      ) : token ? (
        <>
          <p>{t('unsubscribe.prompt')}</p>
          <button
            className="button"
            type="button"
            disabled={isSubmitting}
            onClick={() => void handleConfirm()}
          >
            {isSubmitting ? t('unsubscribe.working') : t('unsubscribe.confirm')}
          </button>
        </>
      ) : null}
    </section>
  )
}
