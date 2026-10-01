import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

import * as authApi from '../api/auth'
import {
  getThemePreference,
  setThemePreference,
  type ThemePreference,
} from '../design/themePreference'
import { useLocale } from './LocaleContext'
import { clearTokens, getAccessToken, setTokens } from '../lib/storage'
import { getVisitorId } from '../lib/guestMode'
import { tryImportGuestDiaryAfterAuth } from '../lib/guestImport'
import {
  applyTelegramChrome,
  isTelegramMiniApp,
  getTelegramWebApp,
  subscribeTelegramTheme,
} from '../platform/telegram'
import type { LoginRequest, RegisterRequest, UserPublic } from '../types/auth'

type AuthContextValue = {
  user: UserPublic | null
  isLoading: boolean
  isAuthenticated: boolean
  isTelegram: boolean
  telegramAuthError: string | null
  login: (body: LoginRequest) => Promise<void>
  register: (body: RegisterRequest) => Promise<string>
  logout: () => void
  refreshUser: () => Promise<void>
  updateTimezone: (timezone: string) => Promise<void>
  updateThemePreference: (themePreference: ThemePreference) => Promise<void>
  completeLogin: (accessToken: string, refreshToken: string, userCreated?: boolean) => Promise<void>
  retryBootstrap: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function browserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Minsk'
  } catch {
    return 'Europe/Minsk'
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [telegramAuthError, setTelegramAuthError] = useState<string | null>(null)
  const [bootId, setBootId] = useState(0)
  const isTelegram = isTelegramMiniApp()
  const { locale, setLocale } = useLocale()

  const refreshUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null)
      return
    }

    const profile = await authApi.getMe()
    setUser(profile)
  }, [])

  const completeLogin = useCallback(async (accessToken: string, refreshToken: string, userCreated?: boolean) => {
    setTokens(accessToken, refreshToken)
    const profile = await authApi.getMe()
    setUser(profile)
    await tryImportGuestDiaryAfterAuth(userCreated)
  }, [])

  const login = useCallback(
    async (body: LoginRequest) => {
      const tokens = await authApi.login({
        ...body,
        visitor_id: getVisitorId() ?? undefined,
      })
      await completeLogin(tokens.access_token, tokens.refresh_token, tokens.user_created ?? false)
    },
    [completeLogin],
  )

  const register = useCallback(async (body: RegisterRequest) => {
    const response = await authApi.register({
      ...body,
      visitor_id: getVisitorId() ?? undefined,
    })
    return response.message
  }, [])

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
  }, [])

  const updateTimezone = useCallback(async (timezone: string) => {
    const profile = await authApi.updateMe({ timezone })
    setUser(profile)
  }, [])

  const updateThemePreference = useCallback(async (themePreference: ThemePreference) => {
    const previous = getThemePreference()
    setThemePreference(themePreference)
    try {
      const profile = await authApi.updateMe({ theme_preference: themePreference })
      setUser(profile)
    } catch (err) {
      setThemePreference(previous)
      throw err
    }
  }, [])

  const retryBootstrap = useCallback(() => {
    setTelegramAuthError(null)
    setIsLoading(true)
    setBootId((current) => current + 1)
  }, [])

  useEffect(() => {
    let cancelled = false
    const bootstrap = async () => {
      setIsLoading(true)
      try {
        if (isTelegramMiniApp()) {
          applyTelegramChrome()
          const webApp = getTelegramWebApp()
          if (!webApp) {
            if (!cancelled) {
              setTelegramAuthError('missing_init_data')
            }
            return
          }
          const tokens = await authApi.loginTelegram({
            init_data: webApp.initData,
            timezone: browserTimezone(),
          })
          if (cancelled) {
            return
          }
          await completeLogin(tokens.access_token, tokens.refresh_token, tokens.user_created ?? false)
          if (!cancelled) {
            setTelegramAuthError(null)
          }
          return
        }
        if (!getAccessToken()) {
          if (!cancelled) {
            setUser(null)
          }
          return
        }
        const profile = await authApi.getMe()
        if (!cancelled) {
          setUser(profile)
        }
      } catch {
        if (cancelled) {
          return
        }
        if (isTelegramMiniApp()) {
          setTelegramAuthError('auth_failed')
        }
        clearTokens()
        setUser(null)
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void bootstrap()
    return () => {
      cancelled = true
    }
  }, [bootId, completeLogin])

  useEffect(() => {
    if (!isTelegramMiniApp()) {
      return
    }
    return subscribeTelegramTheme(() => undefined)
  }, [])

  const serverThemePreference = user?.theme_preference
  useEffect(() => {
    if (serverThemePreference) {
      setThemePreference(serverThemePreference)
    }
  }, [serverThemePreference])

  // The account keeps the interface language so reminders can use it. Once per account
  // (and whenever the saved value changes) the saved language wins over this device's;
  // an account without one adopts the language this device is showing.
  const userId = user?.id
  const serverLocale = user?.locale ?? null
  const reconciledRef = useRef<string | null>(null)
  useEffect(() => {
    if (!userId) {
      reconciledRef.current = null
      return
    }
    const key = `${userId}:${serverLocale ?? ''}`
    if (reconciledRef.current === key) {
      return
    }
    reconciledRef.current = key
    if (serverLocale) {
      if (serverLocale !== locale) {
        setLocale(serverLocale)
      }
      return
    }
    authApi
      .updateMe({ locale })
      .then(setUser)
      .catch(() => undefined)
  }, [userId, serverLocale, locale, setLocale])

  // Language picked in the app afterwards is saved to the account.
  const previousLocaleRef = useRef(locale)
  useEffect(() => {
    const changed = previousLocaleRef.current !== locale
    previousLocaleRef.current = locale
    if (!changed || !userId || !serverLocale || serverLocale === locale) {
      return
    }
    authApi
      .updateMe({ locale })
      .then(setUser)
      .catch(() => undefined)
  }, [locale, userId, serverLocale])

  const value = useMemo(
    () => ({
      user,
      isLoading,
      isAuthenticated: user !== null,
      isTelegram,
      telegramAuthError,
      login,
      register,
      logout,
      refreshUser,
      updateTimezone,
      updateThemePreference,
      completeLogin,
      retryBootstrap,
    }),
    [
      user,
      isLoading,
      isTelegram,
      telegramAuthError,
      login,
      register,
      logout,
      refreshUser,
      updateTimezone,
      updateThemePreference,
      completeLogin,
      retryBootstrap,
    ],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
