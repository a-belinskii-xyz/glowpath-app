import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { getTelegramStartParam, getTelegramWebApp, isTelegramMiniApp } from './telegram'
import { routeForStartParam } from './startParam'

let startParamApplied = false

function isTelegramDashboard(pathname: string, search: string): boolean {
  if (pathname !== '/') {
    return false
  }
  const params = new URLSearchParams(search)
  params.delete('tgWebAppStartParam')
  return [...params.keys()].length === 0
}

export function TelegramNavigation() {
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    if (!isTelegramMiniApp() || startParamApplied) {
      return
    }
    const param = getTelegramStartParam()
    if (!param) {
      startParamApplied = true
      return
    }
    const route = routeForStartParam(param)
    startParamApplied = true
    if (route && route !== `${location.pathname}${location.search}`) {
      // Push so Telegram Back returns to the dashboard instead of leaving the Mini App.
      navigate(route)
    }
  }, [location.pathname, location.search, navigate])

  useEffect(() => {
    const webApp = getTelegramWebApp()
    if (!webApp) {
      return
    }
    const back = webApp.BackButton
    if (isTelegramDashboard(location.pathname, location.search)) {
      back.hide()
      return
    }
    back.show()
    const onBack = () => {
      const historyIndex = window.history.state?.idx
      if (typeof historyIndex === 'number' && historyIndex > 0) {
        navigate(-1)
        return
      }
      navigate('/', { replace: true })
    }
    back.onClick(onBack)
    return () => {
      back.offClick(onBack)
    }
  }, [location.pathname, location.search, navigate])

  return null
}
