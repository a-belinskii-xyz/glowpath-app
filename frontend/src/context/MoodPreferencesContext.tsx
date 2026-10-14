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
import { hasAppAccess } from '../lib/authAccess'
import {
  resolveComposerLayout,
  type ResolvedComposerBlock,
} from '../lib/entryComposer'
import { defaultMoodPreferences, getMoodScoreColor, getMoodScoreStyle } from '../lib/moodScale'
import type { MoodPreferencesPublic, MoodScoreStylePublic } from '../types/moodPreferences'

type MoodPreferencesContextValue = {
  scores: Record<string, MoodScoreStylePublic>
  useHistoricalColors: boolean
  showStreak: boolean
  calendarFromStart: boolean
  calendarStartOn: string | null
  firstEntryOn: string | null
  composerLayout: ResolvedComposerBlock[]
  /** Raw saved layout; null when the user has never customized. */
  composerBlocks: MoodPreferencesPublic['composer_blocks']
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
  const [calendarFromStart, setCalendarFromStart] = useState(false)
  const [calendarStartOn, setCalendarStartOn] = useState<string | null>(null)
  const [firstEntryOn, setFirstEntryOn] = useState<string | null>(null)
  const [composerBlocks, setComposerBlocks] = useState<MoodPreferencesPublic['composer_blocks']>(
    null,
  )
  const [isLoading, setIsLoading] = useState(false)

  const applyPreferences = useCallback((preferences: MoodPreferencesPublic) => {
    setScores(preferences.scores)
    setUseHistoricalColors(preferences.use_historical_colors)
    setShowStreak(preferences.show_streak ?? true)
    setCalendarFromStart(preferences.calendar_from_start ?? false)
    setCalendarStartOn(preferences.calendar_start_on ?? null)
    setFirstEntryOn(preferences.first_entry_on ?? null)
    setComposerBlocks(preferences.composer_blocks ?? null)
  }, [])

  const refreshPreferences = useCallback(async () => {
    if (isGuestDiaryMode()) {
      setIsLoading(true)
      try {
        const preferences = await getMoodPreferences()
        applyPreferences(preferences)
      } finally {
        setIsLoading(false)
      }
      return
    }

    if (!hasAppAccess(user)) {
      setScores(defaultMoodPreferences(locale))
      setUseHistoricalColors(true)
      setShowStreak(true)
      setCalendarFromStart(false)
      setCalendarStartOn(null)
      setFirstEntryOn(null)
      setComposerBlocks(null)
      return
    }

    setIsLoading(true)
    try {
      const preferences = await getMoodPreferences()
      applyPreferences(preferences)
    } catch {
      setScores(defaultMoodPreferences(locale))
      setUseHistoricalColors(true)
      setShowStreak(true)
      setCalendarFromStart(false)
      setCalendarStartOn(null)
      setFirstEntryOn(null)
      setComposerBlocks(null)
    } finally {
      setIsLoading(false)
    }
  }, [user, locale, applyPreferences])

  const setPreferences = useCallback(
    (preferences: MoodPreferencesPublic) => {
      applyPreferences(preferences)
    },
    [applyPreferences],
  )

  useEffect(() => {
    if (isGuestDiaryMode()) {
      void refreshPreferences()
      return
    }

    if (!hasAppAccess(user)) {
      setScores(defaultMoodPreferences(locale))
      setUseHistoricalColors(true)
      setShowStreak(true)
      setCalendarFromStart(false)
      setCalendarStartOn(null)
      setFirstEntryOn(null)
      setComposerBlocks(null)
      setIsLoading(false)
      return
    }

    void refreshPreferences()
  }, [user, refreshPreferences, locale])

  const composerLayout = useMemo(
    () => resolveComposerLayout(composerBlocks),
    [composerBlocks],
  )

  const value = useMemo(
    () => ({
      scores,
      useHistoricalColors,
      showStreak,
      calendarFromStart,
      calendarStartOn,
      firstEntryOn,
      composerLayout,
      composerBlocks,
      isLoading,
      refreshPreferences,
      setPreferences,
      getScoreColor: (score: number) => getMoodScoreColor(score, scores),
      getScoreStyle: (score: number) => getMoodScoreStyle(score, scores, locale),
    }),
    [
      scores,
      useHistoricalColors,
      showStreak,
      calendarFromStart,
      calendarStartOn,
      firstEntryOn,
      composerLayout,
      composerBlocks,
      isLoading,
      refreshPreferences,
      setPreferences,
      locale,
    ],
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

/** Swap the mood scale for a subtree (pack preview) without touching saved preferences. */
export function MoodPreferencesOverride({
  scores,
  children,
}: {
  scores: Record<string, MoodScoreStylePublic>
  children: ReactNode
}) {
  const parent = useMoodPreferences()
  const { locale } = useLocale()
  const value = useMemo(
    () => ({
      ...parent,
      scores,
      useHistoricalColors: false,
      getScoreColor: (score: number) => getMoodScoreColor(score, scores),
      getScoreStyle: (score: number) => getMoodScoreStyle(score, scores, locale),
    }),
    [parent, scores, locale],
  )
  return (
    <MoodPreferencesContext.Provider value={value}>{children}</MoodPreferencesContext.Provider>
  )
}
