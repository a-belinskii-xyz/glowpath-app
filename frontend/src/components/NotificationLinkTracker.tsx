import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { reportNotificationEngaged } from '../api/notificationSettings'

const PARAM = 'n'

/**
 * Reminder links (email and Telegram buttons) carry `?n=<token>`. Reporting it tells the
 * server the reminder was useful, so reminders keep their normal pace instead of slowing down.
 */
export function NotificationLinkTracker() {
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const token = params.get(PARAM)
    if (!token) {
      return
    }
    void reportNotificationEngaged(token).catch(() => undefined)
    params.delete(PARAM)
    const search = params.toString()
    navigate(
      { pathname: location.pathname, search: search ? `?${search}` : '', hash: location.hash },
      { replace: true },
    )
  }, [location.hash, location.pathname, location.search, navigate])

  return null
}
