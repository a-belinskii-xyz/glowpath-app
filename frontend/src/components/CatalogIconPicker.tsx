import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { listMarketplaceIcons } from '../api/marketplace'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { moodGlowFilter } from '../design'
import {
  buildCollapsedCatalogIcons,
  catalogIconMatchesQuery,
  groupCatalogIconsByPack,
  isCatalogIconAssignable,
} from '../lib/catalogIcons'
import { formatApiError } from '../lib/errors'
import type { CatalogIconWithPackPublic } from '../types/marketplace'
import { CatalogIconPreview } from './CatalogIconPreview'
import { CatalogIconThumb } from './CatalogIconThumb'
import { ConfirmDialog } from './ConfirmDialog'

const COLLAPSED_COUNT = 8

type CatalogIconPickerProps = {
  selectedIconId?: string | null
  glowColor?: string | null
  suggestedMood?: number
  disabled?: boolean
  /** Packs shown elsewhere in the picker; a selected icon from them still shows. */
  hiddenPackSlugs?: string[]
  onSelect: (icon: CatalogIconWithPackPublic) => void
}

function LockBadge() {
  return (
    <span className="catalog-icon-picker-lock" aria-hidden="true">
      <svg viewBox="0 0 24 24" focusable="false">
        <path
          fill="currentColor"
          d="M17 8h-1V6a4 4 0 0 0-8 0v2H7a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V10a2 2 0 0 0-2-2zm-7-2a2 2 0 1 1 4 0v2h-4V6zm3 10.7a1.7 1.7 0 1 1 0-3.4 1.7 1.7 0 0 1 0 3.4z"
        />
      </svg>
    </span>
  )
}

export function CatalogIconPicker({
  selectedIconId,
  glowColor,
  suggestedMood,
  disabled = false,
  hiddenPackSlugs,
  onSelect,
}: CatalogIconPickerProps) {
  const { t } = useLocale()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [icons, setIcons] = useState<CatalogIconWithPackPublic[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [query, setQuery] = useState('')
  const [pendingLocked, setPendingLocked] = useState<CatalogIconWithPackPublic | null>(null)
  const rootRef = useRef<HTMLDivElement>(null)
  const sheetRef = useRef<HTMLDivElement>(null)
  const panelId = useId()

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    void listMarketplaceIcons({
      limit: 100,
    })
      .then((response) => {
        if (!cancelled) {
          setIcons(response.items)
          setError(null)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setIcons([])
          setError(formatApiError(err, t, 'errors.failedLoadMarket'))
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [t])

  const sorted = useMemo(() => {
    const copy = icons.filter(
      (icon) => icon.id === selectedIconId || !hiddenPackSlugs?.includes(icon.pack.slug),
    )
    copy.sort((a, b) => {
      const aOk = isCatalogIconAssignable(a, user?.id) ? 0 : 1
      const bOk = isCatalogIconAssignable(b, user?.id) ? 0 : 1
      if (aOk !== bOk) {
        return aOk - bOk
      }
      if (suggestedMood != null) {
        const aMood = a.suggested_mood_scores.includes(suggestedMood) ? 0 : 1
        const bMood = b.suggested_mood_scores.includes(suggestedMood) ? 0 : 1
        if (aMood !== bMood) {
          return aMood - bMood
        }
      }
      if (a.pack.sort_order !== b.pack.sort_order) {
        return a.pack.sort_order - b.pack.sort_order
      }
      return a.sort_order - b.sort_order
    })
    return copy
  }, [icons, suggestedMood, user?.id, selectedIconId, hiddenPackSlugs])

  const filtered = useMemo(
    () => sorted.filter((icon) => catalogIconMatchesQuery(icon, query)),
    [query, sorted],
  )
  const groups = useMemo(() => groupCatalogIconsByPack(filtered), [filtered])
  const collapsed = useMemo(
    () => buildCollapsedCatalogIcons(sorted, selectedIconId, COLLAPSED_COUNT),
    [selectedIconId, sorted],
  )
  const needsCollapse = sorted.length > COLLAPSED_COUNT
  const hiddenCount = Math.max(0, sorted.length - collapsed.length)

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
      if (pendingLocked) {
        return
      }
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
  }, [expanded, pendingLocked])

  const handleIconClick = (icon: CatalogIconWithPackPublic) => {
    if (!isCatalogIconAssignable(icon, user?.id)) {
      setPendingLocked(icon)
      return
    }
    onSelect(icon)
    setExpanded(false)
  }

  const renderTile = (icon: CatalogIconWithPackPublic) => {
    const assignable = isCatalogIconAssignable(icon, user?.id)
    const selected = selectedIconId === icon.id
    const glow = glowColor || icon.suggested_colors[0] || null
    return (
      <button
        key={icon.id}
        type="button"
        className={`catalog-icon-picker-tile${selected ? ' catalog-icon-picker-tile-selected' : ''}${assignable ? '' : ' catalog-icon-picker-tile-locked'}`}
        aria-pressed={assignable ? selected : undefined}
        aria-label={
          assignable ? icon.label : `${icon.label}. ${t('moodPreferences.catalogLocked')}`
        }
        title={assignable ? icon.label : t('moodPreferences.catalogLocked')}
        disabled={disabled}
        onClick={() => handleIconClick(icon)}
      >
        <span style={glow ? { filter: moodGlowFilter(glow) } : undefined}>
          <CatalogIconThumb
            iconId={icon.id}
            label=""
            className="catalog-icon-picker-thumb"
            glowColor={glow}
          />
        </span>
        {assignable ? null : <LockBadge />}
      </button>
    )
  }

  if (isLoading) {
    return <p className="form-hint">{t('common.loadingMarket')}</p>
  }

  if (error) {
    return <p className="form-hint">{error}</p>
  }

  if (sorted.length === 0) {
    return <p className="form-hint">{t('moodPreferences.catalogEmpty')}</p>
  }

  return (
    <div className="catalog-icon-picker emoji-picker" ref={rootRef}>
      {pendingLocked ? (
        <ConfirmDialog
          open
          variant="default"
          title={t('confirm.goToMarketTitle')}
          message={t('confirm.goToMarket', { label: pendingLocked.label })}
          confirmLabel={t('moodPreferences.goToMarket')}
          preview={<CatalogIconPreview icons={[pendingLocked]} variant="single" />}
          onCancel={() => setPendingLocked(null)}
          onConfirm={() => {
            setPendingLocked(null)
            navigate('/market')
          }}
        />
      ) : null}
      <div
        className="emoji-picker-strip catalog-icon-picker-strip"
        role="listbox"
        aria-label={t('moodPreferences.selectCatalogIcon')}
      >
        {collapsed.map(renderTile)}
        {needsCollapse ? (
          <button
            type="button"
            className={`emoji-picker-more${expanded ? ' is-open' : ''}`}
            aria-expanded={expanded}
            aria-controls={panelId}
            disabled={disabled}
            onClick={() => setExpanded((current) => !current)}
            title={t('moodPreferences.moreCatalogIcons')}
          >
            {expanded ? '▴' : `+${hiddenCount}`}
          </button>
        ) : null}
      </div>

      {expanded ? (
        <div
          id={panelId}
          ref={sheetRef}
          className="emoji-picker-sheet catalog-icon-picker-sheet"
          role="dialog"
          aria-label={t('moodPreferences.selectCatalogIcon')}
        >
          <label className="catalog-icon-picker-search">
            <span className="visually-hidden">{t('moodPreferences.catalogSearch')}</span>
            <input
              className="form-input catalog-icon-picker-search-input"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t('moodPreferences.catalogSearchPlaceholder')}
              autoComplete="off"
            />
          </label>
          {groups.length === 0 ? (
            <p className="form-hint">{t('moodPreferences.catalogSearchEmpty')}</p>
          ) : (
            <div className="emoji-picker-groups">
              {groups.map((group) => (
                <div key={group.pack.id} className="emoji-picker-group catalog-icon-picker-group">
                  <span className="emoji-picker-group-label">{group.pack.name}</span>
                  <div className="emoji-picker-grid catalog-icon-picker-grid">
                    {group.icons.map(renderTile)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}
