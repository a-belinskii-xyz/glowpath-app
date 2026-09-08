import { useEffect, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { getTelegramStartParam, getTelegramWebApp, isTelegramMiniApp } from './telegram'
import { routeForStartParam } from './startParam'

export function TelegramNavigation() {
  const location = useLocation()
  const navigate = useNavigate()
  const appliedStart = useRef(false)

  useEffect(() => {
    if (!isTelegramMiniApp() || appliedStart.current) {
      return
    }
    const param = getTelegramStartParam()
    if (!param) {
      appliedStart.current = true
      return
    }
    const route = routeForStartParam(param)
    appliedStart.current = true
    if (route && route !== `${location.pathname}${location.search}`) {
      navigate(route, { replace: true })
    }
  }, [location.pathname, location.search, navigate])

  useEffect(() => {
    const webApp = getTelegramWebApp()
    if (!webApp) {
      return
    }
    const back = webApp.BackButton
    const isRoot = location.pathname === '/' && !location.search
    if (isRoot) {
      back.hide()
      return
    }
    back.show()
    const onBack = () => {
      navigate(-1)
    }
    back.onClick(onBack)
    return () => {
      back.offClick(onBack)
    }
  }, [location.pathname, location.search, navigate])

  return null
}
