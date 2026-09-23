import type { ApiLocale } from './locale'
import type { MoodScoreStylePublic } from '../types/moodPreferences'

export type MoodScoreOption = {
  score: number
  label: string
  emoji: string
  color: string
  style: MoodScoreStylePublic
}

type MoodScoreLabels = Record<ApiLocale, string>

const MOOD_SCORE_META: { score: number; labels: MoodScoreLabels; emoji: string }[] = [
  { score: 1, labels: { en: 'awful', ru: 'ужасно' }, emoji: '😢' },
  { score: 2, labels: { en: 'bad', ru: 'плохо' }, emoji: '😞' },
  { score: 3, labels: { en: 'neutral', ru: 'нейтрально' }, emoji: '😐' },
  { score: 4, labels: { en: 'good', ru: 'хорошо' }, emoji: '🙂' },
  { score: 5, labels: { en: 'great', ru: 'отлично' }, emoji: '😄' },
]

export const DEFAULT_MOOD_SCORE_COLORS: Record<number, string> = {
  1: '#64748b',
  2: '#94a3b8',
  3: '#60a5fa',
  4: '#34d399',
  5: '#f59e0b',
}

export const MAX_MOOD_SCORE_LABEL_LENGTH = 40

export function defaultMoodScoreLabel(score: number, locale: ApiLocale): string {
  const meta = MOOD_SCORE_META.find((item) => item.score === score)
  if (!meta) {
    return String(score)
  }
  return meta.labels[locale] ?? meta.labels.en
}

export function defaultMoodScoreStyle(
  score: number,
  locale: ApiLocale = 'en',
): MoodScoreStylePublic {
  return {
    color: DEFAULT_MOOD_SCORE_COLORS[score] ?? '#94a3b8',
    icon_type: 'emoji',
    icon: MOOD_SCORE_META.find((item) => item.score === score)?.emoji ?? '😐',
    label: defaultMoodScoreLabel(score, locale),
  }
}

export function defaultMoodPreferences(
  locale: ApiLocale = 'en',
): Record<string, MoodScoreStylePublic> {
  return Object.fromEntries(
    MOOD_SCORE_META.map(({ score }) => [String(score), defaultMoodScoreStyle(score, locale)]),
  )
}

export function resolveMoodPreferences(
  scores?: Record<string, MoodScoreStylePublic> | null,
  locale: ApiLocale = 'en',
): Record<string, MoodScoreStylePublic> {
  const defaults = defaultMoodPreferences(locale)
  if (!scores) {
    return defaults
  }
  return Object.fromEntries(
    MOOD_SCORE_META.map(({ score }) => {
      const key = String(score)
      return [key, { ...defaults[key], ...scores[key] }]
    }),
  )
}

export function getMoodScoreColor(
  score: number,
  preferences?: Record<string, MoodScoreStylePublic> | null,
): string {
  return (
    resolveMoodPreferences(preferences)[String(score)]?.color ??
    DEFAULT_MOOD_SCORE_COLORS[score] ??
    '#94a3b8'
  )
}

export function getMoodScoreStyle(
  score: number,
  preferences?: Record<string, MoodScoreStylePublic> | null,
  locale: ApiLocale = 'en',
): MoodScoreStylePublic {
  return resolveMoodPreferences(preferences, locale)[String(score)] ?? defaultMoodScoreStyle(score, locale)
}

export function entryMoodColor(
  entry: { score: number; score_color?: string | null },
  preferences?: Record<string, MoodScoreStylePublic> | null,
): string {
  return entry.score_color || getMoodScoreColor(entry.score, preferences)
}

export function entryMoodStyle(
  entry: { score: number; score_color?: string | null },
  preferences?: Record<string, MoodScoreStylePublic> | null,
  locale: ApiLocale = 'en',
): MoodScoreStylePublic {
  const style = getMoodScoreStyle(entry.score, preferences, locale)
  return entry.score_color ? { ...style, color: entry.score_color } : style
}

export function getMoodScoreOptions(
  locale: ApiLocale,
  preferences?: Record<string, MoodScoreStylePublic> | null,
): MoodScoreOption[] {
  const resolved = resolveMoodPreferences(preferences, locale)
  return MOOD_SCORE_META.map(({ score, labels, emoji }) => {
    const style = resolved[String(score)] ?? defaultMoodScoreStyle(score, locale)
    return {
      score,
      label: style.label || labels[locale] || labels.en,
      emoji: style.icon_type === 'emoji' ? style.icon : emoji,
      color: style.color,
      style,
    }
  })
}

export function isValidHexColor(value: string): boolean {
  return /^#[0-9A-Fa-f]{6}$/.test(value)
}
