import { type FormEvent, useEffect, useState } from 'react'

import { patchMoodPreferences } from '../api/moodPreferences'
import { Alert } from './Alert'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { ApiError } from '../lib/errors'
import {
  DEFAULT_MOOD_SCORE_COLORS,
  getMoodScoreOptions,
  isValidHexColor,
} from '../lib/moodScale'
import type { MoodPreferencesPublic } from '../types/moodPreferences'

export function MoodPreferencesForm() {
  const { locale, t } = useLocale()
  const { scores, isLoading, refreshPreferences, setPreferences } = useMoodPreferences()
  const moodScoreOptions = getMoodScoreOptions(locale, scores)

  const [draftColors, setDraftColors] = useState<Record<number, string>>({})
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    setDraftColors(
      Object.fromEntries(
        Object.entries(scores).map(([score, style]) => [Number(score), style.color]),
      ),
    )
  }, [scores])

  const applyPreferences = (preferences: MoodPreferencesPublic) => {
    setPreferences(preferences)
    setDraftColors(
      Object.fromEntries(
        Object.entries(preferences.scores).map(([score, style]) => [Number(score), style.color]),
      ),
    )
  }

  const handleColorChange = (score: number, value: string) => {
    setDraftColors((current) => ({ ...current, [score]: value }))
  }

  const handleResetScore = (score: number) => {
    setDraftColors((current) => ({
      ...current,
      [score]: DEFAULT_MOOD_SCORE_COLORS[score] ?? '#94a3b8',
    }))
  }

  const handleResetAll = () => {
    setDraftColors({ ...DEFAULT_MOOD_SCORE_COLORS })
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSuccess(null)

    for (const option of moodScoreOptions) {
      const color = draftColors[option.score]
      if (!color || !isValidHexColor(color)) {
        setError(t('moodPreferences.invalidColor', { label: option.label }))
        return
      }
    }

    setIsSaving(true)
    setError(null)
    try {
      const saved = await patchMoodPreferences({
        scores: Object.fromEntries(
          moodScoreOptions.map((option) => [
            String(option.score),
            { color: draftColors[option.score] },
          ]),
        ),
      })
      applyPreferences(saved)
      setSuccess(t('moodPreferences.saved'))
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError(t('errors.verifyToManageMoodPreferences'))
      } else {
        setError(err instanceof Error ? err.message : t('errors.failedSave'))
      }
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return <p className="muted">{t('common.loadingMoodPreferences')}</p>
  }

  return (
    <form className="card form mood-preferences-form" onSubmit={(e) => void handleSubmit(e)}>
      {error ? <Alert variant="error">{error}</Alert> : null}
      {success ? <Alert variant="success">{success}</Alert> : null}

      <div className="mood-preferences-grid">
        {moodScoreOptions.map((option) => (
          <div key={option.score} className="mood-preferences-row">
            <div className="mood-preferences-preview">
              <span
                className="mood-preferences-swatch"
                style={{ backgroundColor: draftColors[option.score] ?? option.color }}
                aria-hidden
              />
              <span className="mood-preferences-emoji" aria-hidden>
                {option.emoji}
              </span>
              <span className="mood-preferences-label">{option.label}</span>
            </div>
            <div className="mood-preferences-controls">
              <input
                className="mood-preferences-color-input"
                type="color"
                value={draftColors[option.score] ?? option.color}
                onChange={(event) => handleColorChange(option.score, event.target.value)}
                aria-label={t('moodPreferences.colorFor', { label: option.label })}
              />
              <input
                className="form-input mood-preferences-hex-input"
                type="text"
                value={draftColors[option.score] ?? option.color}
                onChange={(event) => handleColorChange(option.score, event.target.value)}
                pattern="^#[0-9A-Fa-f]{6}$"
                spellCheck={false}
                aria-label={t('moodPreferences.hexFor', { label: option.label })}
              />
              <button
                type="button"
                className="button button-secondary button-small"
                onClick={() => handleResetScore(option.score)}
              >
                {t('moodPreferences.resetScore')}
              </button>
            </div>
          </div>
        ))}
      </div>

      <p className="form-hint">{t('moodPreferences.lead')}</p>

      <div className="button-row">
        <button type="button" className="button button-secondary" onClick={handleResetAll}>
          {t('moodPreferences.resetAll')}
        </button>
        <button type="button" className="button button-secondary" onClick={() => void refreshPreferences()}>
          {t('common.refresh')}
        </button>
        <button type="submit" className="button" disabled={isSaving}>
          {isSaving ? t('common.saving') : t('moodPreferences.save')}
        </button>
      </div>
    </form>
  )
}
