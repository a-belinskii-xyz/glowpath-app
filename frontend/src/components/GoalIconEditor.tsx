import { type ChangeEvent, useCallback, useEffect, useState } from 'react'

import {
  deleteGoalIcon,
  fetchGoalIconBlob,
  getGoalIcons,
  listGoals,
  patchGoal,
  uploadGoalIcon,
} from '../api/goals'
import { Alert } from './Alert'
import { GoalIcon } from './GoalIcon'
import { ImageCropModal } from './ImageCropModal'
import { useLocale } from '../context/LocaleContext'
import { ApiError } from '../lib/errors'
import {
  readMoodIconBlobForCrop,
  readMoodIconImage,
  type CropValidationError,
} from '../lib/imageCrop'
import {
  getBuiltinMoodIconLabel,
  MOOD_BUILTIN_ICONS,
} from '../lib/moodBuiltinIcons'
import { revokeGoalIconObjectUrl } from '../lib/goalIconBlobUrl'
import { isValidHexColor } from '../lib/moodScale'
import type { GoalIconMeta, GoalPublic, GoalStyle } from '../types/goal'
import type { MoodScoreIconType } from '../types/moodPreferences'

type PendingCrop = {
  image: HTMLImageElement
  objectUrl: string
  fileName: string
  replaceIconId?: string
}

const MAX_UPLOADS_PER_GOAL = 3

type GoalIconEditorProps = {
  goal: GoalPublic
  onGoalChange: (goal: GoalPublic) => void
}

export function GoalIconEditor({ goal, onGoalChange }: GoalIconEditorProps) {
  const { locale, t } = useLocale()
  const [draftColor, setDraftColor] = useState(goal.color)
  const [draftEmoji, setDraftEmoji] = useState(goal.icon_type === 'emoji' ? goal.icon : '🎯')
  const [uploadedIcons, setUploadedIcons] = useState<GoalIconMeta[]>([])
  const [maxUploads, setMaxUploads] = useState(MAX_UPLOADS_PER_GOAL)
  const [iconBusy, setIconBusy] = useState(false)
  const [pendingCrop, setPendingCrop] = useState<PendingCrop | null>(null)
  const [isCropSaving, setIsCropSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const style: GoalStyle = {
    color: draftColor,
    icon_type: goal.icon_type,
    icon: goal.icon,
  }
  const uploadFull = uploadedIcons.length >= maxUploads

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

  useEffect(() => {
    setDraftColor(goal.color)
    if (goal.icon_type === 'emoji') {
      setDraftEmoji(goal.icon)
    }
  }, [goal.color, goal.icon, goal.icon_type, goal.id])

  useEffect(() => {
    let cancelled = false
    void getGoalIcons(goal.id)
      .then((response) => {
        if (cancelled) {
          return
        }
        setUploadedIcons(response.items)
        setMaxUploads(response.max_per_goal)
      })
      .catch(() => {
        if (!cancelled) {
          setUploadedIcons([])
        }
      })
    return () => {
      cancelled = true
    }
  }, [goal.id])

  const applyStyle = async (patch: {
    color?: string
    icon_type?: MoodScoreIconType
    icon?: string
  }) => {
    setIconBusy(true)
    setError(null)
    try {
      const updated = await patchGoal(goal.id, patch)
      onGoalChange(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.failedSave'))
    } finally {
      setIconBusy(false)
    }
  }

  const handleColorBlur = async () => {
    if (!isValidHexColor(draftColor)) {
      setDraftColor(goal.color)
      return
    }
    if (draftColor.toLowerCase() === goal.color.toLowerCase()) {
      return
    }
    await applyStyle({ color: draftColor })
  }

  const handleIconSourceChange = async (iconType: MoodScoreIconType) => {
    if (iconType === goal.icon_type) {
      return
    }
    if (iconType === 'emoji') {
      await applyStyle({ icon_type: 'emoji', icon: draftEmoji || '🎯' })
      return
    }
    if (iconType === 'builtin') {
      await applyStyle({ icon_type: 'builtin', icon: MOOD_BUILTIN_ICONS[0]?.slug ?? 'awful-cloud' })
      return
    }
    if (uploadedIcons.length === 0) {
      return
    }
    await applyStyle({ icon_type: 'upload', icon: uploadedIcons[uploadedIcons.length - 1].id })
  }

  const handleEmojiBlur = async () => {
    const emoji = draftEmoji.trim()
    if (!emoji || emoji === goal.icon) {
      return
    }
    await applyStyle({ icon_type: 'emoji', icon: emoji })
  }

  const handleBuiltinSelect = async (slug: string) => {
    if (goal.icon_type === 'builtin' && goal.icon === slug) {
      return
    }
    await applyStyle({ icon_type: 'builtin', icon: slug })
  }

  const handleUploadSelect = async (iconId: string) => {
    if (goal.icon_type === 'upload' && goal.icon === iconId) {
      return
    }
    await applyStyle({ icon_type: 'upload', icon: iconId })
  }

  const handleUploadSelectFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) {
      return
    }
    setError(null)
    try {
      const { image, objectUrl } = await readMoodIconImage(file)
      setPendingCrop({
        image,
        objectUrl,
        fileName: file.name || 'icon.png',
      })
    } catch (err) {
      const reason = (err as { reason?: CropValidationError }).reason
      setError(reason ? cropValidationMessage(reason) : t('moodPreferences.uploadFailed'))
    }
  }

  const handleRecropUpload = async (icon: GoalIconMeta) => {
    setError(null)
    try {
      const blob = await fetchGoalIconBlob(icon.id)
      const { image, objectUrl } = await readMoodIconBlobForCrop(blob, icon.original_name)
      setPendingCrop({
        image,
        objectUrl,
        fileName: icon.original_name,
        replaceIconId: icon.id,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : t('moodPreferences.uploadFailed'))
    }
  }

  const handleCropSave = async (croppedFile: File) => {
    if (!pendingCrop) {
      return
    }
    setIsCropSaving(true)
    setError(null)
    try {
      const replaceId = pendingCrop.replaceIconId
      let resultGoal: GoalPublic | null = null

      if (replaceId) {
        const atLimit = uploadedIcons.length >= maxUploads
        if (atLimit) {
          await deleteGoalIcon(replaceId)
          revokeGoalIconObjectUrl(replaceId)
          const result = await uploadGoalIcon(goal.id, croppedFile)
          resultGoal = result.goal
        } else {
          const result = await uploadGoalIcon(goal.id, croppedFile)
          resultGoal = result.goal
          try {
            await deleteGoalIcon(replaceId)
            revokeGoalIconObjectUrl(replaceId)
          } catch {
            // New crop is saved; stale icon may remain until the user removes it.
          }
        }
      } else {
        const result = await uploadGoalIcon(goal.id, croppedFile)
        resultGoal = result.goal
      }

      const listed = await getGoalIcons(goal.id)
      setUploadedIcons(listed.items)
      setMaxUploads(listed.max_per_goal)
      if (resultGoal) {
        onGoalChange(resultGoal)
      }
      closeCropEditor()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('moodPreferences.uploadFailed'))
      setIsCropSaving(false)
    }
  }

  const handleRemoveUpload = async (iconId: string) => {
    setIconBusy(true)
    setError(null)
    try {
      await deleteGoalIcon(iconId)
      revokeGoalIconObjectUrl(iconId)
      const [listed, goalsResponse] = await Promise.all([
        getGoalIcons(goal.id),
        listGoals(),
      ])
      setUploadedIcons(listed.items)
      setMaxUploads(listed.max_per_goal)
      const updated = goalsResponse.items.find((item) => item.id === goal.id)
      if (updated) {
        onGoalChange(updated)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('moodPreferences.uploadFailed'))
    } finally {
      setIconBusy(false)
    }
  }

  return (
    <div className="goal-icon-editor">
      {pendingCrop ? (
        <ImageCropModal
          image={pendingCrop.image}
          imageUrl={pendingCrop.objectUrl}
          fileName={pendingCrop.fileName}
          isSaving={isCropSaving}
          onCancel={closeCropEditor}
          onSave={(file) => void handleCropSave(file)}
        />
      ) : null}
      {error ? <Alert variant="error">{error}</Alert> : null}

      <div className="mood-preferences-preview">
        <span
          className="mood-preferences-swatch"
          style={{ backgroundColor: draftColor }}
          aria-hidden
        />
        <span style={{ filter: `drop-shadow(0 0 0.35rem ${draftColor}88)` }}>
          <GoalIcon style={style} className="mood-preferences-emoji" />
        </span>
      </div>

      <div className="mood-preferences-controls">
        <input
          className="mood-preferences-color-input"
          type="color"
          value={isValidHexColor(draftColor) ? draftColor : goal.color}
          onChange={(event) => setDraftColor(event.target.value)}
          onBlur={() => void handleColorBlur()}
          disabled={iconBusy}
          aria-label={t('goalsPage.colorFor', { label: goal.label })}
        />
        <input
          className="form-input mood-preferences-hex-input"
          type="text"
          value={draftColor}
          onChange={(event) => setDraftColor(event.target.value)}
          onBlur={() => void handleColorBlur()}
          pattern="^#[0-9A-Fa-f]{6}$"
          spellCheck={false}
          disabled={iconBusy}
          aria-label={t('goalsPage.hexFor', { label: goal.label })}
        />
      </div>

      <fieldset className="mood-preferences-icon-source" disabled={iconBusy}>
        <legend className="form-label">{t('moodPreferences.iconSource')}</legend>
        <div className="mood-preferences-icon-source-options">
          <label className="mood-preferences-radio">
            <input
              type="radio"
              name={`goal-icon-source-${goal.id}`}
              checked={goal.icon_type === 'emoji'}
              onChange={() => void handleIconSourceChange('emoji')}
            />
            {t('moodPreferences.iconTypeEmoji')}
          </label>
          <label className="mood-preferences-radio">
            <input
              type="radio"
              name={`goal-icon-source-${goal.id}`}
              checked={goal.icon_type === 'builtin'}
              onChange={() => void handleIconSourceChange('builtin')}
            />
            {t('moodPreferences.iconTypeBuiltin')}
          </label>
          <label className="mood-preferences-radio">
            <input
              type="radio"
              name={`goal-icon-source-${goal.id}`}
              checked={goal.icon_type === 'upload'}
              disabled={uploadedIcons.length === 0}
              onChange={() => void handleIconSourceChange('upload')}
            />
            {t('moodPreferences.iconTypeUpload')}
          </label>
        </div>

        {goal.icon_type === 'emoji' ? (
          <label className="form-field mood-preferences-emoji-field">
            <span className="form-label">{t('moodPreferences.iconTypeEmoji')}</span>
            <input
              className="form-input mood-preferences-emoji-input"
              type="text"
              value={draftEmoji}
              maxLength={8}
              onChange={(event) => setDraftEmoji(event.target.value)}
              onBlur={() => void handleEmojiBlur()}
            />
          </label>
        ) : null}

        {goal.icon_type === 'builtin' ? (
          <div className="mood-preferences-builtin-grid" role="list">
            <p className="form-hint">{t('moodPreferences.selectBuiltinIcon')}</p>
            {MOOD_BUILTIN_ICONS.map((icon) => {
              const selected = goal.icon === icon.slug
              return (
                <button
                  key={icon.slug}
                  type="button"
                  role="listitem"
                  className={`mood-preferences-builtin-option${selected ? ' mood-preferences-builtin-option-selected' : ''}`}
                  aria-pressed={selected}
                  aria-label={getBuiltinMoodIconLabel(icon.slug, locale)}
                  onClick={() => void handleBuiltinSelect(icon.slug)}
                >
                  <img src={icon.assetPath} alt="" className="mood-preferences-builtin-thumb" />
                </button>
              )
            })}
          </div>
        ) : null}

        <div className="mood-preferences-upload-section">
          {uploadedIcons.length > 0 ? (
            <>
              <p className="form-hint">{t('moodPreferences.selectUploadedIcon')}</p>
              <div className="mood-preferences-upload-grid" role="list">
                {uploadedIcons.map((icon) => {
                  const selected = goal.icon_type === 'upload' && goal.icon === icon.id
                  return (
                    <div key={icon.id} className="mood-preferences-upload-item" role="listitem">
                      <button
                        type="button"
                        className={`mood-preferences-upload-tile${selected ? ' mood-preferences-upload-tile-selected' : ''}`}
                        aria-pressed={selected}
                        aria-label={
                          selected ? t('moodPreferences.editIcon') : icon.original_name
                        }
                        disabled={iconBusy}
                        onClick={() => {
                          if (selected) {
                            void handleRecropUpload(icon)
                          } else {
                            void handleUploadSelect(icon.id)
                          }
                        }}
                      >
                        <span style={{ filter: `drop-shadow(0 0 0.35rem ${draftColor}88)` }}>
                          <GoalIcon
                            style={{
                              color: draftColor,
                              icon_type: 'upload',
                              icon: icon.id,
                            }}
                            className="mood-preferences-upload-thumb"
                          />
                        </span>
                      </button>
                      <button
                        type="button"
                        className="mood-preferences-upload-remove"
                        aria-label={t('moodPreferences.removeIcon')}
                        disabled={iconBusy}
                        onClick={() => void handleRemoveUpload(icon.id)}
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
              </div>
            </>
          ) : null}

          <div className="mood-preferences-upload-controls">
            {uploadFull ? (
              <button type="button" className="button button-secondary button-small" disabled>
                {t('goalsPage.uploadIcon')}
              </button>
            ) : (
              <label className="button button-secondary button-small mood-preferences-upload-label">
                {t('goalsPage.uploadIcon')}
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  className="mood-preferences-upload-input"
                  onChange={(event) => void handleUploadSelectFile(event)}
                />
              </label>
            )}
            <span className="form-hint mood-preferences-upload-count">
              {t('goalsPage.uploadCount', {
                count: String(uploadedIcons.length),
                max: String(maxUploads),
              })}
            </span>
          </div>
          {uploadFull ? (
            <p className="form-hint mood-preferences-upload-limit">
              {t('goalsPage.uploadLimitReached', { max: String(maxUploads) })}
            </p>
          ) : null}
        </div>
      </fieldset>
    </div>
  )
}
