import { useState, type FormEvent } from 'react'

import {
  createStaffAchievement,
  patchStaffAchievement,
  uploadStaffAchievementIcon,
} from '../../api/staff'
import { useLocale } from '../../context/LocaleContext'
import { formatApiError } from '../../lib/errors'
import type {
  AchievementStatus,
  CriteriaSpec,
  StaffAchievementPublic,
} from '../../types/achievement'
import type { PackCardPublic } from '../../types/marketplace'
import { AchievementIcon } from '../AchievementIcon'
import { Alert } from '../Alert'
import { PageErrorAlert } from '../PageErrorAlert'
import {
  ACHIEVEMENT_CATEGORIES,
  buildPayload,
  draftFromAchievement,
  emptyDraft,
  type AchievementDraft,
} from './achievementDraft'
import { ACCEPTED_ICON_TYPES } from './iconFields'
import { PackStatusPill } from './PackStatusPill'
import { StaffCriteriaFields } from './StaffCriteriaFields'
import { StaffRewardsFields } from './StaffRewardsFields'

type StaffAchievementEditorProps = {
  /** null opens an empty form for a new achievement. */
  achievement: StaffAchievementPublic | null
  specs: CriteriaSpec[]
  packs: PackCardPublic[]
  onSaved: (achievement: StaffAchievementPublic) => void
  onBack: () => void
}

export function StaffAchievementEditor({
  achievement: initial,
  specs,
  packs,
  onSaved,
  onBack,
}: StaffAchievementEditorProps) {
  const { t } = useLocale()
  const [achievement, setAchievement] = useState(initial)
  const [draft, setDraft] = useState<AchievementDraft>(() =>
    initial ? draftFromAchievement(initial) : emptyDraft(specs),
  )
  const [pendingImage, setPendingImage] = useState<File | null>(null)
  const [fileInputKey, setFileInputKey] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const spec = specs.find((item) => item.type === draft.criteriaType)

  const set = <K extends keyof AchievementDraft>(key: K, value: AchievementDraft[K]) =>
    setDraft((current) => ({ ...current, [key]: value }))

  const run = async (action: () => Promise<StaffAchievementPublic>, message: string) => {
    if (busy) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const saved = await action()
      setAchievement(saved)
      onSaved(saved)
      setNotice(message)
    } catch (err) {
      setError(formatApiError(err, t, 'errors.requestFailed'))
    } finally {
      setBusy(false)
    }
  }

  const save = (event: FormEvent) => {
    event.preventDefault()
    const payload = buildPayload(draft, spec)
    void run(async () => {
      let saved: StaffAchievementPublic
      if (achievement) {
        // The slug is fixed after creation. Keep an uploaded image unless staff
        // typed a different emoji.
        const keepImage = achievement.icon_type === 'image' && draft.emoji === achievement.icon
        saved = await patchStaffAchievement(achievement.id, {
          ...payload,
          slug: undefined,
          emoji: keepImage ? undefined : payload.emoji,
        })
      } else {
        saved = await createStaffAchievement(payload)
      }
      if (pendingImage) {
        saved = await uploadStaffAchievementIcon(saved.id, pendingImage)
        setPendingImage(null)
      }
      setDraft(draftFromAchievement(saved))
      return saved
    }, achievement ? t('staffAchievements.saved') : t('staffAchievements.created'))
  }

  const setStatus = (status: AchievementStatus) => {
    if (!achievement) return
    void run(() => patchStaffAchievement(achievement.id, { status }), t('staffAchievements.saved'))
  }

  const pickImage = (file: File | undefined) => {
    setFileInputKey((key) => key + 1)
    if (!file) return
    if (!achievement) {
      setPendingImage(file)
      return
    }
    void run(() => uploadStaffAchievementIcon(achievement.id, file), t('staffAchievements.saved'))
  }

  const useEmoji = () => {
    if (!achievement) return
    void run(
      () => patchStaffAchievement(achievement.id, { emoji: draft.emoji.trim() || '🏆' }),
      t('staffAchievements.saved'),
    )
  }

  const textField = (
    key: 'nameEn' | 'nameRu' | 'descriptionEn' | 'descriptionRu',
    label: string,
    required = false,
  ) => (
    <label className="form-field">
      <span className="form-label">{label}</span>
      <input
        className="form-input"
        value={draft[key]}
        maxLength={200}
        required={required}
        placeholder={required ? undefined : t('staffAchievements.ruHint')}
        onChange={(event) => set(key, event.target.value)}
      />
    </label>
  )

  const isImage = achievement?.icon_type === 'image'

  return (
    <div className="staff-panel">
      <div className="staff-toolbar">
        <button type="button" className="button button-secondary button-small" onClick={onBack}>
          ← {t('staffAchievements.back')}
        </button>
        {achievement ? (
          <div className="staff-chip-row">
            <PackStatusPill status={achievement.status} />
            {achievement.status !== 'published' ? (
              <button
                type="button"
                className="button button-small"
                disabled={busy}
                onClick={() => setStatus('published')}
              >
                {t('staffAchievements.publish')}
              </button>
            ) : (
              <button
                type="button"
                className="button button-secondary button-small"
                disabled={busy}
                onClick={() => setStatus('draft')}
              >
                {t('staffAchievements.toDraft')}
              </button>
            )}
            {achievement.status !== 'archived' ? (
              <button
                type="button"
                className="button button-secondary button-small"
                disabled={busy}
                onClick={() => setStatus('archived')}
              >
                {t('staffAchievements.archive')}
              </button>
            ) : null}
          </div>
        ) : null}
      </div>

      <PageErrorAlert error={error} />
      {notice ? <Alert variant="success">{notice}</Alert> : null}
      {achievement && achievement.unlocked_count > 0 ? (
        <p className="form-hint">{t('staffAchievements.editWarning')}</p>
      ) : null}

      <form className="card form staff-card staff-achievement-form" onSubmit={save}>
        <h3 className="staff-subtitle">{t('staffAchievements.sectionText')}</h3>
        <div className="staff-form-grid">
          {textField('nameEn', t('staffAchievements.nameEn'), true)}
          {textField('nameRu', t('staffAchievements.nameRu'))}
          {textField('descriptionEn', t('staffAchievements.descriptionEn'), true)}
          {textField('descriptionRu', t('staffAchievements.descriptionRu'))}
          {achievement ? null : (
            <label className="form-field">
              <span className="form-label">{t('staffAchievements.slug')}</span>
              <input
                className="form-input"
                value={draft.slug}
                maxLength={64}
                pattern="[a-z][a-z0-9_]*"
                onChange={(event) => set('slug', event.target.value)}
              />
              <span className="form-hint">{t('staffAchievements.slugHint')}</span>
            </label>
          )}
        </div>

        <h3 className="staff-subtitle">{t('staffAchievements.sectionLook')}</h3>
        <div className="staff-achievement-look">
          <span className="staff-achievement-preview">
            {achievement ? (
              <AchievementIcon achievement={achievement} version={achievement.updated_at} />
            ) : (
              <span className="achievement-icon">{draft.emoji || '🏆'}</span>
            )}
          </span>
          <div className="staff-form-grid">
            <label className="form-field">
              <span className="form-label">{t('staffAchievements.emoji')}</span>
              <input
                className="form-input"
                value={draft.emoji}
                maxLength={16}
                onChange={(event) => set('emoji', event.target.value)}
              />
              <span className="form-hint">{t('staffAchievements.emojiHint')}</span>
            </label>
            <div className="form-field">
              <label className="button button-secondary button-small staff-file-button">
                {isImage ? t('staffAchievements.replaceImage') : t('staffAchievements.uploadImage')}
                <input
                  key={fileInputKey}
                  type="file"
                  accept={ACCEPTED_ICON_TYPES}
                  className="visually-hidden"
                  disabled={busy}
                  onChange={(event) => pickImage(event.target.files?.[0])}
                />
              </label>
              <span className="form-hint">
                {pendingImage
                  ? t('staffAchievements.imagePending', { name: pendingImage.name })
                  : isImage
                    ? t('staffAchievements.imageActive')
                    : t('staffAchievements.imageHint')}
              </span>
              {isImage ? (
                <button
                  type="button"
                  className="link-button"
                  disabled={busy}
                  onClick={useEmoji}
                >
                  {t('staffAchievements.useEmoji')}
                </button>
              ) : null}
            </div>
          </div>
        </div>
        <div className="staff-form-grid">
          <label className="form-field">
            <span className="form-label">{t('staffAchievements.category')}</span>
            <select
              className="form-input"
              value={draft.category}
              onChange={(event) =>
                set('category', event.target.value as AchievementDraft['category'])
              }
            >
              {ACHIEVEMENT_CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {t(`achievements.category.${category}`)}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span className="form-label">{t('staffAchievements.visibility')}</span>
            <select
              className="form-input"
              value={draft.visibility}
              onChange={(event) =>
                set('visibility', event.target.value as AchievementDraft['visibility'])
              }
            >
              <option value="visible">{t('staffAchievements.visible')}</option>
              <option value="secret">{t('staffAchievements.secret')}</option>
            </select>
          </label>
          <label className="form-field">
            <span className="form-label">{t('staffAchievements.sortOrder')}</span>
            <input
              className="form-input"
              type="number"
              step={1}
              value={draft.sortOrder}
              onChange={(event) => set('sortOrder', event.target.value)}
            />
          </label>
        </div>

        <h3 className="staff-subtitle">{t('staffAchievements.sectionCondition')}</h3>
        <StaffCriteriaFields
          specs={specs}
          draft={draft}
          onChange={(patch) => setDraft((current) => ({ ...current, ...patch }))}
        />

        <h3 className="staff-subtitle">{t('staffAchievements.sectionRewards')}</h3>
        <p className="form-hint">{t('staffAchievements.rewardsHint')}</p>
        <StaffRewardsFields
          rewards={draft.rewards}
          packs={packs}
          onChange={(rewards) => set('rewards', rewards)}
        />

        <div className="staff-form-actions">
          <button type="submit" className="button" disabled={busy}>
            {achievement
              ? busy
                ? t('staffAchievements.saving')
                : t('staffAchievements.save')
              : busy
                ? t('staffAchievements.creating')
                : t('staffAchievements.create')}
          </button>
        </div>
      </form>
    </div>
  )
}
