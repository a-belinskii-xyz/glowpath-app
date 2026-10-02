import { useState, type FormEvent } from 'react'

import { patchStudioIcon, replaceStudioIconImage } from '../../api/marketplace'
import { useLocale } from '../../context/LocaleContext'
import type {
  CatalogIconPublic,
  IconUsage,
  SearchTagPublic,
  StudioIconPatch,
} from '../../types/marketplace'
import { ChipToggleRow } from './ChipToggleRow'
import { ACCEPTED_ICON_TYPES, ICON_USAGES, MAX_ICON_COLORS, MOOD_SCORES } from './iconFields'

type Draft = {
  en: string
  ru: string
  colors: string[]
  scores: number[]
  usage: IconUsage[]
  tags: string[]
}

function draftFromIcon(icon: CatalogIconPublic): Draft {
  return {
    en: icon.labels.en ?? icon.label,
    ru: icon.labels.ru ?? '',
    colors: icon.suggested_colors.length > 0 ? [...icon.suggested_colors] : ['#94a3b8'],
    scores: [...icon.suggested_mood_scores],
    usage: [...icon.suggested_usage],
    tags: icon.search_tags.map((tag) => tag.slug),
  }
}

type StaffIconEditorProps = {
  icon: CatalogIconPublic
  searchTags: SearchTagPublic[]
  busy: boolean
  /** Runs a request through the pack editor (busy state, errors, reload). */
  run: (key: string, action: () => Promise<unknown>, successMessage?: string) => Promise<void>
  onImageChanged: () => void
  onClose: () => void
}

export function StaffIconEditor({
  icon,
  searchTags,
  busy,
  run,
  onImageChanged,
  onClose,
}: StaffIconEditorProps) {
  const { t } = useLocale()
  const [draft, setDraft] = useState<Draft>(() => draftFromIcon(icon))
  const [fileInputKey, setFileInputKey] = useState(0)

  const save = (event: FormEvent) => {
    event.preventDefault()
    const en = draft.en.trim()
    const body: StudioIconPatch = {
      labels: { en, ru: draft.ru.trim() || en },
      suggested_colors: draft.colors,
      suggested_mood_scores: draft.scores,
      suggested_usage: draft.usage,
      search_tag_slugs: draft.tags,
    }
    void run(
      'icon',
      async () => {
        await patchStudioIcon(icon.id, body)
        onClose()
      },
      t('staff.iconSaved'),
    )
  }

  const replaceFile = (file: File | undefined) => {
    setFileInputKey((key) => key + 1)
    if (!file) return
    void run('replace', async () => {
      await replaceStudioIconImage(icon.id, file)
      onImageChanged()
    })
  }

  const setColor = (index: number, value: string) =>
    setDraft({ ...draft, colors: draft.colors.map((color, i) => (i === index ? value : color)) })

  return (
    <form className="staff-icon-editor" onSubmit={save}>
      <h4 className="staff-subtitle">{t('staff.editIconTitle', { name: icon.label })}</h4>
      <div className="staff-form-grid">
        <label className="form-field">
          <span className="form-label">{t('staff.labelEn')}</span>
          <input
            className="form-input"
            value={draft.en}
            required
            onChange={(event) => setDraft({ ...draft, en: event.target.value })}
          />
        </label>
        <label className="form-field">
          <span className="form-label">{t('staff.labelRu')}</span>
          <input
            className="form-input"
            value={draft.ru}
            onChange={(event) => setDraft({ ...draft, ru: event.target.value })}
          />
        </label>
      </div>

      <div>
        <span className="form-label">{t('staff.usage')}</span>
        <p className="form-hint">{t('staff.usageHint')}</p>
        <ChipToggleRow
          options={ICON_USAGES}
          selected={draft.usage}
          label={(usage) => t(`staff.usageOptions.${usage}`)}
          onChange={(usage) => setDraft({ ...draft, usage })}
        />
      </div>

      <div>
        <span className="form-label">{t('staff.scores')}</span>
        <ChipToggleRow
          options={MOOD_SCORES}
          selected={draft.scores}
          label={(score) => String(score)}
          onChange={(scores) => setDraft({ ...draft, scores })}
        />
      </div>

      <div>
        <span className="form-label">{t('staff.colors')}</span>
        <div className="staff-chip-row">
          {draft.colors.map((color, index) => (
            <span key={index} className="staff-color-field">
              <input
                type="color"
                value={color}
                aria-label={t('staff.colors')}
                onChange={(event) => setColor(index, event.target.value)}
              />
              {draft.colors.length > 1 ? (
                <button
                  type="button"
                  className="button button-secondary button-small"
                  aria-label={t('staff.removeColor', { color })}
                  onClick={() =>
                    setDraft({ ...draft, colors: draft.colors.filter((_, i) => i !== index) })
                  }
                >
                  ×
                </button>
              ) : null}
            </span>
          ))}
          {draft.colors.length < MAX_ICON_COLORS ? (
            <button
              type="button"
              className="button button-secondary button-small"
              onClick={() =>
                setDraft({ ...draft, colors: [...draft.colors, draft.colors[draft.colors.length - 1] ?? '#94a3b8'] })
              }
            >
              {t('staff.addColor')}
            </button>
          ) : null}
        </div>
      </div>

      {searchTags.length > 0 ? (
        <div>
          <span className="form-label">{t('staff.tags')}</span>
          <ChipToggleRow
            options={searchTags.map((tag) => tag.slug)}
            selected={draft.tags}
            label={(slug) => searchTags.find((tag) => tag.slug === slug)?.label ?? slug}
            onChange={(tags) => setDraft({ ...draft, tags })}
          />
        </div>
      ) : null}

      <div>
        <label className="button button-secondary button-small staff-file-button">
          {busy ? t('common.saving') : t('staff.replaceFile')}
          <input
            key={fileInputKey}
            type="file"
            accept={ACCEPTED_ICON_TYPES}
            className="visually-hidden"
            disabled={busy}
            onChange={(event) => replaceFile(event.target.files?.[0])}
          />
        </label>
        <p className="form-hint">{t('staff.replaceFileHint')}</p>
      </div>

      <div className="staff-icon-actions">
        <button type="submit" className="button button-small" disabled={busy}>
          {t('common.save')}
        </button>
        <button type="button" className="button button-secondary button-small" onClick={onClose}>
          {t('common.cancel')}
        </button>
      </div>
    </form>
  )
}
