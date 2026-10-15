import { useEffect, useId, useMemo, useState } from 'react'

import { listTagGroups } from '../api/tagGroups'
import { useLocale } from '../context/LocaleContext'
import { moodChipStyle } from '../design'
import { useColorScheme } from '../hooks/useColorScheme'
import type { TagPublic } from '../types/tag'
import { TagIcon } from './TagIcon'

const SUGGESTED_TAGS = 4
const SEARCH_RESULTS = 8

type QuickTagPickerProps = {
  selectedIds: string[]
  onToggle: (tagId: string) => void
}

/** A few of the user's frequent tags plus search over all of them (GP-52). */
export function QuickTagPicker({ selectedIds, onToggle }: QuickTagPickerProps) {
  const { t } = useLocale()
  const colorScheme = useColorScheme()
  const searchId = useId()
  const [allTags, setAllTags] = useState<TagPublic[]>([])
  const [frequent, setFrequent] = useState<TagPublic[]>([])
  const [query, setQuery] = useState('')

  useEffect(() => {
    let cancelled = false
    listTagGroups()
      .then((response) => {
        if (cancelled) return
        setAllTags(response.items.flatMap((group) => group.tags))
        setFrequent(response.frequent_tags ?? [])
      })
      .catch(() => {
        // Tags are optional here: without them the win still saves.
      })
    return () => {
      cancelled = true
    }
  }, [])

  const shown = useMemo(() => {
    const byId = new Map(allTags.map((tag) => [tag.id, tag]))
    const selected = selectedIds
      .map((id) => byId.get(id))
      .filter((tag): tag is TagPublic => tag != null)
    const needle = query.trim().toLowerCase()
    if (needle) {
      const matches = allTags
        .filter(
          (tag) =>
            !selectedIds.includes(tag.id) &&
            (tag.label.toLowerCase().includes(needle) || tag.slug.toLowerCase().includes(needle)),
        )
        .slice(0, SEARCH_RESULTS)
      return { selected, rest: matches }
    }
    const suggestions = frequent
      .filter((tag) => !selectedIds.includes(tag.id))
      .slice(0, Math.max(0, SUGGESTED_TAGS - selected.length))
    return { selected, rest: suggestions }
  }, [allTags, frequent, selectedIds, query])

  if (allTags.length === 0) {
    return null
  }

  const renderChip = (tag: TagPublic) => {
    const isSelected = selectedIds.includes(tag.id)
    const chip = moodChipStyle(tag.color, colorScheme)
    return (
      <button
        key={tag.id}
        type="button"
        className={`tag-chip tag-chip-iconic${isSelected ? ' tag-chip-selected' : ''}`}
        style={
          isSelected
            ? { background: chip.background, borderColor: tag.color, color: chip.color }
            : undefined
        }
        onClick={() => onToggle(tag.id)}
        aria-pressed={isSelected}
      >
        <TagIcon
          style={{
            color: isSelected ? chip.color : tag.color,
            icon_type: tag.icon_type,
            icon: tag.icon,
          }}
          className="tag-chip-icon"
        />
        <span className="tag-chip-text">{tag.label}</span>
      </button>
    )
  }

  const chips = [...shown.selected, ...shown.rest]

  return (
    <div className="form-field quick-tag-picker">
      <label className="form-label" htmlFor={searchId}>
        {t('myPage.tagsLabel')}
      </label>
      {chips.length > 0 ? <div className="tag-chips">{chips.map(renderChip)}</div> : null}
      {query.trim() && shown.rest.length === 0 ? (
        <p className="muted quick-tag-picker-empty">{t('myPage.tagsNoMatch')}</p>
      ) : null}
      <input
        id={searchId}
        className="form-input"
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={t('myPage.tagsSearch')}
        autoComplete="off"
      />
    </div>
  )
}
