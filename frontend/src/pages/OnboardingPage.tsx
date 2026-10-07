import { useCallback, useEffect, useMemo, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'

import {
  completeOnboarding,
  getOnboardingCatalog,
  getOnboardingSuggestions,
} from '../api/onboarding'
import { MarkdownNote } from '../components/MarkdownNote'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { StableButtonLabel } from '../components/StableButtonLabel'
import { useAuth } from '../context/AuthContext'
import { useGuestExperiment } from '../context/GuestExperimentContext'
import { useLocale } from '../context/LocaleContext'
import { isGuestDiaryMode } from '../lib/guestMode'
import { formatApiError } from '../lib/errors'
import { hapticSelection, isTelegramMiniApp } from '../platform/telegram'
import { useTelegramMainButton } from '../platform/useTelegramMainButton'
import type {
  OnboardingQuestion,
  OnboardingSuggestions,
} from '../types/onboarding'

type Phase = 'questions' | 'suggestions'

export function OnboardingPage() {
  const { user, refreshUser } = useAuth()
  const { guestOnboardingCompleted, refreshGuestMeta } = useGuestExperiment()
  const { locale, t } = useLocale()
  const navigate = useNavigate()
  const [questions, setQuestions] = useState<OnboardingQuestion[]>([])
  const [phase, setPhase] = useState<Phase>('questions')
  const [stepIndex, setStepIndex] = useState(0)
  const [selected, setSelected] = useState<Record<string, string[]>>({})
  const [suggestions, setSuggestions] = useState<OnboardingSuggestions | null>(null)
  const [selectedGroupSlugs, setSelectedGroupSlugs] = useState<string[]>([])
  const [selectedTemplateSlugs, setSelectedTemplateSlugs] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const optionKeys = useMemo(() => Object.values(selected).flat(), [selected])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const catalog = await getOnboardingCatalog()
        if (!cancelled) {
          setQuestions(catalog.questions)
        }
      } catch (err) {
        if (!cancelled) {
          setError(formatApiError(err, t, 'errors.requestFailed'))
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [locale, t])

  useEffect(() => {
    if (phase !== 'suggestions') {
      return
    }
    let cancelled = false
    const reload = async () => {
      setIsLoadingSuggestions(true)
      setError(null)
      try {
        const payload = await getOnboardingSuggestions(optionKeys)
        if (cancelled) {
          return
        }
        setSuggestions(payload)
        const groupSlugs = new Set(payload.tag_groups.map((group) => group.slug))
        const templateSlugs = new Set(payload.note_templates.map((item) => item.slug))
        setSelectedGroupSlugs((prev) => prev.filter((slug) => groupSlugs.has(slug)))
        setSelectedTemplateSlugs((prev) => prev.filter((slug) => templateSlugs.has(slug)))
      } catch (err) {
        if (!cancelled) {
          setError(formatApiError(err, t, 'errors.requestFailed'))
        }
      } finally {
        if (!cancelled) {
          setIsLoadingSuggestions(false)
        }
      }
    }
    void reload()
    return () => {
      cancelled = true
    }
  }, [locale, phase, optionKeys, t])

  const current = questions[stepIndex] ?? null
  const currentSelected = current ? (selected[current.block_id] ?? []) : []
  const isLastQuestion = stepIndex >= questions.length - 1 && questions.length > 0
  const questionStepTotal = questions.length + 1
  const currentHasAnswer = currentSelected.length > 0

  const selectedCountLabel = useMemo(() => {
    if (!current) {
      return ''
    }
    return t('onboarding.selectedCount', {
      count: String(currentSelected.length),
      max: String(current.max_selections),
    })
  }, [current, currentSelected.length, t])

  const ensureCurrentAnswer = useCallback((): boolean => {
    if (currentHasAnswer) {
      return true
    }
    setError(t('onboarding.selectAtLeastOne'))
    return false
  }, [currentHasAnswer, t])

  const goNextQuestion = useCallback(() => {
    if (!ensureCurrentAnswer()) {
      return
    }
    setStepIndex((value) => value + 1)
  }, [ensureCurrentAnswer])

  const goToSuggestions = useCallback(() => {
    if (!ensureCurrentAnswer()) {
      return
    }
    const unanswered = questions.find((question) => (selected[question.block_id] ?? []).length === 0)
    if (unanswered) {
      const unansweredIndex = questions.findIndex(
        (question) => question.block_id === unanswered.block_id,
      )
      setStepIndex(Math.max(0, unansweredIndex))
      setError(t('onboarding.selectAtLeastOne'))
      return
    }
    setSelectedGroupSlugs([])
    setSelectedTemplateSlugs([])
    setSuggestions(null)
    setPhase('suggestions')
  }, [ensureCurrentAnswer, questions, selected, t])

  const finish = useCallback(
    async (skip: boolean) => {
      setIsSubmitting(true)
      setError(null)
      try {
        await completeOnboarding(
          skip
            ? { skip: true, option_keys: [], tag_group_slugs: [], note_template_slugs: [] }
            : {
                skip: false,
                option_keys: optionKeys,
                tag_group_slugs: selectedGroupSlugs,
                note_template_slugs: selectedTemplateSlugs,
              },
        )
        if (isGuestDiaryMode()) {
          await refreshGuestMeta()
        } else {
          await refreshUser()
        }
        navigate('/', { replace: true })
      } catch (err) {
        setError(formatApiError(err, t, 'errors.requestFailed'))
      } finally {
        setIsSubmitting(false)
      }
    },
    [
      navigate,
      optionKeys,
      refreshGuestMeta,
      refreshUser,
      selectedGroupSlugs,
      selectedTemplateSlugs,
      t,
    ],
  )

  const onMainButton = useCallback(() => {
    if (phase === 'suggestions') {
      void finish(false)
      return
    }
    if (isLastQuestion) {
      goToSuggestions()
      return
    }
    goNextQuestion()
  }, [finish, goNextQuestion, goToSuggestions, isLastQuestion, phase])

  const mainButtonVisible =
    isTelegramMiniApp() &&
    !isLoading &&
    !user?.onboarding_completed &&
    !(isGuestDiaryMode() && guestOnboardingCompleted) &&
    ((phase === 'questions' && Boolean(current)) || phase === 'suggestions')
  const mainButtonEnabled =
    !isSubmitting &&
    !isLoadingSuggestions &&
    (phase === 'suggestions' ? Boolean(suggestions) : currentHasAnswer)
  const mainButtonText =
    phase === 'suggestions'
      ? isSubmitting
        ? t('onboarding.finishing')
        : t('onboarding.finish')
      : isLastQuestion && isLoadingSuggestions
        ? t('common.loading')
        : t('common.next')

  useTelegramMainButton({
    visible: mainButtonVisible,
    text: mainButtonText,
    enabled: mainButtonEnabled,
    progress: isSubmitting || (phase === 'questions' && isLastQuestion && isLoadingSuggestions),
    onClick: onMainButton,
  })

  if (user?.onboarding_completed || (isGuestDiaryMode() && guestOnboardingCompleted)) {
    return <Navigate to="/" replace />
  }

  const toggleOption = (blockId: string, key: string, maxSelections: number) => {
    setError(null)
    setSelected((prev) => {
      const currentKeys = prev[blockId] ?? []
      if (currentKeys.includes(key)) {
        hapticSelection()
        return { ...prev, [blockId]: currentKeys.filter((item) => item !== key) }
      }
      if (currentKeys.length >= maxSelections) {
        return prev
      }
      hapticSelection()
      return { ...prev, [blockId]: [...currentKeys, key] }
    })
  }

  const toggleSlug = (
    slug: string,
    selectedSlugs: string[],
    setSelectedSlugs: (next: string[]) => void,
  ) => {
    hapticSelection()
    setSelectedSlugs(
      selectedSlugs.includes(slug)
        ? selectedSlugs.filter((item) => item !== slug)
        : [...selectedSlugs, slug],
    )
  }

  const suggestionCount =
    (suggestions?.tag_groups.length ?? 0) + (suggestions?.note_templates.length ?? 0)
  const selectedSuggestionCount = selectedGroupSlugs.length + selectedTemplateSlugs.length

  return (
    <section className="page narrow onboarding-page">
      <div className="onboarding-page-body">
        <h1>{t('onboarding.title')}</h1>
        <p className="muted">
          {phase === 'suggestions' ? t('onboarding.suggestionsSubtitle') : t('onboarding.subtitle')}
        </p>

        <PageErrorAlert error={error} />

        {isLoading ? <p className="muted">{t('common.loading')}</p> : null}

        {!isLoading && phase === 'suggestions' && (isLoadingSuggestions || !suggestions) ? (
          <p className="muted">{t('common.loading')}</p>
        ) : null}

        {!isLoading && phase === 'questions' && current ? (
          <div className="onboarding-step">
            <div className="onboarding-step-meta">
              <p className="onboarding-progress">
                {t('onboarding.step', {
                  current: String(stepIndex + 1),
                  total: String(questionStepTotal),
                })}
              </p>
              <p className="muted">{selectedCountLabel}</p>
            </div>

            <h2 className="onboarding-question">{current.title}</h2>
            <p
              className={`onboarding-required-hint${currentHasAnswer ? ' is-satisfied' : ''}`}
              aria-hidden={currentHasAnswer}
            >
              {t('onboarding.selectAtLeastOne')}
            </p>

            <div className="onboarding-options" role="group" aria-label={current.title}>
              {current.options.map((option) => {
                const isActive = currentSelected.includes(option.key)
                const atLimit = !isActive && currentSelected.length >= current.max_selections
                return (
                  <button
                    key={option.key}
                    type="button"
                    className={`button button-secondary onboarding-option${isActive ? ' is-active' : ''}`}
                    aria-pressed={isActive}
                    disabled={isSubmitting || isLoadingSuggestions || atLimit}
                    onClick={() => toggleOption(current.block_id, option.key, current.max_selections)}
                  >
                    {option.label}
                  </button>
                )
              })}
            </div>
          </div>
        ) : null}

        {!isLoading && phase === 'suggestions' && suggestions ? (
          <div className="onboarding-step">
            <div className="onboarding-step-meta">
              <p className="onboarding-progress">
                {t('onboarding.step', {
                  current: String(questionStepTotal),
                  total: String(questionStepTotal),
                })}
              </p>
              <p className="muted">
                {t('onboarding.suggestionsSelected', {
                  count: String(selectedSuggestionCount),
                  total: String(suggestionCount),
                })}
              </p>
            </div>

            <h2 className="onboarding-question">{t('onboarding.suggestionsTitle')}</h2>

            {suggestionCount === 0 ? (
              <p className="muted">{t('onboarding.suggestionsEmpty')}</p>
            ) : null}

            {suggestions.tag_groups.length > 0 ? (
              <div className="onboarding-suggestions-section">
                <div className="onboarding-suggestions-header">
                  <h3>{t('onboarding.tagGroupsSection')}</h3>
                  <button
                    type="button"
                    className="button button-secondary"
                    disabled={isSubmitting}
                    onClick={() =>
                      setSelectedGroupSlugs(
                        selectedGroupSlugs.length === suggestions.tag_groups.length
                          ? []
                          : suggestions.tag_groups.map((group) => group.slug),
                      )
                    }
                  >
                    <StableButtonLabel
                      active={
                        selectedGroupSlugs.length === suggestions.tag_groups.length
                          ? t('onboarding.deselectAll')
                          : t('onboarding.selectAll')
                      }
                      labels={[t('onboarding.selectAll'), t('onboarding.deselectAll')]}
                    />
                  </button>
                </div>
                <div className="onboarding-suggestion-list">
                  {suggestions.tag_groups.map((group) => {
                    const isActive = selectedGroupSlugs.includes(group.slug)
                    return (
                      <button
                        key={group.slug}
                        type="button"
                        className={`onboarding-suggestion-card${isActive ? ' is-active' : ''}`}
                        aria-pressed={isActive}
                        disabled={isSubmitting}
                        onClick={() =>
                          toggleSlug(group.slug, selectedGroupSlugs, setSelectedGroupSlugs)
                        }
                      >
                        <span className="onboarding-suggestion-title">{group.label}</span>
                        <span className="onboarding-suggestion-tags">
                          {group.tags.map((tag) => (
                            <span key={tag.slug} className="onboarding-suggestion-tag">
                              <span aria-hidden="true">{tag.icon}</span> {tag.label}
                            </span>
                          ))}
                        </span>
                      </button>
                    )
                  })}
                </div>
              </div>
            ) : null}

            {suggestions.note_templates.length > 0 ? (
              <div className="onboarding-suggestions-section">
                <div className="onboarding-suggestions-header">
                  <h3>{t('onboarding.templatesSection')}</h3>
                  <button
                    type="button"
                    className="button button-secondary"
                    disabled={isSubmitting}
                    onClick={() =>
                      setSelectedTemplateSlugs(
                        selectedTemplateSlugs.length === suggestions.note_templates.length
                          ? []
                          : suggestions.note_templates.map((template) => template.slug),
                      )
                    }
                  >
                    <StableButtonLabel
                      active={
                        selectedTemplateSlugs.length === suggestions.note_templates.length
                          ? t('onboarding.deselectAll')
                          : t('onboarding.selectAll')
                      }
                      labels={[t('onboarding.selectAll'), t('onboarding.deselectAll')]}
                    />
                  </button>
                </div>
                <div className="onboarding-suggestion-list">
                  {suggestions.note_templates.map((template) => {
                    const isActive = selectedTemplateSlugs.includes(template.slug)
                    return (
                      <button
                        key={template.slug}
                        type="button"
                        className={`onboarding-suggestion-card${isActive ? ' is-active' : ''}`}
                        aria-pressed={isActive}
                        disabled={isSubmitting}
                        onClick={() =>
                          toggleSlug(template.slug, selectedTemplateSlugs, setSelectedTemplateSlugs)
                        }
                      >
                        <span className="onboarding-suggestion-title">{template.label}</span>
                        <MarkdownNote
                          content={template.body}
                          compact
                          className="onboarding-template-preview"
                        />
                      </button>
                    )
                  })}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      {!isLoading ? (
        <div className="onboarding-sticky-bar">
          <div className="onboarding-sticky-actions">
            {phase === 'questions' && current ? (
              <div className="button-row onboarding-actions">
                <button
                  type="button"
                  className="button button-secondary"
                  disabled={stepIndex === 0 || isSubmitting || isLoadingSuggestions}
                  onClick={() => setStepIndex((value) => Math.max(0, value - 1))}
                >
                  {t('common.previous')}
                </button>

                <button
                  type="button"
                  className="button"
                  disabled={isSubmitting || isLoadingSuggestions || !currentHasAnswer}
                  onClick={() => (isLastQuestion ? goToSuggestions() : goNextQuestion())}
                >
                  <StableButtonLabel
                    active={
                      isLastQuestion && isLoadingSuggestions
                        ? t('common.loading')
                        : t('common.next')
                    }
                    labels={[t('common.next'), t('common.loading')]}
                  />
                </button>
              </div>
            ) : null}

            {phase === 'suggestions' ? (
              <div className="button-row onboarding-actions">
                <button
                  type="button"
                  className="button button-secondary"
                  disabled={isSubmitting || isLoadingSuggestions}
                  onClick={() => setPhase('questions')}
                >
                  {t('common.previous')}
                </button>
                <button
                  type="button"
                  className="button"
                  disabled={isSubmitting || isLoadingSuggestions || !suggestions}
                  onClick={() => void finish(false)}
                >
                  <StableButtonLabel
                    active={
                      isSubmitting ? t('onboarding.finishing') : t('onboarding.finish')
                    }
                    labels={[t('onboarding.finish'), t('onboarding.finishing')]}
                  />
                </button>
              </div>
            ) : null}

            {phase === 'questions' ? (
              <>
                <button
                  type="button"
                  className="button button-secondary button-block onboarding-skip"
                  disabled={isSubmitting}
                  onClick={() => void finish(true)}
                >
                  {t('onboarding.skip')}
                </button>
                <p className="muted onboarding-skip-hint">{t('onboarding.skipHint')}</p>
              </>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  )
}
