import { type ChangeEvent, type FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import {
  createMoodEntry,
  deleteMoodEntryAttachment,
  patchMoodEntry,
  uploadMoodEntryAttachment,
} from '../api/moodEntries'
import { listTagGroups } from '../api/tagGroups'
import { Alert } from './Alert'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../lib/errors'
import {
  datetimeLocalToIso,
  isoToDatetimeLocal,
  nowDatetimeLocal,
} from '../lib/datetime'
import { MOOD_SCORE_OPTIONS } from '../lib/moodScale'
import type { AttachmentPublic, MoodEntryPublic } from '../types/mood'
import type { TagGroupPublic } from '../types/tag'

type PendingFile = {
  kind: 'photo' | 'audio'
  file: File
}

type MoodEntryFormProps = {
  mode: 'create' | 'edit'
  initialEntry?: MoodEntryPublic
}

export function MoodEntryForm({ mode, initialEntry }: MoodEntryFormProps) {
  const navigate = useNavigate()
  const { user } = useAuth()
  const timeZone = user?.timezone ?? 'UTC'

  const [score, setScore] = useState(initialEntry?.score ?? 4)
  const [recordedAtLocal, setRecordedAtLocal] = useState(
    initialEntry ? isoToDatetimeLocal(initialEntry.recorded_at, timeZone) : nowDatetimeLocal(timeZone),
  )
  const [note, setNote] = useState(initialEntry?.note ?? '')
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>(
    initialEntry?.tags.map((tag) => tag.id) ?? [],
  )
  const [tagGroups, setTagGroups] = useState<TagGroupPublic[]>([])
  const [showOtherGroups, setShowOtherGroups] = useState(false)
  const [existingAttachments, setExistingAttachments] = useState<AttachmentPublic[]>(
    initialEntry?.attachments ?? [],
  )
  const [pendingPhotos, setPendingPhotos] = useState<PendingFile[]>([])
  const [pendingAudio, setPendingAudio] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoadingTags, setIsLoadingTags] = useState(true)

  useEffect(() => {
    const loadTags = async () => {
      try {
        const response = await listTagGroups()
        setTagGroups(response.items)
        const selectedIds = new Set(initialEntry?.tags.map((tag) => tag.id) ?? [])
        const hasSelectedOther = response.items.some(
          (group) =>
            !group.show_on_entry && group.tags.some((tag) => selectedIds.has(tag.id)),
        )
        if (hasSelectedOther) {
          setShowOtherGroups(true)
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError('Verify your email before managing mood entries.')
        } else {
          setError(err instanceof Error ? err.message : 'Failed to load tags')
        }
      } finally {
        setIsLoadingTags(false)
      }
    }
    void loadTags()
  }, [initialEntry])

  const primaryGroups = tagGroups.filter((group) => group.show_on_entry)
  const otherGroups = tagGroups.filter((group) => !group.show_on_entry)

  const toggleTag = (tagId: string) => {
    setSelectedTagIds((current) =>
      current.includes(tagId) ? current.filter((id) => id !== tagId) : [...current, tagId],
    )
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

  const photoCount =
    existingAttachments.filter((item) => item.kind === 'photo').length + pendingPhotos.length
  const hasAudio =
    existingAttachments.some((item) => item.kind === 'audio') || pendingAudio !== null

  const handlePhotoChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? [])
    if (photoCount + files.length > 5) {
      setError('You can attach up to 5 photos per entry.')
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
      setError('Only one audio file is allowed per entry.')
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
      setError(err instanceof Error ? err.message : 'Failed to remove attachment')
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

    const payload = {
      score,
      recorded_at: datetimeLocalToIso(recordedAtLocal, timeZone),
      note: note.trim() ? note.trim() : null,
      tag_ids: selectedTagIds,
    }

    try {
      if (mode === 'create') {
        const created = await createMoodEntry(payload)
        await uploadPendingFiles(created.id)
      } else if (initialEntry) {
        await patchMoodEntry(initialEntry.id, payload)
        await uploadPendingFiles(initialEntry.id)
      }
      navigate('/')
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError('Verify your email before saving mood entries.')
      } else {
        setError(err instanceof Error ? err.message : 'Failed to save entry')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form className="form mood-entry-form" onSubmit={handleSubmit}>
      {error ? <Alert variant="error">{error}</Alert> : null}

      <fieldset className="form-field">
        <legend className="form-label">Mood score</legend>
        <div className="score-picker">
          {MOOD_SCORE_OPTIONS.map((option) => (
            <button
              key={option.score}
              type="button"
              className={`score-option${score === option.score ? ' score-option-selected' : ''}`}
              onClick={() => setScore(option.score)}
              aria-pressed={score === option.score}
            >
              <span className="score-emoji">{option.emoji}</span>
              <span className="score-label">{option.label}</span>
            </button>
          ))}
        </div>
      </fieldset>

      <label className="form-field">
        <span className="form-label">Recorded at</span>
        <input
          className="form-input"
          type="datetime-local"
          value={recordedAtLocal}
          onChange={(event) => setRecordedAtLocal(event.target.value)}
          required
        />
      </label>

      <label className="form-field">
        <span className="form-label">Note</span>
        <textarea
          className="form-input form-textarea"
          value={note}
          maxLength={500}
          rows={4}
          onChange={(event) => setNote(event.target.value)}
          placeholder="Optional note (max 500 characters)"
        />
        <span className="form-hint">{note.length}/500</span>
      </label>

      <section className="tag-sections">
        <div className="tag-sections-header">
          <h2 className="section-title">Tags</h2>
          <Link to="/tags" className="button button-secondary button-small">
            Manage tags
          </Link>
        </div>
        {isLoadingTags ? (
          <p className="muted">Loading tags…</p>
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
                  {showOtherGroups ? 'Hide other' : 'Other'}
                </button>
                {showOtherGroups ? otherGroups.map(renderTagGroup) : null}
              </div>
            ) : null}
          </>
        )}
      </section>

      <section className="attachments-section">
        <h2 className="section-title">Attachments</h2>
        <div className="attachment-inputs">
          <label className="form-field">
            <span className="form-label">Photos ({photoCount}/5)</span>
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
            <span className="form-label">Audio ({hasAudio ? 1 : 0}/1)</span>
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
                {attachment.kind}: {attachment.original_name}
              </span>
              {mode === 'edit' ? (
                <button
                  type="button"
                  className="link-button"
                  onClick={() => void removeExistingAttachment(attachment.id)}
                >
                  Remove
                </button>
              ) : null}
            </li>
          ))}
          {pendingPhotos.map((pending, index) => (
            <li key={`photo-${pending.file.name}-${index}`}>
              <span>photo: {pending.file.name}</span>
              <button type="button" className="link-button" onClick={() => removePendingPhoto(index)}>
                Remove
              </button>
            </li>
          ))}
          {pendingAudio ? (
            <li>
              <span>audio: {pendingAudio.name}</span>
              <button type="button" className="link-button" onClick={() => setPendingAudio(null)}>
                Remove
              </button>
            </li>
          ) : null}
        </ul>
      </section>

      <div className="button-row">
        <button className="button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Saving…' : mode === 'create' ? 'Create entry' : 'Save changes'}
        </button>
        <button className="button button-secondary" type="button" onClick={() => navigate('/')}>
          Cancel
        </button>
      </div>
    </form>
  )
}
