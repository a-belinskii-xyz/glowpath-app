import { useLocale } from '../../context/LocaleContext'
import type {
  CatalogIconPublic,
  IconUsage,
  SearchTagPublic,
  StudioIconPatch,
} from '../../types/marketplace'
import { ChipToggleRow } from './ChipToggleRow'
import { ICON_USAGES, MAX_ICON_COLORS, MOOD_SCORES } from './iconFields'

export type IconDraft = {
  en: string
  ru: string
  colors: string[]
  scores: number[]
  usage: IconUsage[]
  tags: string[]
}

const DEFAULT_ICON_COLOR = '#94a3b8'

export function emptyIconDraft(previous?: IconDraft): IconDraft {
  // Names are always typed by hand; hints carry over between files of one upload.
  return {
    en: '',
    ru: '',
    colors: previous ? [...previous.colors] : [DEFAULT_ICON_COLOR],
    scores: previous ? [...previous.scores] : [],
    usage: previous ? [...previous.usage] : [],
    tags: previous ? [...previous.tags] : [],
  }
}

export function draftFromIcon(icon: CatalogIconPublic): IconDraft {
  return {
    en: icon.labels.en ?? icon.label,
    ru: icon.labels.ru ?? '',
    colors: icon.suggested_colors.length > 0 ? [...icon.suggested_colors] : [DEFAULT_ICON_COLOR],
    scores: [...icon.suggested_mood_scores],
    usage: [...icon.suggested_usage],
    tags: icon.search_tags.map((tag) => tag.slug),
  }
}

export function iconFieldsFromDraft(draft: IconDraft) {
  return {
    labels: { en: draft.en.trim(), ru: draft.ru.trim() },
    suggested_colors: draft.colors,
    suggested_mood_scores: draft.scores,
    suggested_usage: draft.usage,
    search_tag_slugs: draft.tags,
  } satisfies StudioIconPatch
}

type StaffIconFieldsProps = {
  draft: IconDraft
  searchTags: SearchTagPublic[]
  onChange: (draft: IconDraft) => void
}

/** Name, usage hints, mood scores, colors and search tags of a catalog icon. */
export function StaffIconFields({ draft, searchTags, onChange }: StaffIconFieldsProps) {
  const { t } = useLocale()
  const set = (patch: Partial<IconDraft>) => onChange({ ...draft, ...patch })
  const setColor = (index: number, value: string) =>
    set({ colors: draft.colors.map((color, i) => (i === index ? value : color)) })
  const namesTagOrGoal = draft.usage.includes('tag') || draft.usage.includes('goal')

  return (
    <>
      <div className="staff-form-grid">
        <label className="form-field">
          <span className="form-label">{t('staff.labelRu')}</span>
          <input
            className="form-input"
            value={draft.ru}
            maxLength={100}
            required
            onChange={(event) => set({ ru: event.target.value })}
          />
        </label>
        <label className="form-field">
          <span className="form-label">{t('staff.labelEn')}</span>
          <input
            className="form-input"
            value={draft.en}
            maxLength={100}
            required
            onChange={(event) => set({ en: event.target.value })}
          />
        </label>
      </div>
      <p className="form-hint">
        {namesTagOrGoal ? t('staff.labelTagGoalHint') : t('staff.labelHint')}
      </p>

      <div>
        <span className="form-label">{t('staff.usage')}</span>
        <p className="form-hint">{t('staff.usageHint')}</p>
        <ChipToggleRow
          options={ICON_USAGES}
          selected={draft.usage}
          label={(usage) => t(`staff.usageOptions.${usage}`)}
          onChange={(usage) => set({ usage })}
        />
      </div>

      <div>
        <span className="form-label">{t('staff.scores')}</span>
        <ChipToggleRow
          options={MOOD_SCORES}
          selected={draft.scores}
          label={(score) => String(score)}
          onChange={(scores) => set({ scores })}
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
                  onClick={() => set({ colors: draft.colors.filter((_, i) => i !== index) })}
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
                set({
                  colors: [...draft.colors, draft.colors[draft.colors.length - 1] ?? DEFAULT_ICON_COLOR],
                })
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
            onChange={(tags) => set({ tags })}
          />
        </div>
      ) : null}
    </>
  )
}
