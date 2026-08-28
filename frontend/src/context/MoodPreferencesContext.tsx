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
import { useLocale } from './LocaleContext'
import { isGuestDiaryMode } from '../lib/guestMode'
import { defaultMoodPreferences, getMoodScoreColor, getMoodScoreStyle } from '../lib/moodScale'
import type { MoodPreferencesPublic, MoodScoreStylePublic } from '../types/moodPreferences'

type MoodPreferencesContextValue = {
  scores: Record<string, MoodScoreStylePublic>
  useHistoricalColors: boolean
  showStreak: boolean
  isLoading: boolean
  refreshPreferences: () => Promise<void>
  setPreferences: (preferences: MoodPreferencesPublic) => void
  getScoreColor: (score: number) => string
  getScoreStyle: (score: number) => MoodScoreStylePublic
}

const MoodPreferencesContext = createContext<MoodPreferencesContextValue | null>(null)

export function MoodPreferencesProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const { locale } = useLocale()
  const [scores, setScores] = useState<Record<string, MoodScoreStylePublic>>(() =>
    defaultMoodPreferences(locale),
  )
  const [useHistoricalColors, setUseHistoricalColors] = useState(true)
  const [showStreak, setShowStreak] = useState(true)
  const [isLoading, setIsLoading] = useState(false)

  const refreshPreferences = useCallback(async () => {
    if (isGuestDiaryMode()) {
      setIsLoading(true)
      try {
        const preferences = await getMoodPreferences()
        setScores(preferences.scores)
        setUseHistoricalColors(preferences.use_historical_colors)
        setShowStreak(preferences.show_streak ?? true)
      } finally {
        setIsLoading(false)
      }
      return
    }

    if (!user?.email_verified) {
      setScores(defaultMoodPreferences(locale))
      setUseHistoricalColors(true)
      setShowStreak(true)
      return
    }

    setIsLoading(true)
    try {
      const preferences = await getMoodPreferences()
      setScores(preferences.scores)
      setUseHistoricalColors(preferences.use_historical_colors)
      setShowStreak(preferences.show_streak ?? true)
    } catch {
      setScores(defaultMoodPreferences(locale))
      setUseHistoricalColors(true)
      setShowStreak(true)
    } finally {
      setIsLoading(false)
    }
  }, [user?.email_verified, locale])

  const setPreferences = useCallback((preferences: MoodPreferencesPublic) => {
    setScores(preferences.scores)
    setUseHistoricalColors(preferences.use_historical_colors)
    setShowStreak(preferences.show_streak ?? true)
  }, [])

  useEffect(() => {
    if (isGuestDiaryMode()) {
      void refreshPreferences()
      return
    }

    if (!user?.email_verified) {
      setScores(defaultMoodPreferences(locale))
      setUseHistoricalColors(true)
      setShowStreak(true)
      setIsLoading(false)
      return
    }

    void refreshPreferences()
  }, [user?.email_verified, refreshPreferences, locale])

  const value = useMemo(
    () => ({
      scores,
      useHistoricalColors,
      showStreak,
      isLoading,
      refreshPreferences,
      setPreferences,
      getScoreColor: (score: number) => getMoodScoreColor(score, scores),
      getScoreStyle: (score: number) => getMoodScoreStyle(score, scores, locale),
    }),
    [scores, useHistoricalColors, showStreak, isLoading, refreshPreferences, setPreferences, locale],
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
