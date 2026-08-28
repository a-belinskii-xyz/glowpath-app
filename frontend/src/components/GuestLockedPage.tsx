import { Link } from 'react-router-dom'

import { useLocale } from '../context/LocaleContext'
import { isGuestDiaryMode } from '../lib/guestMode'

type GuestLockedPageProps = {
  feature: 'gallery' | 'market' | 'achievements' | 'profile'
}

export function GuestLockedPage({ feature }: GuestLockedPageProps) {
  const { t } = useLocale()

  if (!isGuestDiaryMode()) {
    return null
  }

  return (
    <section className="page guest-locked-page">
      <h1>{t(`guest.locked.${feature}.title`)}</h1>
      <p className="muted">{t(`guest.locked.${feature}.body`)}</p>
      <p className="muted">{t('guest.locked.common')}</p>
      <Link to="/register">{t('guest.banner.createAccount')}</Link>
    </section>
  )
}
