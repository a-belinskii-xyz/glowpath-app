import { type ChangeEvent, type FormEvent, useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link, useNavigate } from 'react-router-dom'

import { listGoals } from '../api/goals'
import {
  createMoodEntry,
  deleteMoodEntryAttachment,
  patchMoodEntry,
  reorderMoodEntryAttachments,
  uploadMoodEntryAttachment,
} from '../api/moodEntries'
import { listNoteTemplates } from '../api/noteTemplates'
import { listTagGroups } from '../api/tagGroups'
import { PageErrorAlert } from './PageErrorAlert'
import { GoalIcon } from './GoalIcon'
import { AudioRecorder } from './AudioRecorder'
import { AudioIcon, PhotoIcon } from './icons'
import { GuestLockBadge } from './GuestRegistrationLock'
import { MarkdownNoteEditor } from './MarkdownNoteEditor'
import { MoodScoreIcon } from './MoodScoreIcon'
import { PhotoCollageEditor, type CollagePhotoDraft } from './PhotoCollageEditor'
import { SoftAudioPlayer } from './SoftAudioPlayer'
import { StableButtonLabel } from './StableButtonLabel'
import { TagIcon } from './TagIcon'
import { useAuth } from '../context/AuthContext'
import { isGuestDiaryMode } from '../lib/guestMode'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { moodChipStyle, moodGlowBoxShadow, moodGlowFilter, moodSubtleFill } from '../design'
import { useColorScheme } from '../hooks/useColorScheme'
import {
  companionDaypartForHour,
  companionLine,
  companionMoodPhrase,
  type CompanionSlot,
} from '../lib/companion'
import {
  datetimeLocalToIso,
  entriesListPathForInstant,
  formatCalendarDate,
  hourFromDatetimeLocal,
  isoToDatetimeLocal,
  nowDatetimeLocal,
  todayKey,
} from '../lib/datetime'
import { ApiError, formatApiError } from '../lib/errors'
import { randomId } from '../lib/randomId'
import { intlLocale } from '../i18n/t'
import { getMoodScoreOptions } from '../lib/moodScale'
import { emojiForGroupSlug } from '../lib/tagEmoji'
import type { GoalPublic } from '../types/goal'
import type { AttachmentPublic, MoodEntryPublic } from '../types/mood'
import type { AchievementPublic } from '../types/achievement'
import {
  clearMoodEntryDraft,
  getMoodEntryDraft,
  isMoodEntryDraftEmpty,
  setMoodEntryDraft,
} from '../lib/moodEntryDraft'
import { MAX_AUDIO_BYTES } from '../lib/audioRecorder'
import { getStoredMoodEntrySource } from '../lib/moodEntrySource'
import { hapticNotification, hapticSelection, isTelegramMiniApp } from '../platform/telegram'
import { useTelegramMainButton } from '../platform/useTelegramMainButton'
import type { NoteTemplatePublic } from '../types/noteTemplate'
import type { TagGroupPublic, TagPublic } from '../types/tag'

type PendingAudio = File

type PhotoDraftItem =
  | {
      key: string
      source: 'existing'
      attachment: AttachmentPublic
    }
  | {
      key: string
      source: 'pending'
      file: File
      previewUrl: string
    }

type MoodEntryFormProps = {
  mode: 'create' | 'edit'
  initialEntry?: MoodEntryPublic
  /** Prefill `datetime-local` in create mode (e.g. from calendar day). */
  initialRecordedAtLocal?: string
  /** Prefill mood score in create mode (e.g. from empty-state picker). */
  initialScore?: number
}

export function MoodEntryForm({
  mode,
  initialEntry,
  initialRecordedAtLocal,
  initialScore,
}: MoodEntryFormProps) {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { locale, t } = useLocale()
  const { scores } = useMoodPreferences()
  const colorScheme = useColorScheme()
  const timeZone = user?.timezone ?? 'UTC'
  const moodScoreOptions = getMoodScoreOptions(locale, scores)
  const templateSheetTitleId = useId()
  const contextSearchId = useId()
  const frequentTagsHeadingId = useId()
  const noteSectionRef = useRef<HTMLElement>(null)
  const photoPreviewUrlsRef = useRef<Set<string>>(new Set())
  const formRef = useRef<HTMLFormElement>(null)
  const draftHydratedRef = useRef(mode !== 'create')
  const [noteScrollToken, setNoteScrollToken] = useState(0)
  const [draftHydrated, setDraftHydrated] = useState(mode !== 'create')

  const prefilledScore =
    initialEntry?.score ??
    (initialScore != null && moodScoreOptions.some((option) => option.score === initialScore)
      ? initialScore
      : undefined)
  const [score, setScore] = useState(prefilledScore ?? 4)
  const [moodPicked, setMoodPicked] = useState(
    mode === 'edit' || initialEntry != null || prefilledScore != null,
  )
  const [recordedAtLocal, setRecordedAtLocal] = useState(
    initialEntry
      ? isoToDatetimeLocal(initialEntry.recorded_at, timeZone)
      : (initialRecordedAtLocal ?? nowDatetimeLocal(timeZone)),
  )
  const [note, setNote] = useState(initialEntry?.note ?? '')
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>(
    initialEntry?.tags.map((tag) => tag.id) ?? [],
  )
  const [selectedGoalIds, setSelectedGoalIds] = useState<string[]>(
    initialEntry?.goals.map((goal) => goal.id) ?? [],
  )
  const [selectedGoalAmounts, setSelectedGoalAmounts] = useState<Record<string, number>>(() => {
    const amounts: Record<string, number> = {}
    for (const goal of initialEntry?.goals ?? []) {
      if (goal.amount != null) {
        amounts[goal.id] = goal.amount
      }
    }
    return amounts
  })
  const [tagGroups, setTagGroups] = useState<TagGroupPublic[]>([])
  const [frequentTags, setFrequentTags] = useState<TagPublic[]>([])
  const [goals, setGoals] = useState<GoalPublic[]>([])
  const [noteTemplates, setNoteTemplates] = useState<NoteTemplatePublic[]>([])
  const [contextQuery, setContextQuery] = useState('')
  const [showTemplateSheet, setShowTemplateSheet] = useState(false)
  const [photoDrafts, setPhotoDrafts] = useState<PhotoDraftItem[]>(() =>
    (initialEntry?.attachments ?? [])
      .filter((item) => item.kind === 'photo')
      .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
      .map((attachment) => ({
        key: attachment.id,
        source: 'existing' as const,
        attachment,
      })),
  )
  const [existingAudio, setExistingAudio] = useState<AttachmentPublic | null>(
    () => initialEntry?.attachments.find((item) => item.kind === 'audio') ?? null,
  )
  const [pendingAudio, setPendingAudio] = useState<PendingAudio | null>(null)
  const [isRecordingAudio, setIsRecordingAudio] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoadingTags, setIsLoadingTags] = useState(true)
  const [isLoadingGoals, setIsLoadingGoals] = useState(true)

  useEffect(() => {
    const loadCatalog = async () => {
      setIsLoadingTags(true)
      try {
        const [tagsResponse, templatesResponse] = await Promise.all([
          listTagGroups(),
          listNoteTemplates(),
        ])
        setTagGroups(tagsResponse.items)
        setFrequentTags(
          tagsResponse.frequent_tags_enabled ? (tagsResponse.frequent_tags ?? []) : [],
        )
        setNoteTemplates(templatesResponse.items)
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError(t('errors.verifyToManageEntries'))
        } else {
          setError(formatApiError(err, t, 'errors.failedLoadTags'))
        }
      } finally {
        setIsLoadingTags(false)
      }
    }
    void loadCatalog()
  }, [initialEntry, locale, t])

  useEffect(() => {
    const loadGoals = async () => {
      const dateKey = recordedAtLocal.split('T')[0]
      if (!dateKey) {
        return
      }
      setIsLoadingGoals(true)
      try {
        const goalsResponse = await listGoals({ progressOn: dateKey })
        setGoals(goalsResponse.items)
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError(t('errors.verifyToManageEntries'))
        } else {
          setError(formatApiError(err, t, 'errors.failedLoadGoals'))
        }
      } finally {
        setIsLoadingGoals(false)
      }
    }
    void loadGoals()
  }, [recordedAtLocal, locale, t])

  useEffect(() => {
    if (mode !== 'create' || !user?.id || draftHydratedRef.current) {
      return
    }
    draftHydratedRef.current = true
    const dateKey =
      (initialRecordedAtLocal ?? nowDatetimeLocal(timeZone)).split('T')[0] ?? ''
    if (dateKey) {
      const draft = getMoodEntryDraft(user.id, dateKey)
      if (draft) {
        // URL/chart-picked mood wins over a saved draft score.
        if (prefilledScore == null) {
          setScore(draft.score)
          setMoodPicked(draft.moodPicked)
        }
        // Today's drafts keep note/tags/etc., but refresh time to "now".
        setRecordedAtLocal(
          dateKey === todayKey(timeZone)
            ? nowDatetimeLocal(timeZone)
            : draft.recordedAtLocal,
        )
        setNote(draft.note)
        setSelectedTagIds(draft.selectedTagIds)
        setSelectedGoalIds(draft.selectedGoalIds)
        setSelectedGoalAmounts(draft.selectedGoalAmounts)
      }
    }
    setDraftHydrated(true)
  }, [mode, user?.id, initialRecordedAtLocal, timeZone, prefilledScore])

  useEffect(() => {
    if (mode !== 'create' || !user?.id || !draftHydrated) {
      return
    }
    const dateKey = recordedAtLocal.split('T')[0] ?? ''
    if (!dateKey) {
      return
    }
    const draft = {
      score,
      moodPicked,
      recordedAtLocal,
      note,
      selectedTagIds,
      selectedGoalIds,
      selectedGoalAmounts,
    }
    const timer = window.setTimeout(() => {
      if (isMoodEntryDraftEmpty(draft)) {
        clearMoodEntryDraft(user.id, dateKey)
      } else {
        setMoodEntryDraft(user.id, dateKey, draft)
      }
    }, 400)
    return () => window.clearTimeout(timer)
  }, [
    mode,
    user?.id,
    draftHydrated,
    score,
    moodPicked,
    recordedAtLocal,
    note,
    selectedTagIds,
    selectedGoalIds,
    selectedGoalAmounts,
  ])

  useEffect(() => {
    if (!showTemplateSheet) {
      return
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowTemplateSheet(false)
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [showTemplateSheet])

  useEffect(() => {
    if (noteScrollToken === 0) {
      return
    }
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const timer = window.setTimeout(
      () => {
        noteSectionRef.current?.scrollIntoView({
          behavior: prefersReducedMotion ? 'auto' : 'smooth',
          block: 'start',
        })
      },
      prefersReducedMotion ? 0 : 140,
    )
    return () => window.clearTimeout(timer)
  }, [noteScrollToken])

  useEffect(() => {
    const urls = photoPreviewUrlsRef.current
    return () => {
      for (const url of urls) {
        URL.revokeObjectURL(url)
      }
      urls.clear()
    }
  }, [])

  const pendingAudioUrl = useMemo(() => {
    if (!pendingAudio) {
      return null
    }
    return URL.createObjectURL(pendingAudio)
  }, [pendingAudio])

  useEffect(() => {
    return () => {
      if (pendingAudioUrl) {
        URL.revokeObjectURL(pendingAudioUrl)
      }
    }
  }, [pendingAudioUrl])

  const entryDate = recordedAtLocal.split('T')[0] ?? ''
  const isPastEntryDay = Boolean(entryDate) && entryDate < todayKey(timeZone)
  const liveDaypart = companionDaypartForHour(hourFromDatetimeLocal(recordedAtLocal))
  const companionSeed = entryDate || todayKey(timeZone)
  const liveLine = (slot: CompanionSlot) =>
    companionLine(t, slot, liveDaypart, companionSeed)
  const entryDateLabel = useMemo(
    () => (entryDate ? formatCalendarDate(entryDate, intlLocale(locale)) : ''),
    [entryDate, locale],
  )
  const activeGoals = useMemo(
    () =>
      goals.filter(
        (goal) =>
          goal.starts_on <= entryDate && (goal.ends_on === null || goal.ends_on >= entryDate),
      ),
    [goals, entryDate],
  )
  const primaryGoals = activeGoals.filter((goal) => goal.show_on_entry)
  const otherGoals = activeGoals.filter((goal) => !goal.show_on_entry)

  const primaryGroups = useMemo(
    () => tagGroups.filter((group) => group.show_on_entry),
    [tagGroups],
  )
  const otherGroups = useMemo(
    () => tagGroups.filter((group) => !group.show_on_entry),
    [tagGroups],
  )

  const visibleFrequentTags = useMemo(() => {
    const query = contextQuery.trim().toLowerCase()
    if (!query) {
      return frequentTags
    }
    return frequentTags.filter(
      (tag) =>
        tag.label.toLowerCase().includes(query) || tag.slug.toLowerCase().includes(query),
    )
  }, [frequentTags, contextQuery])

  const visiblePrimaryGroups = useMemo(() => {
    const query = contextQuery.trim().toLowerCase()
    return primaryGroups
      .map((group) => ({
        ...group,
        tags: query
          ? group.tags.filter(
              (tag) =>
                tag.label.toLowerCase().includes(query) ||
                tag.slug.toLowerCase().includes(query),
            )
          : group.tags,
      }))
      .filter((group) => group.tags.length > 0)
  }, [primaryGroups, contextQuery])

  const visibleOtherGroups = useMemo(() => {
    const query = contextQuery.trim().toLowerCase()
    return otherGroups
      .map((group) => ({
        ...group,
        tags: query
          ? group.tags.filter(
              (tag) =>
                tag.label.toLowerCase().includes(query) ||
                tag.slug.toLowerCase().includes(query),
            )
          : group.tags,
      }))
      .filter((group) => group.tags.length > 0)
  }, [otherGroups, contextQuery])

  const detailsVisible = moodPicked || mode === 'edit'

  const toggleTag = (tagId: string) => {
    setSelectedTagIds((current) =>
      current.includes(tagId) ? current.filter((id) => id !== tagId) : [...current, tagId],
    )
  }

  const toggleGoal = (goal: GoalPublic) => {
    setSelectedGoalIds((current) => {
      if (current.includes(goal.id)) {
        setSelectedGoalAmounts((amounts) => {
          const next = { ...amounts }
          delete next[goal.id]
          return next
        })
        return current.filter((id) => id !== goal.id)
      }
      if (goal.tracking_kind === 'quantity') {
        const other = otherDayAmountFor(goal)
        const remaining = Math.max(0, (goal.target_amount ?? 0) - other)
        if (remaining > 0) {
          setSelectedGoalAmounts((amounts) => ({ ...amounts, [goal.id]: remaining }))
        }
      }
      return [...current, goal.id]
    })
  }

  const otherDayAmountFor = (goal: GoalPublic) => {
    if (!initialEntry) {
      return goal.day_amount
    }
    const initialDate = isoToDatetimeLocal(initialEntry.recorded_at, timeZone).split('T')[0]
    if (initialDate !== entryDate) {
      return goal.day_amount
    }
    const linked = initialEntry.goals.find((item) => item.id === goal.id)
    const initialAmount = linked?.amount ?? (linked ? 1 : 0)
    return Math.max(0, goal.day_amount - initialAmount)
  }

  const insertTemplate = (template: NoteTemplatePublic) => {
    const templateBody = template.body.trim()
    if (!templateBody) {
      return
    }
    setNote(templateBody)
    setShowTemplateSheet(false)
  }

  const pickMood = (nextScore: number) => {
    setScore(nextScore)
    setMoodPicked(true)
    setNoteScrollToken((token) => token + 1)
    hapticSelection()
  }

  const moodPhrase = (scoreValue: number) =>
    isPastEntryDay
      ? t(`entries.moodPhrasePast.${scoreValue}`)
      : companionMoodPhrase(t, liveDaypart, scoreValue)

  const renderTagChip = (tag: TagPublic) => {
    const selected = selectedTagIds.includes(tag.id)
    const chip = moodChipStyle(tag.color, colorScheme)
    return (
      <button
        key={tag.id}
        type="button"
        className={`tag-chip tag-chip-iconic${selected ? ' tag-chip-selected' : ''}`}
        style={
          selected
            ? {
                background: chip.background,
                borderColor: tag.color,
                color: chip.color,
              }
            : undefined
        }
        onClick={() => toggleTag(tag.id)}
        aria-pressed={selected}
      >
        <TagIcon
          style={{
            color: selected ? chip.color : tag.color,
            icon_type: tag.icon_type,
            icon: tag.icon,
          }}
          className="tag-chip-icon"
        />
        <span className="tag-chip-text">{tag.label}</span>
      </button>
    )
  }

  const renderTagGroup = (group: TagGroupPublic) => {
    const groupEmoji = emojiForGroupSlug(group.slug)
    const labelId = `entry-tag-group-${group.id}`
    return (
      <div
        key={group.id}
        className="entry-context-section"
        role="group"
        aria-labelledby={labelId}
      >
        <p id={labelId} className="entry-context-section-label">
          {groupEmoji ? (
            <span className="entry-context-section-emoji" aria-hidden="true">
              {groupEmoji}
            </span>
          ) : null}
          {group.label}
        </p>
        <div className="tag-chips">{group.tags.map(renderTagChip)}</div>
      </div>
    )
  }

  const renderFrequentTags = () => {
    if (visibleFrequentTags.length === 0) {
      return null
    }
    return (
      <div
        className="entry-context-section entry-context-section-frequent"
        role="group"
        aria-labelledby={frequentTagsHeadingId}
      >
        <p id={frequentTagsHeadingId} className="entry-context-section-label">
          <span className="entry-context-section-emoji" aria-hidden="true">
            ⏱
          </span>
          {t('entries.frequentTagsThisWeek')}
        </p>
        <div className="tag-chips">{visibleFrequentTags.map(renderTagChip)}</div>
      </div>
    )
  }

  const renderGoalChip = (goal: GoalPublic) => {
    const selected = selectedGoalIds.includes(goal.id)
    const isQuantity = goal.tracking_kind === 'quantity'
    const otherAmount = otherDayAmountFor(goal)
    const draftAmount = selected && isQuantity ? (selectedGoalAmounts[goal.id] ?? 0) : 0
    const dayDone = otherAmount + draftAmount
    const dayTarget = goal.target_amount ?? 0
    return (
      <div key={goal.id} className={`goal-chip-wrap${selected ? ' is-selected' : ''}`}>
        <button
          type="button"
          className={`tag-chip goal-chip${selected ? ' tag-chip-selected' : ''}`}
          onClick={() => toggleGoal(goal)}
          aria-pressed={selected}
        >
          <span className="goal-chip-label">
            <GoalIcon
              style={{
                color: goal.color,
                icon_type: goal.icon_type,
                icon: goal.icon,
              }}
              className="goal-chip-icon"
            />
            {goal.label}
          </span>
          <span className="goal-chip-progress">
            {isQuantity
              ? t('goalsPage.dayProgress', {
                  done: dayDone,
                  target: dayTarget,
                })
              : t('goalsPage.weekProgress', {
                  done: goal.completed_this_week,
                  target: goal.times_per_week,
                })}
          </span>
        </button>
        {selected && isQuantity ? (
          <label className="goal-chip-amount">
            <span className="visually-hidden">{t('goalsPage.targetAmount')}</span>
            <input
              className="form-input goal-chip-amount-input"
              type="number"
              min={1}
              max={1000000}
              value={selectedGoalAmounts[goal.id] ?? ''}
              onChange={(event) => {
                const raw = event.target.value
                setSelectedGoalAmounts((current) => {
                  const next = { ...current }
                  if (raw === '') {
                    delete next[goal.id]
                  } else {
                    next[goal.id] = Number(raw)
                  }
                  return next
                })
              }}
            />
            {goal.unit ? <span className="goal-chip-amount-unit">{goal.unit}</span> : null}
          </label>
        ) : null}
      </div>
    )
  }

  const photoCount = photoDrafts.length
  const hasAudio = existingAudio !== null || pendingAudio !== null
  const attachmentsLocked = isGuestDiaryMode()
  const selectedMoodColor = moodScoreOptions.find((option) => option.score === score)?.color

  const collagePhotos: CollagePhotoDraft[] = photoDrafts.map((draft) => {
    if (draft.source === 'existing') {
      return {
        key: draft.key,
        name: draft.attachment.original_name,
        preview: {
          type: 'attachment',
          entryId: initialEntry?.id ?? '',
          attachmentId: draft.attachment.id,
        },
      }
    }
    return {
      key: draft.key,
      name: draft.file.name,
      preview: { type: 'url', url: draft.previewUrl },
    }
  })

  const handlePhotoChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? [])
    if (photoCount + files.length > 5) {
      setError(t('errors.photosLimit'))
      return
    }
    setPhotoDrafts((current) => [
      ...current,
      ...files.map((file) => {
        const previewUrl = URL.createObjectURL(file)
        photoPreviewUrlsRef.current.add(previewUrl)
        return {
          key: randomId(),
          source: 'pending' as const,
          file,
          previewUrl,
        }
      }),
    ])
    event.target.value = ''
  }

  const handleAudioChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }
    if (hasAudio) {
      setError(t('errors.audioLimit'))
      event.target.value = ''
      return
    }
    if (file.size > MAX_AUDIO_BYTES) {
      setError(t('errors.audioTooLarge'))
      event.target.value = ''
      return
    }
    setError(null)
    setPendingAudio(file)
    event.target.value = ''
  }

  const handleRecordedAudio = (file: File) => {
    if (hasAudio) {
      setError(t('errors.audioLimit'))
      return
    }
    setError(null)
    setPendingAudio(file)
  }

  const removePhotoDraft = async (key: string) => {
    const draft = photoDrafts.find((item) => item.key === key)
    if (!draft) {
      return
    }
    if (draft.source === 'pending') {
      URL.revokeObjectURL(draft.previewUrl)
      photoPreviewUrlsRef.current.delete(draft.previewUrl)
      setPhotoDrafts((current) => current.filter((item) => item.key !== key))
      return
    }
    if (!initialEntry) {
      return
    }
    try {
      await deleteMoodEntryAttachment(initialEntry.id, draft.attachment.id)
      setPhotoDrafts((current) => current.filter((item) => item.key !== key))
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedRemoveAttachment'))
    }
  }

  const removeExistingAudio = async () => {
    if (!initialEntry || !existingAudio) {
      return
    }
    try {
      await deleteMoodEntryAttachment(initialEntry.id, existingAudio.id)
      setExistingAudio(null)
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedRemoveAttachment'))
    }
  }

  const syncAttachments = async (entryId: string) => {
    const orderedIds: string[] = []
    for (const draft of photoDrafts) {
      if (draft.source === 'existing') {
        orderedIds.push(draft.attachment.id)
      } else {
        const uploaded = await uploadMoodEntryAttachment(entryId, 'photo', draft.file)
        orderedIds.push(uploaded.id)
      }
    }
    if (mode === 'edit' && orderedIds.length > 0) {
      await reorderMoodEntryAttachments(entryId, orderedIds)
    }
    if (pendingAudio) {
      await uploadMoodEntryAttachment(entryId, 'audio', pendingAudio)
    }
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!moodPicked && mode === 'create') {
      setError(t('entries.pickMoodFirst'))
      return
    }
    setError(null)
    setIsSubmitting(true)

    const activeGoalIdSet = new Set(activeGoals.map((goal) => goal.id))
    const selectedActiveIds = selectedGoalIds.filter((id) => activeGoalIdSet.has(id))
    const goalProgress = selectedActiveIds.flatMap((id) => {
      const goal = activeGoals.find((item) => item.id === id)
      if (!goal || goal.tracking_kind !== 'quantity') {
        return []
      }
      const amount = selectedGoalAmounts[id]
      if (!amount || amount < 1) {
        return []
      }
      return [{ goal_id: id, amount }]
    })
    const missingAmount = selectedActiveIds.some((id) => {
      const goal = activeGoals.find((item) => item.id === id)
      return goal?.tracking_kind === 'quantity' && !(selectedGoalAmounts[id] >= 1)
    })
    if (missingAmount) {
      setError(t('goalsPage.amountRequired'))
      setIsSubmitting(false)
      return
    }
    const sessionSource = mode === 'create' ? getStoredMoodEntrySource() : undefined
    const payload = {
      score,
      recorded_at: datetimeLocalToIso(recordedAtLocal, timeZone),
      note: note.trim() ? note.trim() : null,
      tag_ids: selectedTagIds,
      goal_ids: selectedActiveIds,
      goal_progress: goalProgress,
      ...(sessionSource ? { source: sessionSource } : {}),
    }

        try {
      let savedId = initialEntry?.id
      let unlocked: AchievementPublic[] = []
      if (mode === 'create') {
        const created = await createMoodEntry(payload)
        await syncAttachments(created.id)
        savedId = created.id
        unlocked = created.unlocked_achievements ?? []
        const draftDateKey = recordedAtLocal.split('T')[0]
        if (user?.id && draftDateKey) {
          clearMoodEntryDraft(user.id, draftDateKey)
        }
      } else if (initialEntry) {
        const patched = await patchMoodEntry(initialEntry.id, payload)
        await syncAttachments(initialEntry.id)
        unlocked = patched.unlocked_achievements ?? []
      }
      navigate(entriesListPathForInstant(payload.recorded_at, timeZone, savedId), {
        state: unlocked.length > 0 ? { unlockedAchievements: unlocked } : undefined,
      })
      hapticNotification('success')
    } catch (err) {
      hapticNotification('error')
      if (err instanceof ApiError && err.status === 403) {
        setError(t('errors.verifyToSaveEntries'))
      } else {
        setError(formatApiError(err, t, 'errors.failedSaveEntry'))
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const kindLabel = (kind: string) =>
    kind === 'photo' ? t('entries.kindPhoto') : kind === 'audio' ? t('entries.kindAudio') : kind

  const submitViaMainButton = useCallback(() => {
    formRef.current?.requestSubmit()
  }, [])
  const canSubmit = !isSubmitting && !isRecordingAudio && (moodPicked || mode !== 'create')
  useTelegramMainButton({
    visible: isTelegramMiniApp(),
    text: isSubmitting
      ? t('common.saving')
      : mode === 'create'
        ? t('entries.createEntry')
        : t('entries.saveChanges'),
    enabled: canSubmit,
    progress: isSubmitting,
    onClick: submitViaMainButton,
  })

  return (
    <form ref={formRef} className="form mood-entry-form entry-journey" onSubmit={handleSubmit}>
      <PageErrorAlert error={error} />

      <section className="entry-mood-hero" aria-labelledby="entry-mood-question">
        <div className="entry-when" role="group" aria-label={t('entries.recordedAt')}>
          <label className="entry-when-field">
            <span className="visually-hidden">{t('entries.recordedDate')}</span>
            <input
              className="entry-when-input"
              type="date"
              value={entryDate}
              onChange={(event) => {
                const nextDate = event.target.value
                if (!nextDate) {
                  return
                }
                const timePart = recordedAtLocal.split('T')[1] ?? '20:00'
                setRecordedAtLocal(`${nextDate}T${timePart}`)
              }}
              required
            />
          </label>
          <span className="entry-when-sep" aria-hidden="true">
            ·
          </span>
          <label className="entry-when-field entry-when-field-time">
            <span className="visually-hidden">{t('entries.recordedTime')}</span>
            <input
              className="entry-when-input"
              type="time"
              value={recordedAtLocal.split('T')[1] ?? ''}
              onChange={(event) => {
                const nextTime = event.target.value
                if (!nextTime) {
                  return
                }
                const datePart = recordedAtLocal.split('T')[0] ?? entryDate
                if (!datePart) {
                  return
                }
                setRecordedAtLocal(`${datePart}T${nextTime}`)
              }}
              required
            />
          </label>
        </div>

        {isPastEntryDay ? null : (
          <p className="entry-mood-kicker">{liveLine('kicker')}</p>
        )}
        <h2 id="entry-mood-question" className="entry-mood-question">
          {isPastEntryDay ? t('entries.howAreYouFeelingPast') : liveLine('howAreYou')}
        </h2>

        <div className="mood-picker" role="group" aria-label={t('entries.moodScore')}>
          <div className="mood-picker-options">
            {moodScoreOptions.map((option) => {
              const isSelected = moodPicked && score === option.score
              return (
                <button
                  key={option.score}
                  type="button"
                  className={`mood-picker-option${isSelected ? ' is-selected' : ''}`}
                  style={{
                    ['--mood-picker-color' as string]: option.color,
                    borderColor: isSelected ? option.color : undefined,
                    background: isSelected ? moodSubtleFill(option.color, 'moderate', colorScheme) : undefined,
                    boxShadow: isSelected ? moodGlowBoxShadow(option.color, 'sm', 'moderate', colorScheme) : undefined,
                  }}
                  onClick={() => pickMood(option.score)}
                  aria-pressed={isSelected}
                >
                  <span
                    className="mood-picker-icon-wrap"
                    style={{ filter: moodGlowFilter(option.color) }}
                  >
                    <MoodScoreIcon
                      style={option.style}
                      className="mood-picker-icon"
                      fallbackScore={option.score}
                    />
                  </span>
                  <span className="mood-picker-label">{option.label}</span>
                </button>
              )
            })}
          </div>
          <p className={`mood-picker-caption${!moodPicked ? ' muted' : ''}`}>
            {moodPicked
              ? moodPhrase(score)
              : isPastEntryDay
                ? t('entries.pickMoodHint')
                : liveLine('pickMoodHint')}
          </p>
        </div>
      </section>

      {detailsVisible ? (
        <div className="entry-details-reveal">
          <div className="entry-journey-connector" aria-hidden="true" />

          <section ref={noteSectionRef} className="entry-chapter entry-note-block">
            <MarkdownNoteEditor
              value={note}
              onChange={setNote}
              label={
                isPastEntryDay ? t('entries.whatsOnYourMind') : liveLine('whatsOnYourMind')
              }
              placeholder={
                isPastEntryDay ? t('entries.notePlaceholder') : liveLine('notePlaceholder')
              }
              toolbar="simple"
              toolbarPlacement="after"
              size="large"
              actions={
                <button
                  type="button"
                  className="button button-secondary button-small"
                  onClick={() => setShowTemplateSheet(true)}
                >
                  {t('entries.useTemplate')}
                </button>
              }
            />
          </section>

          <div className="entry-journey-connector" aria-hidden="true" />

          <section className="entry-chapter" aria-labelledby="entry-context-title">
            <h2 id="entry-context-title" className="entry-chapter-title">
              {isPastEntryDay
                ? t('entries.whatHappenedPast', { date: entryDateLabel })
                : liveLine('whatHappened')}
            </h2>
            <p className="entry-chapter-lead muted">
              {isPastEntryDay ? t('entries.contextLeadPast') : liveLine('contextLead')}
            </p>

            {isLoadingTags ? (
              <p className="muted">{t('common.loadingTags')}</p>
            ) : tagGroups.length === 0 ? (
              <p className="muted">{t('entries.noContextTags')}</p>
            ) : (
              <div className="entry-context-search">
                <label className="visually-hidden" htmlFor={contextSearchId}>
                  {t('entries.searchContext')}
                </label>
                <input
                  id={contextSearchId}
                  className="form-input entry-context-search-input"
                  type="search"
                  value={contextQuery}
                  onChange={(event) => setContextQuery(event.target.value)}
                  placeholder={t('entries.searchContextPlaceholder')}
                  autoComplete="off"
                />
                {visibleFrequentTags.length === 0 &&
                visiblePrimaryGroups.length === 0 &&
                visibleOtherGroups.length === 0 ? (
                  <p className="muted entry-context-empty">{t('entries.noContextMatches')}</p>
                ) : (
                  <div className="entry-context-sections">
                    {renderFrequentTags()}
                    {visiblePrimaryGroups.map(renderTagGroup)}
                    {visibleOtherGroups.length > 0 ? (
                      <>
                        <p className="entry-context-more-label muted">{t('entries.other')}</p>
                        {visibleOtherGroups.map(renderTagGroup)}
                      </>
                    ) : null}
                  </div>
                )}
              </div>
            )}
          </section>

          <div className="entry-journey-connector" aria-hidden="true" />

          <section className="entry-chapter" aria-labelledby="entry-goals-title">
            <h2 id="entry-goals-title" className="entry-chapter-title">
              {isPastEntryDay
                ? t('entries.goalsPast', { date: entryDateLabel })
                : liveLine('goals')}
            </h2>
            <p className="entry-chapter-lead muted">{t('entries.goalsLead')}</p>
            {isLoadingGoals ? (
              <p className="muted">{t('common.loadingGoals')}</p>
            ) : activeGoals.length === 0 ? (
              <p className="muted">
                {t('entries.noGoalsForDate')}{' '}
                <Link to="/goals">{t('entries.addGoal')}</Link>
              </p>
            ) : (
              <>
                <div className="tag-chips">{primaryGoals.map(renderGoalChip)}</div>
                {otherGoals.length > 0 ? (
                  <div className="tag-chips tag-chips-secondary">
                    {otherGoals.map(renderGoalChip)}
                  </div>
                ) : null}
              </>
            )}
          </section>

          <div className="entry-journey-connector" aria-hidden="true" />

          <section className="entry-chapter" aria-labelledby="entry-attachments-title">
            <h2 id="entry-attachments-title" className="entry-chapter-title">
              {t('entries.attachments')}
            </h2>
            <div className="attachments-section">
              <div className="attachment-inputs">
                {attachmentsLocked ? (
                  <div
                    className="attachment-upload is-disabled is-guest-locked"
                    role="group"
                    aria-label={t('guest.attachmentsLocked')}
                  >
                    <GuestLockBadge />
                    <span className="attachment-upload-icon" aria-hidden="true">
                      <PhotoIcon />
                    </span>
                    <span className="attachment-upload-body">
                      <span className="attachment-upload-title">
                        {t('entries.photos', { count: 0 })}
                      </span>
                      <span className="attachment-upload-action">{t('entries.addPhotos')}</span>
                      <span className="attachment-upload-hint">{t('entries.photosHint')}</span>
                      <span className="attachment-upload-hint">{t('guest.attachmentsLocked')}</span>
                    </span>
                  </div>
                ) : (
                  <label
                    className={`attachment-upload${photoCount >= 5 ? ' is-disabled' : ''}`}
                  >
                    <span className="attachment-upload-icon" aria-hidden="true">
                      <PhotoIcon />
                    </span>
                    <span className="attachment-upload-body">
                      <span className="attachment-upload-title">
                        {t('entries.photos', { count: photoCount })}
                      </span>
                      <span className="attachment-upload-action">
                        {photoCount >= 5
                          ? t('entries.photosFull')
                          : t('entries.addPhotos')}
                      </span>
                      <span className="attachment-upload-hint">
                        {t('entries.photosHint')}
                      </span>
                    </span>
                    <input
                      className="attachment-upload-input"
                      type="file"
                      accept="image/jpeg,image/png,image/webp,image/gif"
                      multiple
                      onChange={handlePhotoChange}
                      disabled={photoCount >= 5}
                    />
                  </label>
                )}
                <div
                  className={`attachment-upload attachment-audio-card${!attachmentsLocked && hasAudio ? ' is-disabled' : ''}${!attachmentsLocked && isRecordingAudio ? ' is-recording' : ''}${attachmentsLocked ? ' is-disabled is-guest-locked' : ''}`}
                  role={attachmentsLocked ? 'group' : undefined}
                  aria-label={attachmentsLocked ? t('guest.attachmentsLocked') : undefined}
                >
                  {attachmentsLocked ? <GuestLockBadge /> : null}
                  <span className="attachment-upload-icon" aria-hidden="true">
                    <AudioIcon />
                  </span>
                  <span className="attachment-upload-body">
                    <span className="attachment-upload-title">
                      {t('entries.audio', { count: attachmentsLocked ? 0 : hasAudio ? 1 : 0 })}
                    </span>
                    {attachmentsLocked ? (
                      <>
                        <span className="attachment-audio-actions">
                          <span className="button button-small attachment-audio-action" aria-disabled="true">
                            {t('entries.addAudio')}
                          </span>
                          <AudioRecorder disabled onRecorded={() => undefined} onError={setError} />
                        </span>
                        <span className="attachment-upload-hint">{t('entries.audioHint')}</span>
                        <span className="attachment-upload-hint">{t('guest.attachmentsLocked')}</span>
                      </>
                    ) : hasAudio ? (
                      <>
                        <span className="attachment-upload-action">
                          {t('entries.audioFull')}
                        </span>
                        <span className="attachment-upload-hint">
                          {t('entries.audioHint')}
                        </span>
                      </>
                    ) : (
                      <>
                        <span className="attachment-audio-actions">
                          {isRecordingAudio ? null : (
                            <label className="button button-small attachment-audio-action">
                              {t('entries.addAudio')}
                              <input
                                className="visually-hidden"
                                type="file"
                                accept="audio/mpeg,audio/mp4,audio/wav,audio/ogg,audio/webm,audio/aac"
                                onChange={handleAudioChange}
                              />
                            </label>
                          )}
                          <AudioRecorder
                            onRecorded={handleRecordedAudio}
                            onError={setError}
                            onBusyChange={setIsRecordingAudio}
                          />
                        </span>
                        {isRecordingAudio ? null : (
                          <span className="attachment-upload-hint">
                            {t('entries.audioHint')}
                          </span>
                        )}
                      </>
                    )}
                  </span>
                </div>
              </div>

              {!attachmentsLocked ? (
                <>
                  <PhotoCollageEditor
                    photos={collagePhotos}
                    onChange={(next) => {
                      const byKey = new Map(photoDrafts.map((draft) => [draft.key, draft]))
                      setPhotoDrafts(
                        next
                          .map((item) => byKey.get(item.key))
                          .filter((draft): draft is PhotoDraftItem => draft != null),
                      )
                    }}
                    onRemove={(key) => void removePhotoDraft(key)}
                  />

                  {existingAudio || pendingAudio ? (
                    <ul className="attachment-list">
                      {existingAudio ? (
                        <li>
                          <span>
                            {t('entries.attachmentItem', {
                              kind: kindLabel(existingAudio.kind),
                              name: existingAudio.original_name,
                            })}
                          </span>
                          {mode === 'edit' ? (
                            <button
                              type="button"
                              className="link-button"
                              onClick={() => void removeExistingAudio()}
                            >
                              {t('common.remove')}
                            </button>
                          ) : null}
                        </li>
                      ) : null}
                      {pendingAudio ? (
                        <li className="attachment-audio-item">
                          {pendingAudioUrl ? (
                            <SoftAudioPlayer
                              src={pendingAudioUrl}
                              accentColor={selectedMoodColor}
                              title={pendingAudio.name}
                            />
                          ) : (
                            <span>
                              {t('entries.attachmentItem', {
                                kind: t('entries.kindAudio'),
                                name: pendingAudio.name,
                              })}
                            </span>
                          )}
                          <button
                            type="button"
                            className="link-button"
                            onClick={() => setPendingAudio(null)}
                          >
                            {t('common.remove')}
                          </button>
                        </li>
                      ) : null}
                    </ul>
                  ) : null}
                </>
              ) : null}
            </div>
          </section>
        </div>
      ) : null}

      <nav className="entry-configure" aria-label={t('entries.configure')}>
        <Link to="/tags">{t('common.tags')}</Link>
        <span aria-hidden="true">·</span>
        <Link to="/goals">{t('common.goals')}</Link>
        <span aria-hidden="true">·</span>
        <Link to="/tracker-settings?tab=templates">{t('entries.templatesLink')}</Link>
      </nav>

      <div className="entry-form-footer">
        <div className="button-row entry-save-row">
          <button
            className="button"
            type="submit"
            disabled={isSubmitting || isRecordingAudio || (!moodPicked && mode === 'create')}
          >
            <StableButtonLabel
              active={
                isSubmitting
                  ? t('common.saving')
                  : mode === 'create'
                    ? t('entries.createEntry')
                    : t('entries.saveChanges')
              }
              labels={
                mode === 'create'
                  ? [t('entries.createEntry'), t('common.saving')]
                  : [t('entries.saveChanges'), t('common.saving')]
              }
            />
          </button>
          <button
            className="button button-secondary"
            type="button"
            onClick={() =>
              navigate(
                initialEntry
                  ? entriesListPathForInstant(
                      initialEntry.recorded_at,
                      timeZone,
                      initialEntry.id,
                    )
                  : '/',
              )
            }
          >
            {t('common.cancel')}
          </button>
        </div>
      </div>

      {showTemplateSheet
        ? createPortal(
            <div
              className="entry-sheet-backdrop"
              role="presentation"
              onMouseDown={(event) => {
                if (event.target === event.currentTarget) {
                  setShowTemplateSheet(false)
                }
              }}
            >
              <div
                className="entry-sheet"
                role="dialog"
                aria-modal="true"
                aria-labelledby={templateSheetTitleId}
              >
                <div className="entry-sheet-header">
                  <h2 id={templateSheetTitleId}>{t('entries.useTemplate')}</h2>
                  <button
                    type="button"
                    className="button button-secondary button-small"
                    onClick={() => setShowTemplateSheet(false)}
                  >
                    {t('common.cancel')}
                  </button>
                </div>
                {noteTemplates.length > 0 ? (
                  <ul className="entry-sheet-list">
                    {noteTemplates.map((template) => (
                      <li key={template.id}>
                        <button
                          type="button"
                          className="entry-sheet-item"
                          onClick={() => insertTemplate(template)}
                        >
                          {template.label}
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">{t('entries.noTemplates')}</p>
                )}
                  <Link
                  to="/tracker-settings?tab=templates"
                  className="button button-secondary button-small entry-sheet-manage"
                  onClick={() => setShowTemplateSheet(false)}
                >
                  {t('entries.manageTemplates')}
                </Link>
              </div>
            </div>,
            document.body,
          )
        : null}
    </form>
  )
}
