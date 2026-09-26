import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { ChevronRightIcon } from './icons'

export function ShortcutLink({
  to,
  icon,
  title,
  lead,
}: {
  to: string
  icon: ReactNode
  title: string
  lead: string
}) {
  return (
    <Link to={to} className="profile-shortcut">
      <span className="profile-shortcut-icon" aria-hidden="true">
        {icon}
      </span>
      <span className="profile-shortcut-copy">
        <span className="profile-shortcut-title">{title}</span>
        <span className="profile-shortcut-lead">{lead}</span>
      </span>
      <ChevronRightIcon className="profile-shortcut-chevron" />
    </Link>
  )
}
