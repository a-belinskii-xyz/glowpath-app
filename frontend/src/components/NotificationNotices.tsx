import { Alert } from './Alert'
import { useLocale } from '../context/LocaleContext'

export function TestingStageNotice() {
  const { t } = useLocale()
  return <Alert variant="warning">{t('profile.notificationsTestingNotice')}</Alert>
}

export function WorkerOfflineNotice() {
  const { t } = useLocale()
  return (
    <div className="notice-worker">
      <Alert variant="warning">{t('profile.notificationsWorkerOfflineNotice')}</Alert>
    </div>
  )
}
