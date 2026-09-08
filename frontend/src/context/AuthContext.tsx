import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import * as authApi from '../api/auth'
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
  completeLogin: (accessToken: string, refreshToken: string, userCreated?: boolean) => Promise<void>
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
  const isTelegram = isTelegramMiniApp()

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

  useEffect(() => {
    const bootstrap = async () => {
      try {
        if (isTelegramMiniApp()) {
          applyTelegramChrome()
          const webApp = getTelegramWebApp()
          if (!webApp) {
            setTelegramAuthError('missing_init_data')
            return
          }
          const tokens = await authApi.loginTelegram({
            init_data: webApp.initData,
            timezone: browserTimezone(),
          })
          await completeLogin(tokens.access_token, tokens.refresh_token, tokens.user_created ?? false)
          setTelegramAuthError(null)
          return
        }
        await refreshUser()
      } catch {
        if (isTelegramMiniApp()) {
          setTelegramAuthError('auth_failed')
        }
        clearTokens()
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    }

    void bootstrap()
  }, [completeLogin, refreshUser])

  useEffect(() => {
    if (!isTelegramMiniApp()) {
      return
    }
    return subscribeTelegramTheme(() => undefined)
  }, [])

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
      completeLogin,
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
      completeLogin,
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
