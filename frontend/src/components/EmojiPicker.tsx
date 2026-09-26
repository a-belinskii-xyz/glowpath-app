import { useEffect, useId, useMemo, useRef, useState } from 'react'

import { isSingleEmoji } from '../lib/emoji'
import type { EmojiGroup } from '../lib/emojiPalette'
import { useLocale } from '../context/LocaleContext'

const COLLAPSED_COUNT = 8

type EmojiPickerProps = {
  value: string
  onChange: (emoji: string) => void
  disabled?: boolean
  label: string
  /** Grouped emoji (preferred for mood / goals). */
  groups?: readonly EmojiGroup[]
  /** Flat list when groups are not used. */
  options?: readonly string[]
  /** Resolve a group id to a visible label. */
  groupLabel?: (groupId: string) => string
  /** How many emoji to show before “more”. */
  collapsedCount?: number
}

function buildCollapsedList(
  flat: readonly string[],
  selected: string,
  count: number,
): string[] {
  if (flat.length <= count) {
    return [...flat]
  }
  const result: string[] = []
  if (selected && flat.includes(selected)) {
    result.push(selected)
  }
  for (const emoji of flat) {
    if (result.length >= count) {
      break
    }
    if (!result.includes(emoji)) {
      result.push(emoji)
    }
  }
  return result
}

export function EmojiPicker({
  value,
  onChange,
  disabled = false,
  label,
  groups,
  options,
  groupLabel,
  collapsedCount = COLLAPSED_COUNT,
}: EmojiPickerProps) {
  const { t } = useLocale()
  const [expanded, setExpanded] = useState(false)
  const [customDraft, setCustomDraft] = useState('')
  const rootRef = useRef<HTMLDivElement>(null)
  const sheetRef = useRef<HTMLDivElement>(null)
  const panelId = useId()
  const customErrorId = useId()

  const selected = value.trim()
  const resolvedGroups: readonly EmojiGroup[] =
    groups ??
    (options && options.length > 0 ? [{ id: 'All', emojis: options }] : [])
  const flat = useMemo(
    () => resolvedGroups.flatMap((group) => group.emojis),
    [resolvedGroups],
  )
  const known = flat.includes(selected)
  const showGroupLabels = resolvedGroups.length > 1
  const needsCollapse = flat.length > collapsedCount
  const collapsed = useMemo(
    () => buildCollapsedList(flat, selected, collapsedCount),
    [flat, selected, collapsedCount],
  )
  const hiddenCount = Math.max(0, flat.length - collapsed.length)
  const customValue = customDraft.trim()
  const customInvalid = customValue !== '' && !isSingleEmoji(customValue)

  const applyCustom = () => {
    if (!customValue || customInvalid) {
      return
    }
    onChange(customValue)
    setCustomDraft('')
    setExpanded(false)
  }

  useEffect(() => {
    if (!expanded) {
      return
    }
    let innerFrame = 0
    const outerFrame = requestAnimationFrame(() => {
      innerFrame = requestAnimationFrame(() => {
        sheetRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
          inline: 'nearest',
        })
      })
    })
    const onPointerDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setExpanded(false)
      }
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setExpanded(false)
      }
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKey)
    return () => {
      cancelAnimationFrame(outerFrame)
      cancelAnimationFrame(innerFrame)
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [expanded])

  const renderEmojiButton = (emoji: string) => {
    const isSelected = selected === emoji
    return (
      <button
        key={emoji}
        type="button"
        role="option"
        className={`emoji-picker-option${isSelected ? ' emoji-picker-option-selected' : ''}`}
        aria-selected={isSelected}
        aria-label={emoji}
        disabled={disabled}
        onClick={() => {
          onChange(emoji)
          setExpanded(false)
        }}
      >
        {emoji}
      </button>
    )
  }

  return (
    <div className="emoji-picker" ref={rootRef}>
      <div className="emoji-picker-strip" role="listbox" aria-label={label}>
        {collapsed.map(renderEmojiButton)}
        {needsCollapse ? (
          <button
            type="button"
            className={`emoji-picker-more${expanded ? ' is-open' : ''}`}
            aria-expanded={expanded}
            aria-controls={panelId}
            disabled={disabled}
            onClick={() => setExpanded((current) => !current)}
            title={t('moodPreferences.moreEmoji')}
          >
            {expanded ? '▴' : `+${hiddenCount}`}
          </button>
        ) : null}
        {!known && selected ? (
          <span className="emoji-picker-custom-preview" aria-hidden>
            {selected}
          </span>
        ) : null}
      </div>

      <div className="emoji-picker-custom">
        <input
          className={`form-input emoji-picker-custom-input${customInvalid ? ' is-invalid' : ''}`}
          type="text"
          inputMode="text"
          autoComplete="off"
          value={customDraft}
          placeholder={t('moodPreferences.customEmojiPlaceholder')}
          aria-label={t('moodPreferences.customEmojiPlaceholder')}
          aria-invalid={customInvalid}
          aria-describedby={customInvalid ? customErrorId : undefined}
          disabled={disabled}
          onChange={(event) => setCustomDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault()
              applyCustom()
            }
          }}
        />
        <button
          type="button"
          className="button button-secondary button-small"
          disabled={disabled || !customValue || customInvalid}
          onClick={applyCustom}
        >
          {t('moodPreferences.customEmojiApply')}
        </button>
        {customInvalid ? (
          <span id={customErrorId} className="emoji-picker-custom-error" role="alert">
            {t('moodPreferences.customEmojiInvalid')}
          </span>
        ) : null}
      </div>

      {expanded ? (
        <div
          id={panelId}
          ref={sheetRef}
          className="emoji-picker-sheet"
          role="dialog"
          aria-label={label}
        >
          <div className="emoji-picker-groups">
            {resolvedGroups.map((group) => (
              <div key={group.id} className="emoji-picker-group" role="group">
                {showGroupLabels ? (
                  <span className="emoji-picker-group-label">
                    {groupLabel?.(group.id) ?? group.id}
                  </span>
                ) : null}
                <div className="emoji-picker-grid">{group.emojis.map(renderEmojiButton)}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
