import { type ChangeEvent, useCallback, useEffect, useRef, useState } from 'react'

import {
  deleteMoodIcon,
  fetchMoodIconBlob,
  fetchMoodIconSourceBlob,
  getMoodIcons,
  patchMoodPreferences,
  uploadMoodIcon,
  type MoodIconMeta,
} from '../api/moodPreferences'
import { Alert } from './Alert'
import { PageErrorAlert } from './PageErrorAlert'
import { ColorPicker } from './ColorPicker'
import { ConfirmDialog } from './ConfirmDialog'
import { EditorDrawer } from './EditorDrawer'
import { EmojiPicker } from './EmojiPicker'
import { IconButton } from './IconButton'
import { EditIcon } from './icons'
import { ImageCropModal } from './ImageCropModal'
import { CatalogIconPicker } from './CatalogIconPicker'
import { MoodScoreIcon } from './MoodScoreIcon'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { moodGlowFilter } from '../design'
import { ApiError, formatApiError } from '../lib/errors'
import {
  blobToNamedFile,
  readMoodIconBlobForCrop,
  readMoodIconImage,
  type CropValidationError,
} from '../lib/imageCrop'
import { MOOD_EMOJI_GROUPS } from '../lib/emojiPalette'
import { revokeMoodIconObjectUrl } from '../lib/moodIconBlobUrl'
import {
  DEFAULT_MOOD_SCORE_COLORS,
  MAX_MOOD_SCORE_LABEL_LENGTH,
  defaultMoodScoreLabel,
  defaultMoodScoreStyle,
  getMoodScoreOptions,
  isValidHexColor,
} from '../lib/moodScale'
import type { MoodPreferencesPublic, MoodScoreIconType, MoodScoreStylePublic } from '../types/moodPreferences'

type PendingCrop = {
  score: number
  image: HTMLImageElement
  objectUrl: string
  fileName: string
  /** Original image used for cropping; uploaded alongside the cropped display icon. */
  sourceFile: File
  /** When set, Save replaces this icon instead of adding a new one. */
  replaceIconId?: string
}

type PendingConfirm =
  | { kind: 'reset-score'; score: number; label: string }
  | { kind: 'reset-all' }
  | { kind: 'remove-icon'; score: number; iconId: string }

type IconSourceUi = 'emoji' | 'upload' | 'catalog'

const MAX_UPLOADS_PER_SCORE = 3
const APPEARANCE_SAVE_DELAY_MS = 400

type AppearancePatch = { color?: string; label?: string }

function groupIconsByScore(items: MoodIconMeta[]): Record<number, MoodIconMeta[]> {
  const grouped: Record<number, MoodIconMeta[]> = {}
  for (const item of items) {
    const list = grouped[item.score] ?? []
    list.push(item)
    grouped[item.score] = list
  }
  return grouped
}

function resolveIconSourceUi(iconType: MoodScoreIconType): IconSourceUi {
  if (iconType === 'upload') {
    return 'upload'
  }
  if (iconType === 'catalog') {
    return 'catalog'
  }
  return 'emoji'
}

export function MoodPreferencesForm() {
  const { locale, t } = useLocale()
  const { user } = useAuth()
  const { scores, isLoading, refreshPreferences, setPreferences } = useMoodPreferences()
  const marketplaceEnabled = Boolean(user?.features?.icon_marketplace)
  const moodScoreOptions = getMoodScoreOptions(locale, scores)

  const [draftColors, setDraftColors] = useState<Record<number, string>>({})
  const [draftLabels, setDraftLabels] = useState<Record<number, string>>({})
  const [draftEmojis, setDraftEmojis] = useState<Record<number, string>>({})
  const [uploadedIcons, setUploadedIcons] = useState<Record<number, MoodIconMeta[]>>({})
  const [maxUploadsPerScore, setMaxUploadsPerScore] = useState(MAX_UPLOADS_PER_SCORE)
  const [sourceUiByScore, setSourceUiByScore] = useState<Record<number, IconSourceUi>>({})
  const [isSaving, setIsSaving] = useState(false)
  const [iconBusyScore, setIconBusyScore] = useState<number | null>(null)
  const [pendingCrop, setPendingCrop] = useState<PendingCrop | null>(null)
  const [pendingConfirm, setPendingConfirm] = useState<PendingConfirm | null>(null)
  const [isCropSaving, setIsCropSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [editingScore, setEditingScore] = useState<number | null>(null)

  const cropValidationMessage = (reason: CropValidationError): string => {
    if (reason === 'tooSmall') {
      return t('moodPreferences.imageTooSmall')
    }
    if (reason === 'loadFailed') {
      return t('moodPreferences.imageLoadFailed')
    }
    if (reason === 'size') {
      return t('moodPreferences.imageTooLarge')
    }
    return t('moodPreferences.uploadFailed')
  }

  const draftColorsRef = useRef<Record<number, string>>({})
  const draftLabelsRef = useRef<Record<number, string>>({})
  const scoresRef = useRef(scores)
  const localeRef = useRef(locale)
  const skipDraftSyncRef = useRef(false)
  const saveTimerRef = useRef<number | null>(null)
  const pendingScoresRef = useRef(new Set<number>())
  const persistChainRef = useRef(Promise.resolve())
  const persistPendingScoresRef = useRef<() => Promise<void>>(async () => {})
  const persistGenerationRef = useRef<Record<number, number>>({})

  scoresRef.current = scores
  localeRef.current = locale

  const closeCropEditor = useCallback(() => {
    setPendingCrop(null)
    setIsCropSaving(false)
  }, [])

  useEffect(() => {
    if (!pendingCrop) {
      return
    }
    const objectUrl = pendingCrop.objectUrl
    return () => {
      URL.revokeObjectURL(objectUrl)
    }
  }, [pendingCrop])

  const refreshUploadedIcons = useCallback(async () => {
    const response = await getMoodIcons()
    setUploadedIcons(groupIconsByScore(response.items))
    setMaxUploadsPerScore(response.max_per_score)
  }, [])

  const syncDraftsFromScores = useCallback(
    (nextScores: Record<string, MoodScoreStylePublic>, nextLocale = locale) => {
      const nextColors = Object.fromEntries(
        Object.entries(nextScores).map(([score, style]) => [Number(score), style.color]),
      )
      const nextLabels = Object.fromEntries(
        Object.entries(nextScores).map(([score, style]) => [
          Number(score),
          style.label || defaultMoodScoreLabel(Number(score), nextLocale),
        ]),
      )
      draftColorsRef.current = nextColors
      draftLabelsRef.current = nextLabels
      setDraftColors(nextColors)
      setDraftLabels(nextLabels)
      setDraftEmojis(
        Object.fromEntries(
          Object.entries(nextScores).map(([score, style]) => [
            Number(score),
            style.icon_type === 'emoji'
              ? style.icon
              : defaultMoodScoreStyle(Number(score), nextLocale).icon,
          ]),
        ),
      )
    },
    [locale],
  )

  useEffect(() => {
    if (skipDraftSyncRef.current) {
      skipDraftSyncRef.current = false
      return
    }
    syncDraftsFromScores(scores, locale)
  }, [scores, locale, syncDraftsFromScores])

  useEffect(() => {
    if (editingScore === null) {
      return
    }
    void refreshUploadedIcons().catch(() => {
      setUploadedIcons({})
    })
  }, [editingScore, refreshUploadedIcons])

  const applyPreferences = (preferences: MoodPreferencesPublic) => {
    setPreferences(preferences)
    syncDraftsFromScores(preferences.scores)
  }

  const buildAppearancePatch = (score: number): AppearancePatch => {
    const saved = scoresRef.current[String(score)]
    const nextLocale = localeRef.current
    const patch: AppearancePatch = {}
    const color = draftColorsRef.current[score]
    if (
      color &&
      isValidHexColor(color) &&
      color.toLowerCase() !== (saved?.color ?? '').toLowerCase()
    ) {
      patch.color = color
    }

    const label = (draftLabelsRef.current[score] ?? '').trim()
    if (label && label.length <= MAX_MOOD_SCORE_LABEL_LENGTH) {
      const defaultLabel = defaultMoodScoreLabel(score, nextLocale)
      const savedLabel = saved?.label || defaultLabel
      const nextStored = label === defaultLabel ? '' : label
      const currentStored = savedLabel === defaultLabel ? '' : savedLabel
      if (nextStored !== currentStored) {
        patch.label = nextStored
      }
    }

    return patch
  }

  const hasAppearancePatch = (patch: AppearancePatch) =>
    patch.color !== undefined || patch.label !== undefined

  const persistPendingScores = () => {
    persistChainRef.current = persistChainRef.current
      .catch(() => undefined)
      .then(async () => {
        while (pendingScoresRef.current.size > 0) {
          const score = pendingScoresRef.current.values().next().value as number
          pendingScoresRef.current.delete(score)
          const patch = buildAppearancePatch(score)
          if (!hasAppearancePatch(patch)) {
            continue
          }
          const generation = persistGenerationRef.current[score] ?? 0
          try {
            const saved = await patchMoodPreferences({
              scores: { [String(score)]: patch },
            })
            if (generation !== (persistGenerationRef.current[score] ?? 0)) {
              continue
            }
            skipDraftSyncRef.current = true
            setPreferences(saved)
          } catch (err) {
            if (err instanceof ApiError && err.status === 403) {
              setError(t('errors.verifyToManageMoodPreferences'))
            } else {
              setError(formatApiError(err, t, 'errors.failedSave'))
            }
            break
          }
        }
      })
    return persistChainRef.current
  }

  persistPendingScoresRef.current = persistPendingScores

  const bumpScoreGeneration = (score: number) => {
    persistGenerationRef.current[score] = (persistGenerationRef.current[score] ?? 0) + 1
  }

  const cancelScheduledPersist = (score?: number) => {
    if (score === undefined) {
      for (const option of moodScoreOptions) {
        bumpScoreGeneration(option.score)
      }
      pendingScoresRef.current.clear()
    } else {
      bumpScoreGeneration(score)
      pendingScoresRef.current.delete(score)
    }
    if (saveTimerRef.current !== null && pendingScoresRef.current.size === 0) {
      window.clearTimeout(saveTimerRef.current)
      saveTimerRef.current = null
    }
  }

  const flushScoreAppearance = (score: number) => {
    pendingScoresRef.current.add(score)
    if (saveTimerRef.current !== null) {
      window.clearTimeout(saveTimerRef.current)
      saveTimerRef.current = null
    }
    void persistPendingScores()
  }

  const schedulePersist = (score: number) => {
    pendingScoresRef.current.add(score)
    if (saveTimerRef.current !== null) {
      window.clearTimeout(saveTimerRef.current)
    }
    saveTimerRef.current = window.setTimeout(() => {
      saveTimerRef.current = null
      void persistPendingScores()
    }, APPEARANCE_SAVE_DELAY_MS)
  }

  const revertInvalidDrafts = (score: number) => {
    const saved = scoresRef.current[String(score)]
    if (!saved) {
      return
    }
    const color = draftColorsRef.current[score]
    if (!color || !isValidHexColor(color)) {
      const nextColors = { ...draftColorsRef.current, [score]: saved.color }
      draftColorsRef.current = nextColors
      setDraftColors(nextColors)
    }
    const label = (draftLabelsRef.current[score] ?? '').trim()
    if (!label) {
      const nextLabel = saved.label || defaultMoodScoreLabel(score, localeRef.current)
      const nextLabels = { ...draftLabelsRef.current, [score]: nextLabel }
      draftLabelsRef.current = nextLabels
      setDraftLabels(nextLabels)
    }
  }

  const closeScoreEditor = () => {
    if (editingScore !== null) {
      revertInvalidDrafts(editingScore)
    }
    if (saveTimerRef.current !== null) {
      window.clearTimeout(saveTimerRef.current)
      saveTimerRef.current = null
    }
    void persistPendingScores()
    setEditingScore(null)
    setError(null)
    setSuccess(null)
  }

  useEffect(() => {
    return () => {
      if (saveTimerRef.current !== null) {
        window.clearTimeout(saveTimerRef.current)
        saveTimerRef.current = null
      }
      void persistPendingScoresRef.current()
    }
  }, [])

  const handleColorChange = (score: number, value: string) => {
    const nextColors = { ...draftColorsRef.current, [score]: value }
    draftColorsRef.current = nextColors
    setDraftColors(nextColors)
    setError(null)
    schedulePersist(score)
  }

  const handleLabelChange = (score: number, value: string) => {
    const nextLabels = { ...draftLabelsRef.current, [score]: value }
    draftLabelsRef.current = nextLabels
    setDraftLabels(nextLabels)
    setError(null)
    schedulePersist(score)
  }

  const patchIconStyle = async (
    score: number,
    patch: { icon_type: MoodScoreIconType; icon: string; color?: string },
  ) => {
    cancelScheduledPersist(score)
    setIconBusyScore(score)
    setError(null)
    setSuccess(null)
    try {
      const appearance = buildAppearancePatch(score)
      const saved = await patchMoodPreferences({
        scores: { [String(score)]: { ...appearance, ...patch } },
      })
      applyPreferences(saved)
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError(t('errors.verifyToManageMoodPreferences'))
      } else {
        setError(formatApiError(err, t, 'errors.failedSave'))
      }
      throw err
    } finally {
      setIconBusyScore(null)
    }
  }

  const handleIconSourceChange = async (score: number, iconType: IconSourceUi) => {
    setSourceUiByScore((current) => ({ ...current, [score]: iconType }))
    if (iconType === 'emoji') {
      await patchIconStyle(score, {
        icon_type: 'emoji',
        icon: draftEmojis[score] ?? defaultMoodScoreStyle(score, locale).icon,
      })
      return
    }
    if (iconType === 'catalog') {
      return
    }
    const uploads = uploadedIcons[score] ?? []
    if (uploads.length === 0) {
      return
    }
    await patchIconStyle(score, {
      icon_type: 'upload',
      icon: uploads[uploads.length - 1].id,
    })
  }

  const handleCatalogSelect = async (score: number, iconId: string) => {
    setSourceUiByScore((current) => ({ ...current, [score]: 'catalog' }))
    const current = scores[String(score)]
    if (current?.icon_type === 'catalog' && current.icon === iconId) {
      return
    }
    await patchIconStyle(score, { icon_type: 'catalog', icon: iconId })
  }

  const handleEmojiSelect = async (score: number, emoji: string) => {
    setDraftEmojis((current) => ({ ...current, [score]: emoji }))
    setSourceUiByScore((current) => ({ ...current, [score]: 'emoji' }))
    const current = scores[String(score)]
    if (current?.icon_type === 'emoji' && current.icon === emoji) {
      return
    }
    await patchIconStyle(score, { icon_type: 'emoji', icon: emoji })
  }

  const handleUploadSelect = async (score: number, iconId: string) => {
    setSourceUiByScore((current) => ({ ...current, [score]: 'upload' }))
    const current = scores[String(score)]
    if (current?.icon_type === 'upload' && current.icon === iconId) {
      return
    }
    await patchIconStyle(score, { icon_type: 'upload', icon: iconId })
  }

  const handleUploadSelectFile = async (score: number, event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) {
      return
    }

    const currentUploads = uploadedIcons[score] ?? []
    if (currentUploads.length >= maxUploadsPerScore) {
      setError(t('moodPreferences.uploadLimitReached', { max: String(maxUploadsPerScore) }))
      return
    }

    setError(null)
    setSuccess(null)

    const loaded = await readMoodIconImage(file)
    if ('error' in loaded) {
      setError(cropValidationMessage(loaded.error))
      return
    }

    setPendingCrop({
      score,
      image: loaded.image,
      objectUrl: loaded.objectUrl,
      fileName: file.name,
      sourceFile: file,
    })
  }

  const handleCropSave = async (croppedFile: File) => {
    if (!pendingCrop) {
      return
    }

    const score = pendingCrop.score
    const replaceIconId = pendingCrop.replaceIconId
    const sourceFile = pendingCrop.sourceFile
    setIsCropSaving(true)
    setIconBusyScore(score)
    setError(null)
    setSuccess(null)
    try {
      if (replaceIconId) {
        const currentCount = (uploadedIcons[score] ?? []).length
        const atLimit = currentCount >= maxUploadsPerScore

        if (atLimit) {
          await deleteMoodIcon(replaceIconId)
          revokeMoodIconObjectUrl(replaceIconId)
          const result = await uploadMoodIcon(score, croppedFile, sourceFile)
          applyPreferences(result.preferences)
        } else {
          const result = await uploadMoodIcon(score, croppedFile, sourceFile)
          applyPreferences(result.preferences)
          try {
            await deleteMoodIcon(replaceIconId)
            revokeMoodIconObjectUrl(replaceIconId)
          } catch {
            // New crop is saved; stale icon may remain until the user removes it.
          }
        }
      } else {
        const result = await uploadMoodIcon(score, croppedFile, sourceFile)
        applyPreferences(result.preferences)
      }

      await refreshUploadedIcons()
      setSourceUiByScore((current) => ({ ...current, [score]: 'upload' }))
      setSuccess(t('moodPreferences.saved'))
      closeCropEditor()
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError(t('errors.verifyToManageMoodPreferences'))
      } else {
        setError(formatApiError(err, t, 'moodPreferences.uploadFailed'))
      }
      setIsCropSaving(false)
      await refreshUploadedIcons().catch(() => undefined)
    } finally {
      setIconBusyScore(null)
    }
  }

  const handleRecropUpload = async (score: number, icon: MoodIconMeta) => {
    setIconBusyScore(score)
    setError(null)
    setSuccess(null)
    try {
      let blob: Blob
      if (icon.has_source) {
        blob = await fetchMoodIconSourceBlob(icon.id)
      } else {
        blob = await fetchMoodIconBlob(icon.id)
      }
      const loaded = await readMoodIconBlobForCrop(blob)
      if ('error' in loaded) {
        setError(cropValidationMessage(loaded.error))
        return
      }
      setPendingCrop({
        score,
        image: loaded.image,
        objectUrl: loaded.objectUrl,
        fileName: icon.original_name,
        sourceFile: blobToNamedFile(blob, icon.original_name),
        replaceIconId: icon.id,
      })
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError(t('errors.verifyToManageMoodPreferences'))
      } else {
        setError(formatApiError(err, t, 'moodPreferences.imageLoadFailed'))
      }
    } finally {
      setIconBusyScore(null)
    }
  }

  const handleRemoveUpload = async (score: number, iconId: string) => {
    setIconBusyScore(score)
    setError(null)
    setSuccess(null)
    try {
      await deleteMoodIcon(iconId)
      revokeMoodIconObjectUrl(iconId)
      await refreshUploadedIcons()
      await refreshPreferences()
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError(t('errors.verifyToManageMoodPreferences'))
      } else {
        setError(formatApiError(err, t, 'errors.failedSave'))
      }
    } finally {
      setIconBusyScore(null)
    }
  }

  const handleResetScore = async (score: number) => {
    cancelScheduledPersist(score)
    const defaultStyle = defaultMoodScoreStyle(score, locale)
    const nextColor = DEFAULT_MOOD_SCORE_COLORS[score] ?? defaultStyle.color
    const nextColors = { ...draftColorsRef.current, [score]: nextColor }
    const nextLabels = { ...draftLabelsRef.current, [score]: defaultStyle.label }
    draftColorsRef.current = nextColors
    draftLabelsRef.current = nextLabels
    setDraftColors(nextColors)
    setDraftLabels(nextLabels)
    setDraftEmojis((current) => ({ ...current, [score]: defaultStyle.icon }))

    setIconBusyScore(score)
    setError(null)
    try {
      const saved = await patchMoodPreferences({
        scores: {
          [String(score)]: {
            color: nextColor,
            icon_type: 'emoji',
            icon: defaultStyle.icon,
            label: '',
          },
        },
      })
      applyPreferences(saved)
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError(t('errors.verifyToManageMoodPreferences'))
      } else {
        setError(formatApiError(err, t, 'errors.failedSave'))
      }
    } finally {
      setIconBusyScore(null)
    }
  }

  const handleResetAll = async () => {
    cancelScheduledPersist()
    const nextColors = { ...DEFAULT_MOOD_SCORE_COLORS }
    const nextLabels = Object.fromEntries(
      moodScoreOptions.map((option) => [
        option.score,
        defaultMoodScoreLabel(option.score, locale),
      ]),
    )
    draftColorsRef.current = nextColors
    draftLabelsRef.current = nextLabels
    setDraftColors(nextColors)
    setDraftLabels(nextLabels)

    setIsSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const saved = await patchMoodPreferences({
        scores: Object.fromEntries(
          moodScoreOptions.map((option) => [
            String(option.score),
            {
              color: DEFAULT_MOOD_SCORE_COLORS[option.score],
              label: '',
            },
          ]),
        ),
      })
      applyPreferences(saved)
      setSuccess(t('moodPreferences.saved'))
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError(t('errors.verifyToManageMoodPreferences'))
      } else {
        setError(formatApiError(err, t, 'errors.failedSave'))
      }
    } finally {
      setIsSaving(false)
    }
  }

  const runPendingConfirm = async () => {
    if (!pendingConfirm) {
      return
    }
    const action = pendingConfirm
    setPendingConfirm(null)
    if (action.kind === 'reset-score') {
      await handleResetScore(action.score)
      return
    }
    if (action.kind === 'reset-all') {
      await handleResetAll()
      return
    }
    await handleRemoveUpload(action.score, action.iconId)
  }

  const confirmDialogProps = (() => {
    if (!pendingConfirm) {
      return null
    }
    if (pendingConfirm.kind === 'reset-score') {
      return {
        title: t('confirm.resetMoodScoreTitle'),
        message: t('confirm.resetMoodScore', { label: pendingConfirm.label }),
        confirmLabel: t('moodPreferences.resetScore'),
      }
    }
    if (pendingConfirm.kind === 'reset-all') {
      return {
        title: t('confirm.resetMoodAllTitle'),
        message: t('confirm.resetMoodAll'),
        confirmLabel: t('moodPreferences.resetAll'),
      }
    }
    return {
      title: t('confirm.removeMoodIconTitle'),
      message: t('confirm.removeMoodIcon'),
      confirmLabel: t('moodPreferences.removeIcon'),
    }
  })()

  if (isLoading) {
    return <p className="muted">{t('common.loadingMoodPreferences')}</p>
  }

  const editingOption =
    editingScore === null
      ? null
      : moodScoreOptions.find((option) => option.score === editingScore) ?? null
  const drawerColors = Object.values(draftColors)

  const renderScoreEditor = (option: (typeof moodScoreOptions)[number]) => {
    const currentStyle = scores[String(option.score)] ?? option.style
    const previewStyle = {
      ...currentStyle,
      color: draftColors[option.score] ?? option.color,
    }
    const iconBusy = iconBusyScore === option.score
    const sourceUi =
      sourceUiByScore[option.score] ?? resolveIconSourceUi(currentStyle.icon_type)
    const scoreUploads = uploadedIcons[option.score] ?? []
    const uploadFull = scoreUploads.length >= maxUploadsPerScore
    const label = draftLabels[option.score] ?? option.label

    return (
      <div key={option.score} className="mood-preferences-row">
        <div className="mood-preferences-preview">
          <span
            className="mood-preferences-swatch"
            style={{ backgroundColor: draftColors[option.score] ?? option.color }}
            aria-hidden
          />
          <span
            className="mood-preferences-icon-slot"
            style={{ filter: moodGlowFilter(previewStyle.color) }}
          >
            <MoodScoreIcon
              style={previewStyle}
              className="mood-preferences-emoji"
              fallbackScore={option.score}
            />
          </span>
          <label className="mood-preferences-label-field">
            <span className="visually-hidden">
              {t('moodPreferences.labelFor', { score: option.score })}
            </span>
            <input
              className="form-input mood-preferences-label-input"
              type="text"
              value={label}
              maxLength={MAX_MOOD_SCORE_LABEL_LENGTH}
              onChange={(event) => handleLabelChange(option.score, event.target.value)}
              onBlur={() => flushScoreAppearance(option.score)}
              aria-label={t('moodPreferences.labelFor', { score: option.score })}
            />
          </label>
          <button
            type="button"
            className="button button-danger-ghost button-small"
            onClick={() =>
              setPendingConfirm({
                kind: 'reset-score',
                score: option.score,
                label,
              })
            }
            disabled={iconBusy}
          >
            {t('moodPreferences.resetScore')}
          </button>
        </div>

        <div
          onBlur={(event) => {
            const next = event.relatedTarget
            if (next instanceof Node && event.currentTarget.contains(next)) {
              return
            }
            flushScoreAppearance(option.score)
          }}
        >
          <ColorPicker
            id={`mood-color-${option.score}`}
            value={draftColors[option.score] ?? option.color}
            onChange={(hex) => handleColorChange(option.score, hex)}
            disabled={iconBusy}
            colorLabel={t('moodPreferences.colorFor', { label })}
            hexLabel={t('moodPreferences.hexFor', { label })}
          />
        </div>

        <fieldset className="mood-preferences-icon-source" disabled={iconBusy}>
          <legend className="form-label">{t('moodPreferences.iconSource')}</legend>
          <div
            className="segmented-control"
            role="radiogroup"
            aria-label={t('moodPreferences.iconSource')}
          >
            <button
              type="button"
              className={`segmented-control-option${sourceUi === 'emoji' ? ' is-active' : ''}`}
              aria-pressed={sourceUi === 'emoji'}
              onClick={() => void handleIconSourceChange(option.score, 'emoji')}
            >
              {t('moodPreferences.iconTypeEmoji')}
            </button>
            <button
              type="button"
              className={`segmented-control-option${sourceUi === 'upload' ? ' is-active' : ''}`}
              aria-pressed={sourceUi === 'upload'}
              onClick={() => void handleIconSourceChange(option.score, 'upload')}
            >
              {t('moodPreferences.iconTypeUpload')}
            </button>
            {marketplaceEnabled || currentStyle.icon_type === 'catalog' ? (
              <button
                type="button"
                className={`segmented-control-option${sourceUi === 'catalog' ? ' is-active' : ''}`}
                aria-pressed={sourceUi === 'catalog'}
                onClick={() => void handleIconSourceChange(option.score, 'catalog')}
              >
                {t('moodPreferences.iconTypeCatalog')}
              </button>
            ) : null}
          </div>

          <div className="mood-preferences-icon-panel">
            {sourceUi === 'emoji' ? (
              <EmojiPicker
                value={draftEmojis[option.score] ?? ''}
                groups={MOOD_EMOJI_GROUPS}
                groupLabel={(groupId) => t(`moodPreferences.emojiGroup${groupId}`)}
                onChange={(emoji) => void handleEmojiSelect(option.score, emoji)}
                disabled={iconBusy}
                label={t('moodPreferences.chooseEmoji')}
              />
            ) : sourceUi === 'catalog' ? (
              <CatalogIconPicker
                selectedIconId={
                  currentStyle.icon_type === 'catalog' ? currentStyle.icon : null
                }
                glowColor={previewStyle.color}
                suggestedMood={option.score}
                disabled={iconBusy}
                onSelect={(icon) => void handleCatalogSelect(option.score, icon.id)}
              />
            ) : (
              <div className="mood-preferences-upload-section">
                <div className="mood-preferences-upload-row">
                  <div className="mood-preferences-upload-grid" role="list">
                    {scoreUploads.map((icon) => {
                      const selected =
                        currentStyle.icon_type === 'upload' && currentStyle.icon === icon.id
                      return (
                        <div
                          key={icon.id}
                          className="mood-preferences-upload-item"
                          role="listitem"
                        >
                          <button
                            type="button"
                            className={`mood-preferences-upload-tile${selected ? ' mood-preferences-upload-tile-selected' : ''}`}
                            aria-pressed={selected}
                            aria-label={icon.original_name}
                            disabled={iconBusyScore === option.score}
                            onClick={() => void handleUploadSelect(option.score, icon.id)}
                          >
                            <span style={{ filter: moodGlowFilter(previewStyle.color) }}>
                              <MoodScoreIcon
                                style={{
                                  color: previewStyle.color,
                                  icon_type: 'upload',
                                  icon: icon.id,
                                  label,
                                }}
                                className="mood-preferences-upload-thumb"
                                fallbackScore={option.score}
                              />
                            </span>
                          </button>
                          <button
                            type="button"
                            className="mood-preferences-upload-action mood-preferences-upload-edit"
                            aria-label={t('moodPreferences.editIcon')}
                            disabled={iconBusyScore === option.score}
                            onClick={() => void handleRecropUpload(option.score, icon)}
                          >
                            <svg
                              viewBox="0 0 24 24"
                              width="14"
                              height="14"
                              aria-hidden="true"
                              focusable="false"
                            >
                              <path
                                fill="currentColor"
                                d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"
                              />
                            </svg>
                          </button>
                          <button
                            type="button"
                            className="mood-preferences-upload-action mood-preferences-upload-remove"
                            aria-label={t('moodPreferences.removeIcon')}
                            disabled={iconBusyScore === option.score}
                            onClick={() =>
                              setPendingConfirm({
                                kind: 'remove-icon',
                                score: option.score,
                                iconId: icon.id,
                              })
                            }
                          >
                            <svg
                              viewBox="0 0 24 24"
                              width="14"
                              height="14"
                              aria-hidden="true"
                              focusable="false"
                            >
                              <path
                                fill="currentColor"
                                d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"
                              />
                            </svg>
                          </button>
                        </div>
                      )
                    })}
                    {!uploadFull ? (
                      <div className="mood-preferences-upload-item" role="listitem">
                        <label
                          className={`mood-preferences-upload-add${iconBusy ? ' is-disabled' : ''}`}
                          aria-label={t('moodPreferences.uploadIcon')}
                        >
                          <span aria-hidden="true">+</span>
                          <input
                            type="file"
                            accept="image/jpeg,image/png,image/webp,image/gif"
                            className="mood-preferences-upload-input"
                            disabled={iconBusy}
                            onChange={(event) => void handleUploadSelectFile(option.score, event)}
                          />
                        </label>
                      </div>
                    ) : null}
                  </div>
                  <p className="form-hint mood-preferences-upload-count">
                    {uploadFull
                      ? t('moodPreferences.uploadSlotsFull', {
                          max: String(maxUploadsPerScore),
                        })
                      : t('moodPreferences.uploadCount', {
                          remaining: String(maxUploadsPerScore - scoreUploads.length),
                          max: String(maxUploadsPerScore),
                        })}
                  </p>
                </div>
              </div>
            )}
          </div>
        </fieldset>
      </div>
    )
  }

  return (
    <form
      className="card form mood-preferences-form"
      onSubmit={(event) => event.preventDefault()}
    >
      {pendingCrop ? (
        <ImageCropModal
          image={pendingCrop.image}
          imageUrl={pendingCrop.objectUrl}
          fileName={pendingCrop.fileName}
          isSaving={isCropSaving}
          onCancel={closeCropEditor}
          onSave={handleCropSave}
        />
      ) : null}
      {confirmDialogProps ? (
        <ConfirmDialog
          open
          title={confirmDialogProps.title}
          message={confirmDialogProps.message}
          confirmLabel={confirmDialogProps.confirmLabel}
          onCancel={() => setPendingConfirm(null)}
          onConfirm={() => void runPendingConfirm()}
        />
      ) : null}
      <PageErrorAlert error={editingOption ? null : error} />
      {!editingOption && success ? <Alert variant="success">{success}</Alert> : null}

      <p className="form-hint">{t('moodPreferences.listLead')}</p>

      <div className="mood-score-list">
        {moodScoreOptions.map((option) => {
          const currentStyle = scores[String(option.score)] ?? option.style
          const previewStyle = {
            ...currentStyle,
            color: draftColors[option.score] ?? option.color,
          }
          const label = draftLabels[option.score] ?? option.label
          return (
            <article
              key={option.score}
              className={`card mood-score-row${editingScore === option.score ? ' is-selected' : ''}`}
            >
              <div className="mood-score-row-main">
                <span
                  className="mood-preferences-swatch"
                  style={{ backgroundColor: previewStyle.color }}
                  aria-hidden
                />
                <span className="mood-preferences-icon-slot">
                  <MoodScoreIcon
                    style={previewStyle}
                    className="mood-preferences-emoji"
                    fallbackScore={option.score}
                  />
                </span>
                <p className="mood-score-row-label">{label}</p>
              </div>
              <IconButton
                label={t('moodPreferences.editScore', { label })}
                size="sm"
                onClick={() => {
                  if (editingScore !== null && editingScore !== option.score) {
                    revertInvalidDrafts(editingScore)
                  }
                  if (saveTimerRef.current !== null) {
                    window.clearTimeout(saveTimerRef.current)
                    saveTimerRef.current = null
                  }
                  void persistPendingScores()
                  setError(null)
                  setSuccess(null)
                  setEditingScore(option.score)
                }}
              >
                <EditIcon />
              </IconButton>
            </article>
          )
        })}
      </div>

      <EditorDrawer
        open={editingOption !== null}
        title={
          editingOption
            ? t('moodPreferences.editScore', {
                label: draftLabels[editingOption.score] ?? editingOption.label,
              })
            : ''
        }
        onClose={closeScoreEditor}
        accentColors={drawerColors}
      >
        <PageErrorAlert error={error} />
        {success ? <Alert variant="success">{success}</Alert> : null}
        {editingOption ? renderScoreEditor(editingOption) : null}
        <p className="form-hint">{t('moodPreferences.lead')}</p>
      </EditorDrawer>

      <div className="button-row">
        <button
          type="button"
          className="button button-danger-ghost"
          onClick={() => setPendingConfirm({ kind: 'reset-all' })}
          disabled={isSaving}
        >
          {t('moodPreferences.resetAll')}
        </button>
      </div>
    </form>
  )
}
