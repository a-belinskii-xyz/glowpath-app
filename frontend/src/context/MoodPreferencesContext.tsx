import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { getMoodPreferences } from '../api/moodPreferences'
import { useAuth } from './AuthContext'
import { defaultMoodPreferences, getMoodScoreColor, getMoodScoreStyle } from '../lib/moodScale'
import type { MoodPreferencesPublic, MoodScoreStylePublic } from '../types/moodPreferences'

type MoodPreferencesContextValue = {
  scores: Record<string, MoodScoreStylePublic>
  isLoading: boolean
  refreshPreferences: () => Promise<void>
  setPreferences: (preferences: MoodPreferencesPublic) => void
  getScoreColor: (score: number) => string
  getScoreStyle: (score: number) => MoodScoreStylePublic
}

const MoodPreferencesContext = createContext<MoodPreferencesContextValue | null>(null)

export function MoodPreferencesProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [scores, setScores] = useState<Record<string, MoodScoreStylePublic>>(defaultMoodPreferences())
  const [isLoading, setIsLoading] = useState(false)

  const refreshPreferences = useCallback(async () => {
    if (!user?.email_verified) {
      setScores(defaultMoodPreferences())
      return
    }

    setIsLoading(true)
    try {
      const preferences = await getMoodPreferences()
      setScores(preferences.scores)
    } catch {
      setScores(defaultMoodPreferences())
    } finally {
      setIsLoading(false)
    }
  }, [user?.email_verified])

  const setPreferences = useCallback((preferences: MoodPreferencesPublic) => {
    setScores(preferences.scores)
  }, [])

  useEffect(() => {
    if (!user?.email_verified) {
      setScores(defaultMoodPreferences())
      setIsLoading(false)
      return
    }

    void refreshPreferences()
  }, [user?.email_verified, refreshPreferences])

  const value = useMemo(
    () => ({
      scores,
      isLoading,
      refreshPreferences,
      setPreferences,
      getScoreColor: (score: number) => getMoodScoreColor(score, scores),
      getScoreStyle: (score: number) => getMoodScoreStyle(score, scores),
    }),
    [scores, isLoading, refreshPreferences, setPreferences],
  )

  return (
    <MoodPreferencesContext.Provider value={value}>{children}</MoodPreferencesContext.Provider>
  )
}

export function useMoodPreferences(): MoodPreferencesContextValue {
  const context = useContext(MoodPreferencesContext)
  if (!context) {
    throw new Error('useMoodPreferences must be used within MoodPreferencesProvider')
  }
  return context
}
