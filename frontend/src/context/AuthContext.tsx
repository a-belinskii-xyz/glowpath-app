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
import type { LoginRequest, RegisterRequest, UserPublic } from '../types/auth'

type AuthContextValue = {
  user: UserPublic | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (body: LoginRequest) => Promise<void>
  register: (body: RegisterRequest) => Promise<string>
  logout: () => void
  refreshUser: () => Promise<void>
  completeLogin: (accessToken: string, refreshToken: string) => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null)
      return
    }

    const profile = await authApi.getMe()
    setUser(profile)
  }, [])

  const completeLogin = useCallback(async (accessToken: string, refreshToken: string) => {
    setTokens(accessToken, refreshToken)
    const profile = await authApi.getMe()
    setUser(profile)
  }, [])

  const login = useCallback(
    async (body: LoginRequest) => {
      const tokens = await authApi.login(body)
      await completeLogin(tokens.access_token, tokens.refresh_token)
    },
    [completeLogin],
  )

  const register = useCallback(async (body: RegisterRequest) => {
    const response = await authApi.register(body)
    return response.message
  }, [])

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
  }, [])

  useEffect(() => {
    const bootstrap = async () => {
      try {
        await refreshUser()
      } catch {
        clearTokens()
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    }

    void bootstrap()
  }, [refreshUser])

  const value = useMemo(
    () => ({
      user,
      isLoading,
      isAuthenticated: user !== null,
      login,
      register,
      logout,
      refreshUser,
      completeLogin,
    }),
    [user, isLoading, login, register, logout, refreshUser, completeLogin],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
