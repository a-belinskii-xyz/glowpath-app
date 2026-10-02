import { useState } from 'react'

import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { formatApiError } from '../lib/errors'
import { importGuestDiaryNow } from '../lib/guestImport'
import { ConfirmDialog } from './ConfirmDialog'

/** Offers to move guest entries from this browser into the account the person signed in to. */
export function GuestImportPrompt() {
  const { pendingGuestImport, dismissGuestImport } = useAuth()
  const { t, tp } = useLocale()
  const [isBusy, setIsBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!pendingGuestImport) {
    return null
  }

  const handleConfirm = async () => {
    setIsBusy(true)
    setError(null)
    try {
      await importGuestDiaryNow(pendingGuestImport.visitorId)
      // Entries, tags and goals change across every screen, so start them fresh.
      window.location.reload()
    } catch (err) {
      setError(formatApiError(err, t, 'guest.import.failed'))
      setIsBusy(false)
    }
  }

  const handleCancel = () => {
    setError(null)
    dismissGuestImport()
  }

  return (
    <ConfirmDialog
      open
      variant="default"
      title={t('guest.import.title')}
      message={t('guest.import.message')}
      confirmLabel={t('guest.import.confirm')}
      cancelLabel={t('guest.import.later')}
      busyLabel={t('guest.import.busy')}
      isBusy={isBusy}
      error={error}
      preview={
        <ul className="guest-import-list">
          <li>
            {tp(pendingGuestImport.entryCount, {
              one: 'guest.import.entriesOne',
              few: 'guest.import.entriesFew',
              many: 'guest.import.entriesMany',
            })}
          </li>
          <li>{t('guest.import.extras')}</li>
        </ul>
      }
      onConfirm={() => void handleConfirm()}
      onCancel={handleCancel}
    />
  )
}
