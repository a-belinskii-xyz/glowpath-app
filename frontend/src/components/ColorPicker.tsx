import { COLOR_PALETTE_SWATCHES } from '../lib/colorPalette'
import { isValidHexColor } from '../lib/moodScale'

type ColorPickerProps = {
  value: string
  onChange: (hex: string) => void
  disabled?: boolean
  colorLabel: string
  hexLabel: string
  /** Optional id prefix for inputs (a11y). */
  id?: string
}

function normalizeHex(value: string): string {
  const trimmed = value.trim()
  if (/^[0-9A-Fa-f]{6}$/.test(trimmed)) {
    return `#${trimmed}`
  }
  return trimmed
}

export function ColorPicker({
  value,
  onChange,
  disabled = false,
  colorLabel,
  hexLabel,
  id = 'color',
}: ColorPickerProps) {
  const safeValue = isValidHexColor(value) ? value.toLowerCase() : value

  return (
    <div className="color-picker">
      <div className="color-picker-swatches" role="listbox" aria-label={colorLabel}>
        {COLOR_PALETTE_SWATCHES.map((swatch) => {
          const selected = safeValue.toLowerCase() === swatch.toLowerCase()
          return (
            <button
              key={swatch}
              type="button"
              role="option"
              className={`color-picker-swatch${selected ? ' color-picker-swatch-selected' : ''}`}
              style={{ backgroundColor: swatch }}
              aria-selected={selected}
              aria-label={swatch}
              disabled={disabled}
              onClick={() => onChange(swatch)}
            />
          )
        })}
      </div>
      <div className="color-picker-custom">
        <label className="color-picker-native-wrap" title={colorLabel}>
          <span className="visually-hidden">{colorLabel}</span>
          <input
            id={`${id}-native`}
            className="color-picker-native"
            type="color"
            value={isValidHexColor(value) ? value : '#60a5fa'}
            disabled={disabled}
            onChange={(event) => onChange(event.target.value)}
            aria-label={colorLabel}
          />
        </label>
        <input
          id={`${id}-hex`}
          className="form-input color-picker-hex"
          type="text"
          value={value}
          disabled={disabled}
          spellCheck={false}
          maxLength={7}
          pattern="^#[0-9A-Fa-f]{6}$"
          aria-label={hexLabel}
          onChange={(event) => onChange(normalizeHex(event.target.value))}
        />
      </div>
    </div>
  )
}
