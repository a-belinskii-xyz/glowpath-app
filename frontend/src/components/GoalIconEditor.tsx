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
import { ColorPicker } from './ColorPicker'
import { ConfirmDialog } from './ConfirmDialog'
import { EmojiPicker } from './EmojiPicker'
import { GoalIcon } from './GoalIcon'
import { ImageCropModal } from './ImageCropModal'
import { useLocale } from '../context/LocaleContext'
import { moodGlowFilter } from '../design'
import { ApiError } from '../lib/errors'
import { GOAL_EMOJI_GROUPS } from '../lib/emojiPalette'
import {
  readMoodIconBlobForCrop,
  readMoodIconImage,
  type CropValidationError,
} from '../lib/imageCrop'
import { revokeGoalIconObjectUrl } from '../lib/goalIconBlobUrl'
import type { GoalIconMeta, GoalPublic, GoalStyle } from '../types/goal'

type PendingCrop = {
  image: HTMLImageElement
  objectUrl: string
  fileName: string
  replaceIconId?: string
}

const MAX_UPLOADS_PER_GOAL = 3

type IconSourceUi = 'emoji' | 'upload'

type GoalIconEditorProps = {
  /** Controlled color draft (saved with the parent form). */
  color: string
  onColorChange: (color: string) => void
  /** Controlled emoji draft (saved with the parent form when source is emoji). */
  emoji: string
  onEmojiChange: (emoji: string) => void
  /** When set, upload management is available (edit mode). */
  goal?: GoalPublic
  onGoalChange?: (goal: GoalPublic) => void
  disabled?: boolean
}

function resolveIconSourceUi(goal: GoalPublic | undefined): IconSourceUi {
  return goal?.icon_type === 'upload' ? 'upload' : 'emoji'
}

export function GoalIconEditor({
  color,
  onColorChange,
  emoji,
  onEmojiChange,
  goal,
  onGoalChange,
  disabled = false,
}: GoalIconEditorProps) {
  const { t } = useLocale()
  const [uploadedIcons, setUploadedIcons] = useState<GoalIconMeta[]>([])
  const [maxUploads, setMaxUploads] = useState(MAX_UPLOADS_PER_GOAL)
  const [iconBusy, setIconBusy] = useState(false)
  const [sourceUi, setSourceUi] = useState<IconSourceUi>(() => resolveIconSourceUi(goal))
  const [pendingCrop, setPendingCrop] = useState<PendingCrop | null>(null)
  const [pendingRemoveIconId, setPendingRemoveIconId] = useState<string | null>(null)
  const [isCropSaving, setIsCropSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const uploadFull = uploadedIcons.length >= maxUploads
  const previewStyle: GoalStyle = {
    color,
    icon_type: sourceUi === 'upload' && goal?.icon_type === 'upload' ? 'upload' : 'emoji',
    icon:
      sourceUi === 'upload' && goal?.icon_type === 'upload'
        ? goal.icon
        : emoji || '🎯',
  }

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
    setSourceUi(resolveIconSourceUi(goal))
  }, [goal?.id, goal?.icon_type])

  useEffect(() => {
    if (!goal) {
      setUploadedIcons([])
      return
    }
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
  }, [goal?.id])

  const applyUploadStyle = async (iconId: string) => {
    if (!goal || !onGoalChange) {
      return
    }
    setIconBusy(true)
    setError(null)
    try {
      const updated = await patchGoal(goal.id, { icon_type: 'upload', icon: iconId })
      onGoalChange(updated)
      setSourceUi('upload')
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.failedSave'))
    } finally {
      setIconBusy(false)
    }
  }

  const handleSourceChange = async (next: IconSourceUi) => {
    if (next === 'emoji') {
      setSourceUi('emoji')
      if (goal && onGoalChange && goal.icon_type !== 'emoji') {
        setIconBusy(true)
        setError(null)
        try {
          const updated = await patchGoal(goal.id, {
            icon_type: 'emoji',
            icon: emoji || '🎯',
          })
          onGoalChange(updated)
        } catch (err) {
          setError(err instanceof Error ? err.message : t('errors.failedSave'))
        } finally {
          setIconBusy(false)
        }
      }
      return
    }
    if (uploadedIcons.length === 0) {
      setSourceUi('upload')
      return
    }
    await applyUploadStyle(uploadedIcons[uploadedIcons.length - 1].id)
  }

  const handleEmojiSelect = (next: string) => {
    onEmojiChange(next)
    setSourceUi('emoji')
  }

  const handleUploadSelectFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || !goal) {
      return
    }
    setError(null)
    const loaded = await readMoodIconImage(file)
    if ('error' in loaded) {
      setError(cropValidationMessage(loaded.error))
      return
    }
    setPendingCrop({
      image: loaded.image,
      objectUrl: loaded.objectUrl,
      fileName: file.name || 'icon.png',
    })
  }

  const handleRecropUpload = async (icon: GoalIconMeta) => {
    if (!goal) {
      return
    }
    setError(null)
    try {
      const blob = await fetchGoalIconBlob(icon.id)
      const loaded = await readMoodIconBlobForCrop(blob)
      if ('error' in loaded) {
        setError(cropValidationMessage(loaded.error))
        return
      }
      setPendingCrop({
        image: loaded.image,
        objectUrl: loaded.objectUrl,
        fileName: icon.original_name,
        replaceIconId: icon.id,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : t('moodPreferences.uploadFailed'))
    }
  }

  const handleCropSave = async (croppedFile: File) => {
    if (!pendingCrop || !goal || !onGoalChange) {
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
        setSourceUi('upload')
      }
      closeCropEditor()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('moodPreferences.uploadFailed'))
      setIsCropSaving(false)
    }
  }

  const handleRemoveUpload = async (iconId: string) => {
    if (!goal || !onGoalChange) {
      return
    }
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
        if (updated.icon_type !== 'upload') {
          setSourceUi('emoji')
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('moodPreferences.uploadFailed'))
    } finally {
      setIconBusy(false)
    }
  }

  const busy = disabled || iconBusy
  const label = goal?.label ?? t('goalsPage.appearance')

  return (
    <div className="goal-icon-editor appearance-editor">
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
      {pendingRemoveIconId ? (
        <ConfirmDialog
          open
          title={t('confirm.removeGoalIconTitle')}
          message={t('confirm.removeGoalIcon')}
          confirmLabel={t('moodPreferences.removeIcon')}
          isBusy={iconBusy}
          onCancel={() => setPendingRemoveIconId(null)}
          onConfirm={() => {
            const iconId = pendingRemoveIconId
            setPendingRemoveIconId(null)
            void handleRemoveUpload(iconId)
          }}
        />
      ) : null}

      <div className="mood-preferences-preview">
        <span
          className="mood-preferences-swatch"
          style={{ backgroundColor: color }}
          aria-hidden
        />
        <span className="mood-preferences-icon-slot" style={{ filter: moodGlowFilter(color) }}>
          <GoalIcon style={previewStyle} className="mood-preferences-emoji" />
        </span>
      </div>

      <ColorPicker
        id={goal ? `goal-color-${goal.id}` : 'goal-color-new'}
        value={color}
        onChange={onColorChange}
        disabled={busy}
        colorLabel={t('goalsPage.colorFor', { label })}
        hexLabel={t('goalsPage.hexFor', { label })}
      />

      <fieldset className="mood-preferences-icon-source" disabled={busy}>
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
            onClick={() => void handleSourceChange('emoji')}
          >
            {t('moodPreferences.iconTypeEmoji')}
          </button>
          <button
            type="button"
            className={`segmented-control-option${sourceUi === 'upload' ? ' is-active' : ''}`}
            aria-pressed={sourceUi === 'upload'}
            disabled={!goal}
            title={!goal ? t('goalsPage.uploadAfterCreate') : undefined}
            onClick={() => void handleSourceChange('upload')}
          >
            {t('moodPreferences.iconTypeUpload')}
          </button>
        </div>

        <div className="mood-preferences-icon-panel">
          {sourceUi === 'emoji' ? (
            <EmojiPicker
              value={emoji}
              groups={GOAL_EMOJI_GROUPS}
              groupLabel={(groupId) => t(`goalsPage.emojiGroup${groupId}`)}
              onChange={handleEmojiSelect}
              disabled={busy}
              label={t('moodPreferences.chooseEmoji')}
            />
          ) : goal ? (
            <div className="mood-preferences-upload-section">
              <div className="mood-preferences-upload-row">
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
                          disabled={busy}
                          onClick={() => {
                            if (selected) {
                              void handleRecropUpload(icon)
                            } else {
                              void applyUploadStyle(icon.id)
                            }
                          }}
                        >
                          <span style={{ filter: moodGlowFilter(color) }}>
                            <GoalIcon
                              style={{
                                color,
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
                          disabled={busy}
                          onClick={() => setPendingRemoveIconId(icon.id)}
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
                        className={`mood-preferences-upload-add${busy ? ' is-disabled' : ''}`}
                        aria-label={t('goalsPage.uploadIcon')}
                      >
                        <span aria-hidden="true">+</span>
                        <input
                          type="file"
                          accept="image/jpeg,image/png,image/webp,image/gif"
                          className="mood-preferences-upload-input"
                          disabled={busy}
                          onChange={(event) => void handleUploadSelectFile(event)}
                        />
                      </label>
                    </div>
                  ) : null}
                </div>
                <p className="form-hint mood-preferences-upload-count">
                  {uploadFull
                    ? t('goalsPage.uploadSlotsFull', { max: String(maxUploads) })
                    : t('goalsPage.uploadCount', {
                        remaining: String(maxUploads - uploadedIcons.length),
                        max: String(maxUploads),
                      })}
                </p>
              </div>
            </div>
          ) : (
            <p className="form-hint">{t('goalsPage.uploadAfterCreate')}</p>
          )}
        </div>
      </fieldset>
    </div>
  )
}
