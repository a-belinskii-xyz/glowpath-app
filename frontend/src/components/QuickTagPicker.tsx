import { useEffect, useId, useMemo, useState } from 'react'

import { listTagGroups, quickCreateTag } from '../api/tagGroups'
import { useLocale } from '../context/LocaleContext'
import { moodChipStyle } from '../design'
import { useColorScheme } from '../hooks/useColorScheme'
import { formatApiError } from '../lib/errors'
import { tagLabelKey } from '../lib/tagLabel'
import type { TagPublic } from '../types/tag'
import { PageErrorAlert } from './PageErrorAlert'
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
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
    const needle = tagLabelKey(query)
    if (needle) {
      const matches = allTags
        .filter(
          (tag) =>
            !selectedIds.includes(tag.id) &&
            (tagLabelKey(tag.label).includes(needle) || tag.slug.toLowerCase().includes(needle)),
        )
        .slice(0, SEARCH_RESULTS)
      return { selected, rest: matches }
    }
    const suggestions = frequent
      .filter((tag) => !selectedIds.includes(tag.id))
      .slice(0, Math.max(0, SUGGESTED_TAGS - selected.length))
    return { selected, rest: suggestions }
  }, [allTags, frequent, selectedIds, query])

  const newName = query.replace(/\s+/g, ' ').trim()
  const newKey = tagLabelKey(newName)
  const canCreate =
    newKey.length > 0 &&
    !allTags.some((tag) =>
      [tag.label, ...Object.values(tag.labels)].some((value) => tagLabelKey(value) === newKey),
    )

  const handleCreate = async () => {
    if (!canCreate || isCreating) return
    setIsCreating(true)
    setError(null)
    try {
      const { tag } = await quickCreateTag(newName)
      setAllTags((current) => (current.some((item) => item.id === tag.id) ? current : [...current, tag]))
      if (!selectedIds.includes(tag.id)) onToggle(tag.id)
      setQuery('')
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedSave'))
    } finally {
      setIsCreating(false)
    }
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
      {query.trim() && shown.rest.length === 0 && !canCreate ? (
        <p className="muted quick-tag-picker-empty">{t('myPage.tagsNoMatch')}</p>
      ) : null}
      <input
        id={searchId}
        className="form-input"
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter') {
            event.preventDefault()
            void handleCreate()
          }
        }}
        placeholder={t('myPage.tagsSearch')}
        autoComplete="off"
      />
      {canCreate ? (
        <button
          type="button"
          className="tag-chip tag-chip-create"
          onClick={() => void handleCreate()}
          disabled={isCreating}
        >
          <span aria-hidden="true">＋</span>
          <span className="tag-chip-text">{t('entries.createTag', { name: newName })}</span>
        </button>
      ) : null}
      <PageErrorAlert error={error} />
    </div>
  )
}
