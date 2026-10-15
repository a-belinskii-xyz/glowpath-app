import { useEffect, useRef, useState } from 'react'

import { normalizeClock, typeClock } from '../lib/sleep'
import { uses12h } from '../lib/timeFormat'

/** What onChange gets for a time that is typed but not valid yet; normalizeClock rejects it. */
export const CLOCK_INVALID = '?'

type ClockFieldProps = {
  /** "HH:MM" in 24 hours, or "" when empty. */
  value: string
  onChange: (value: string) => void
  ariaLabel: string
  required?: boolean
  placeholder?: string
  className?: string
  inputClassName?: string
}

function display(value: string, twelve: boolean): { text: string; pm: boolean } {
  const clock = normalizeClock(value)
  if (!clock) return { text: '', pm: false }
  if (!twelve) return { text: clock, pm: false }
  const [hours, minutes] = clock.split(':').map(Number)
  return { text: `${hours % 12 === 0 ? 12 : hours % 12}:${String(minutes).padStart(2, '0')}`, pm: hours >= 12 }
}

/** The typed text as "HH:MM" in 24 hours, "" when empty, or CLOCK_INVALID. */
function toClock(text: string, pm: boolean, twelve: boolean): string {
  if (text === '') return ''
  const clock = normalizeClock(text)
  if (!clock) return CLOCK_INVALID
  if (!twelve) return clock
  const [hours, minutes] = clock.split(':').map(Number)
  if (hours < 1 || hours > 12) return CLOCK_INVALID
  return `${String((hours % 12) + (pm ? 12 : 0)).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
}

/**
 * A time typed on a digit keypad, in the user's 24-hour or AM/PM clock (GP-53). Used instead of
 * type="time": its picker does not open in some Telegram webviews and ignores the app's format.
 */
export function ClockField({
  value,
  onChange,
  ariaLabel,
  required = false,
  placeholder,
  className,
  inputClassName,
}: ClockFieldProps) {
  const twelve = uses12h()
  const [text, setText] = useState(() => display(value, twelve).text)
  const [pm, setPm] = useState(() => display(value, twelve).pm)
  const emitted = useRef(value)

  // Follow changes made outside the field (another day picked, a reset), not our own echoes.
  useEffect(() => {
    if (value === emitted.current) return
    emitted.current = value
    const next = display(value, twelve)
    setText(next.text)
    setPm(next.pm)
  }, [value, twelve])

  const emit = (nextText: string, nextPm: boolean) => {
    const clock = toClock(nextText, nextPm, twelve)
    emitted.current = clock
    onChange(clock)
  }

  const invalid = text !== '' && toClock(text, pm, twelve) === CLOCK_INVALID

  return (
    <span className={`clock-field${className ? ` ${className}` : ''}`}>
      <input
        className={`${inputClassName ?? 'form-input'}${invalid ? ' is-invalid' : ''}`}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        aria-label={ariaLabel}
        aria-invalid={invalid || undefined}
        required={required}
        placeholder={placeholder ?? (twelve ? '11:00' : '23:00')}
        value={text}
        // Typing replaces the old time instead of appending to it.
        onFocus={(event) => event.currentTarget.select()}
        onChange={(event) => {
          const next = typeClock(event.target.value)
          setText(next)
          emit(next, pm)
        }}
        onBlur={() => {
          const clock = toClock(text, pm, twelve)
          if (clock && clock !== CLOCK_INVALID) setText(display(clock, twelve).text)
        }}
      />
      {twelve ? (
        <button
          type="button"
          className="clock-field-period"
          aria-label={`${ariaLabel}: ${pm ? 'PM' : 'AM'}`}
          onClick={() => {
            setPm(!pm)
            emit(text, !pm)
          }}
        >
          {pm ? 'PM' : 'AM'}
        </button>
      ) : null}
    </span>
  )
}
