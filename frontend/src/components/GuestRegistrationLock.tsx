import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { useLocale } from '../context/LocaleContext'
import { LockIcon } from './icons'

type GuestLockBadgeProps = {
  inline?: boolean
}

export function GuestLockBadge({ inline = false }: GuestLockBadgeProps) {
  return (
    <span
      className={inline ? 'guest-lock-badge guest-lock-badge--inline' : 'guest-lock-badge'}
      aria-hidden="true"
    >
      <LockIcon />
    </span>
  )
}

type GuestRegistrationCalloutProps = {
  message: string
}

export function GuestRegistrationCallout({ message }: GuestRegistrationCalloutProps) {
  const { t } = useLocale()

  return (
    <div className="guest-registration-callout" role="status">
      <span className="guest-registration-callout__icon" aria-hidden="true">
        <LockIcon />
      </span>
      <p className="guest-registration-callout__text">{message}</p>
      <Link className="guest-registration-callout__cta" to="/login">
        {t('guest.banner.createAccount')}
      </Link>
    </div>
  )
}

type GuestLockedPreviewProps = {
  message: string
  /** Controls that stay interactive (e.g. language). Rendered outside the locked body. */
  unlocked?: ReactNode
  children: ReactNode
}

/** Full UI preview with registration callout; interactive content is non-operational. */
export function GuestLockedPreview({ message, unlocked, children }: GuestLockedPreviewProps) {
  return (
    <div className="guest-locked-preview">
      <GuestRegistrationCallout message={message} />
      {unlocked}
      <div className="guest-locked-preview__body">{children}</div>
    </div>
  )
}
