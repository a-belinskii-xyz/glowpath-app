import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'

import { useGuestExperiment } from '../context/GuestExperimentContext'
import { useLocale } from '../context/LocaleContext'
import { getGuestEntryCount } from '../guest/store'
import { isGuestDiaryMode } from '../lib/guestMode'

export function GuestDataBanner() {
  const { t } = useLocale()
  const { guestLocalDiary } = useGuestExperiment()
  const [entryCount, setEntryCount] = useState(0)

  useEffect(() => {
    if (!isGuestDiaryMode()) return
    void getGuestEntryCount().then(setEntryCount)
  }, [guestLocalDiary])

  if (!isGuestDiaryMode()) {
    return null
  }

  return (
    <div className="guest-data-banner" role="status">
      <p>
        {t('guest.banner.message', { count: String(entryCount) })}
      </p>
      <Link to="/register" className="guest-data-banner__cta">
        {t('guest.banner.createAccount')}
      </Link>
    </div>
  )
}
