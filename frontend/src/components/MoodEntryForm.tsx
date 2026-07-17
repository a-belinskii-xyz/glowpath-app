import { type ChangeEvent, type FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { listGoals } from '../api/goals'
import {
  createMoodEntry,
  deleteMoodEntryAttachment,
  patchMoodEntry,
  uploadMoodEntryAttachment,
} from '../api/moodEntries'
import { listNoteTemplates } from '../api/noteTemplates'
import { listTagGroups } from '../api/tagGroups'
import { Alert } from './Alert'
import { GoalIcon } from './GoalIcon'
import { MarkdownNoteEditor } from './MarkdownNoteEditor'
import { MoodScoreIcon } from './MoodScoreIcon'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { useMoodPreferences } from '../context/MoodPreferencesContext'
import { ApiError } from '../lib/errors'
import {
  datetimeLocalToIso,
  entriesListPathForInstant,
  isoToDatetimeLocal,
  nowDatetimeLocal,
} from '../lib/datetime'
import { getMoodScoreOptions } from '../lib/moodScale'
import type { GoalPublic } from '../types/goal'
import type { AttachmentPublic, MoodEntryPublic } from '../types/mood'
import { getStoredMoodEntrySource } from '../lib/moodEntrySource'
import type { NoteTemplatePublic } from '../types/noteTemplate'
import type { TagGroupPublic } from '../types/tag'

type PendingFile = {
  kind: 'photo' | 'audio'
  file: File
}

type MoodEntryFormProps = {
  mode: 'create' | 'edit'
  initialEntry?: MoodEntryPublic
  /** Prefill `datetime-local` in create mode (e.g. from calendar day). */
  initialRecordedAtLocal?: string
}

export function MoodEntryForm({
  mode,
  initialEntry,
  initialRecordedAtLocal,
}: MoodEntryFormProps) {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { locale, t } = useLocale()
  const { scores } = useMoodPreferences()
  const timeZone = user?.timezone ?? 'UTC'
  const moodScoreOptions = getMoodScoreOptions(locale, scores)

  const [score, setScore] = useState(initialEntry?.score ?? 4)
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
  const [tagGroups, setTagGroups] = useState<TagGroupPublic[]>([])
  const [goals, setGoals] = useState<GoalPublic[]>([])
  const [noteTemplates, setNoteTemplates] = useState<NoteTemplatePublic[]>([])
  const [showOtherGroups, setShowOtherGroups] = useState(false)
  const [showOtherGoals, setShowOtherGoals] = useState(false)
  const [existingAttachments, setExistingAttachments] = useState<AttachmentPublic[]>(
    initialEntry?.attachments ?? [],
  )
  const [pendingPhotos, setPendingPhotos] = useState<PendingFile[]>([])
  const [pendingAudio, setPendingAudio] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoadingTags, setIsLoadingTags] = useState(true)
  const [isLoadingGoals, setIsLoadingGoals] = useState(true)

  useEffect(() => {
    const loadCatalog = async () => {
      setIsLoadingTags(true)
      setIsLoadingGoals(true)
      try {
        const [tagsResponse, templatesResponse, goalsResponse] = await Promise.all([
          listTagGroups(),
          listNoteTemplates(),
          listGoals(),
        ])
        setTagGroups(tagsResponse.items)
        setNoteTemplates(templatesResponse.items)
        setGoals(goalsResponse.items)
        const selectedIds = new Set(initialEntry?.tags.map((tag) => tag.id) ?? [])
        const hasSelectedOther = tagsResponse.items.some(
          (group) =>
            !group.show_on_entry && group.tags.some((tag) => selectedIds.has(tag.id)),
        )
        if (hasSelectedOther) {
          setShowOtherGroups(true)
        }
        const selectedGoalIdSet = new Set(initialEntry?.goals.map((goal) => goal.id) ?? [])
        const hasSelectedOtherGoal = goalsResponse.items.some(
          (goal) => !goal.show_on_entry && selectedGoalIdSet.has(goal.id),
        )
        if (hasSelectedOtherGoal) {
          setShowOtherGoals(true)
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError(t('errors.verifyToManageEntries'))
        } else {
          setError(err instanceof Error ? err.message : t('errors.failedLoadTags'))
        }
      } finally {
        setIsLoadingTags(false)
        setIsLoadingGoals(false)
      }
    }
    void loadCatalog()
  }, [initialEntry, locale, t])

  const entryDate = recordedAtLocal.split('T')[0] ?? ''
  const activeGoals = goals.filter(
    (goal) =>
      goal.starts_on <= entryDate && (goal.ends_on === null || goal.ends_on >= entryDate),
  )
  const primaryGroups = tagGroups.filter((group) => group.show_on_entry)
  const otherGroups = tagGroups.filter((group) => !group.show_on_entry)
  const primaryGoals = activeGoals.filter((goal) => goal.show_on_entry)
  const otherGoals = activeGoals.filter((goal) => !goal.show_on_entry)

  const toggleTag = (tagId: string) => {
    setSelectedTagIds((current) =>
      current.includes(tagId) ? current.filter((id) => id !== tagId) : [...current, tagId],
    )
  }

  const toggleGoal = (goalId: string) => {
    setSelectedGoalIds((current) =>
      current.includes(goalId) ? current.filter((id) => id !== goalId) : [...current, goalId],
    )
  }

  const insertTemplate = (template: NoteTemplatePublic) => {
    const templateBody = template.body.trim()
    if (!templateBody) {
      return
    }
    setNote(templateBody)
  }

  const renderTagGroup = (group: TagGroupPublic) => (
    <fieldset key={group.id} className="tag-group">
      <legend className="tag-group-label">{group.label}</legend>
      <div className="tag-chips">
        {group.tags.map((tag) => {
          const selected = selectedTagIds.includes(tag.id)
          return (
            <button
              key={tag.id}
              type="button"
              className={`tag-chip${selected ? ' tag-chip-selected' : ''}`}
              onClick={() => toggleTag(tag.id)}
              aria-pressed={selected}
            >
              {tag.label}
            </button>
          )
        })}
      </div>
    </fieldset>
  )

  const renderGoalChip = (goal: GoalPublic) => {
    const selected = selectedGoalIds.includes(goal.id)
    return (
      <button
        key={goal.id}
        type="button"
        className={`tag-chip goal-chip${selected ? ' tag-chip-selected' : ''}`}
        onClick={() => toggleGoal(goal.id)}
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
          {t('goalsPage.weekProgress', {
            done: goal.completed_this_week,
            target: goal.times_per_week,
          })}
        </span>
      </button>
    )
  }

  const photoCount =
    existingAttachments.filter((item) => item.kind === 'photo').length + pendingPhotos.length
  const hasAudio =
    existingAttachments.some((item) => item.kind === 'audio') || pendingAudio !== null

  const handlePhotoChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? [])
    if (photoCount + files.length > 5) {
      setError(t('errors.photosLimit'))
      return
    }
    setPendingPhotos((current) => [
      ...current,
      ...files.map((file) => ({ kind: 'photo' as const, file })),
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
      return
    }
    setPendingAudio(file)
    event.target.value = ''
  }

  const removePendingPhoto = (index: number) => {
    setPendingPhotos((current) => current.filter((_, itemIndex) => itemIndex !== index))
  }

  const removeExistingAttachment = async (attachmentId: string) => {
    if (!initialEntry) {
      return
    }
    try {
      await deleteMoodEntryAttachment(initialEntry.id, attachmentId)
      setExistingAttachments((current) => current.filter((item) => item.id !== attachmentId))
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.failedRemoveAttachment'))
    }
  }

  const uploadPendingFiles = async (entryId: string) => {
    for (const pending of pendingPhotos) {
      await uploadMoodEntryAttachment(entryId, 'photo', pending.file)
    }
    if (pendingAudio) {
      await uploadMoodEntryAttachment(entryId, 'audio', pendingAudio)
    }
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    const activeGoalIdSet = new Set(activeGoals.map((goal) => goal.id))
    const sessionSource = mode === 'create' ? getStoredMoodEntrySource() : undefined
    const payload = {
      score,
      recorded_at: datetimeLocalToIso(recordedAtLocal, timeZone),
      note: note.trim() ? note.trim() : null,
      tag_ids: selectedTagIds,
      goal_ids: selectedGoalIds.filter((id) => activeGoalIdSet.has(id)),
      ...(sessionSource ? { source: sessionSource } : {}),
    }

    try {
      let savedId = initialEntry?.id
      if (mode === 'create') {
        const created = await createMoodEntry(payload)
        await uploadPendingFiles(created.id)
        savedId = created.id
      } else if (initialEntry) {
        await patchMoodEntry(initialEntry.id, payload)
        await uploadPendingFiles(initialEntry.id)
      }
      navigate(
        entriesListPathForInstant(payload.recorded_at, timeZone, savedId),
      )
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError(t('errors.verifyToSaveEntries'))
      } else {
        setError(err instanceof Error ? err.message : t('errors.failedSaveEntry'))
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const kindLabel = (kind: string) =>
    kind === 'photo' ? t('entries.kindPhoto') : kind === 'audio' ? t('entries.kindAudio') : kind

  return (
    <form className="form mood-entry-form" onSubmit={handleSubmit}>
      {error ? <Alert variant="error">{error}</Alert> : null}

      <fieldset className="form-field">
        <legend className="form-label">{t('entries.moodScore')}</legend>
        <div className="score-picker">
          {moodScoreOptions.map((option) => {
            const isSelected = score === option.score
            return (
            <button
              key={option.score}
              type="button"
              className={`score-option${isSelected ? ' score-option-selected' : ''}`}
              style={{
                borderColor: isSelected ? option.color : undefined,
                background: isSelected ? `${option.color}1a` : undefined,
              }}
              onClick={() => setScore(option.score)}
              aria-pressed={isSelected}
            >
              <MoodScoreIcon
                style={option.style}
                className="score-emoji"
                fallbackScore={option.score}
              />
              <span className="score-label">{option.label}</span>
            </button>
            )
          })}
        </div>
      </fieldset>

      <label className="form-field">
        <span className="form-label">{t('entries.recordedAt')}</span>
        <input
          className="form-input"
          type="datetime-local"
          value={recordedAtLocal}
          onChange={(event) => setRecordedAtLocal(event.target.value)}
          required
        />
      </label>

      <div className="note-template-insert">
        <div className="note-template-insert-header">
          <span className="form-label">{t('entries.insertTemplate')}</span>
          <Link to="/templates" className="button button-secondary button-small">
            {t('entries.manageTemplates')}
          </Link>
        </div>
        {noteTemplates.length > 0 ? (
          <div className="note-template-chips">
            {noteTemplates.map((template) => (
              <button
                key={template.id}
                type="button"
                className="tag-chip"
                onClick={() => insertTemplate(template)}
              >
                {template.label}
              </button>
            ))}
          </div>
        ) : (
          <p className="muted">{t('entries.noTemplates')}</p>
        )}
      </div>

      <MarkdownNoteEditor
        value={note}
        onChange={setNote}
        label={t('common.note')}
        placeholder={t('markdown.placeholder')}
      />

      <section className="tag-sections">
        <div className="tag-sections-header">
          <h2 className="section-title">{t('common.goals')}</h2>
          <Link to="/goals" className="button button-secondary button-small">
            {t('entries.manageGoals')}
          </Link>
        </div>
        {isLoadingGoals ? (
          <p className="muted">{t('common.loadingGoals')}</p>
        ) : activeGoals.length === 0 ? (
          <p className="muted">{t('entries.noGoalsForDate')}</p>
        ) : (
          <>
            <div className="tag-chips">{primaryGoals.map(renderGoalChip)}</div>
            {otherGoals.length > 0 ? (
              <div className="tag-other-section">
                <button
                  type="button"
                  className="button button-secondary button-small"
                  onClick={() => setShowOtherGoals((current) => !current)}
                  aria-expanded={showOtherGoals}
                >
                  {showOtherGoals ? t('entries.hideOther') : t('entries.other')}
                </button>
                {showOtherGoals ? (
                  <div className="tag-chips">{otherGoals.map(renderGoalChip)}</div>
                ) : null}
              </div>
            ) : null}
          </>
        )}
      </section>

      <section className="tag-sections">
        <div className="tag-sections-header">
          <h2 className="section-title">{t('common.tags')}</h2>
          <Link to="/tags" className="button button-secondary button-small">
            {t('entries.manageTags')}
          </Link>
        </div>
        {isLoadingTags ? (
          <p className="muted">{t('common.loadingTags')}</p>
        ) : (
          <>
            {primaryGroups.map(renderTagGroup)}
            {otherGroups.length > 0 ? (
              <div className="tag-other-section">
                <button
                  type="button"
                  className="button button-secondary button-small"
                  onClick={() => setShowOtherGroups((current) => !current)}
                  aria-expanded={showOtherGroups}
                >
                  {showOtherGroups ? t('entries.hideOther') : t('entries.other')}
                </button>
                {showOtherGroups ? otherGroups.map(renderTagGroup) : null}
              </div>
            ) : null}
          </>
        )}
      </section>

      <section className="attachments-section">
        <h2 className="section-title">{t('entries.attachments')}</h2>
        <div className="attachment-inputs">
          <label className="form-field">
            <span className="form-label">{t('entries.photos', { count: photoCount })}</span>
            <input
              className="form-input"
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              multiple
              onChange={handlePhotoChange}
              disabled={photoCount >= 5}
            />
          </label>
          <label className="form-field">
            <span className="form-label">{t('entries.audio', { count: hasAudio ? 1 : 0 })}</span>
            <input
              className="form-input"
              type="file"
              accept="audio/mpeg,audio/mp4,audio/wav,audio/ogg,audio/webm,audio/aac"
              onChange={handleAudioChange}
              disabled={hasAudio}
            />
          </label>
        </div>
        <ul className="attachment-list">
          {existingAttachments.map((attachment) => (
            <li key={attachment.id}>
              <span>
                {t('entries.attachmentItem', {
                  kind: kindLabel(attachment.kind),
                  name: attachment.original_name,
                })}
              </span>
              {mode === 'edit' ? (
                <button
                  type="button"
                  className="link-button"
                  onClick={() => void removeExistingAttachment(attachment.id)}
                >
                  {t('common.remove')}
                </button>
              ) : null}
            </li>
          ))}
          {pendingPhotos.map((pending, index) => (
            <li key={`photo-${pending.file.name}-${index}`}>
              <span>
                {t('entries.attachmentItem', {
                  kind: t('entries.kindPhoto'),
                  name: pending.file.name,
                })}
              </span>
              <button type="button" className="link-button" onClick={() => removePendingPhoto(index)}>
                {t('common.remove')}
              </button>
            </li>
          ))}
          {pendingAudio ? (
            <li>
              <span>
                {t('entries.attachmentItem', {
                  kind: t('entries.kindAudio'),
                  name: pendingAudio.name,
                })}
              </span>
              <button type="button" className="link-button" onClick={() => setPendingAudio(null)}>
                {t('common.remove')}
              </button>
            </li>
          ) : null}
        </ul>
      </section>

      <div className="button-row">
        <button className="button" type="submit" disabled={isSubmitting}>
          {isSubmitting
            ? t('common.saving')
            : mode === 'create'
              ? t('entries.createEntry')
              : t('entries.saveChanges')}
        </button>
        <button
          className="button button-secondary"
          type="button"
          onClick={() =>
            navigate(
              initialEntry
                ? entriesListPathForInstant(initialEntry.recorded_at, timeZone, initialEntry.id)
                : '/',
            )
          }
        >
          {t('common.cancel')}
        </button>
      </div>
    </form>
  )
}
