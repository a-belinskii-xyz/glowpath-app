import { toggle } from './iconFields'

/** Chip row for picking several values, shared by the upload defaults and the icon editor. */
export function ChipToggleRow<T extends string | number>({
  options,
  selected,
  label,
  onChange,
}: {
  options: readonly T[]
  selected: T[]
  label: (value: T) => string
  onChange: (next: T[]) => void
}) {
  return (
    <div className="staff-chip-row">
      {options.map((value) => (
        <button
          key={value}
          type="button"
          aria-pressed={selected.includes(value)}
          className={`market-tag-chip${selected.includes(value) ? ' is-active' : ''}`}
          onClick={() => onChange(toggle(selected, value))}
        >
          {label(value)}
        </button>
      ))}
    </div>
  )
}
