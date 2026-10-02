import { useLocale } from '../context/LocaleContext'
import { MOOD_FACE_ICONS, getBuiltinMoodIconLabel } from '../lib/moodBuiltinIcons'

type BuiltinIconPickerProps = {
  selectedSlug?: string | null
  /** Icons suggested for this score are listed first. */
  suggestedMood?: number
  disabled?: boolean
  onSelect: (slug: string) => void
}

export function BuiltinIconPicker({
  selectedSlug,
  suggestedMood,
  disabled = false,
  onSelect,
}: BuiltinIconPickerProps) {
  const { locale } = useLocale()
  const icons = [...MOOD_FACE_ICONS].sort(
    (a, b) =>
      Number(b.suggestedScore === suggestedMood) - Number(a.suggestedScore === suggestedMood),
  )

  return (
    <ul className="catalog-icon-picker-grid builtin-icon-picker">
      {icons.map((icon) => {
        const selected = icon.slug === selectedSlug
        const label = getBuiltinMoodIconLabel(icon.slug, locale)
        return (
          <li key={icon.slug}>
            <button
              type="button"
              className={`catalog-icon-picker-tile${selected ? ' catalog-icon-picker-tile-selected' : ''}`}
              aria-pressed={selected}
              aria-label={label}
              title={label}
              disabled={disabled}
              onClick={() => onSelect(icon.slug)}
            >
              <img src={icon.assetPath} alt="" draggable={false} />
            </button>
          </li>
        )
      })}
    </ul>
  )
}
