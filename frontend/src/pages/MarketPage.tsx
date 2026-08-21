import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  listMarketplaceIcons,
  getMarketplaceSearchTags,
  unlockMarketplacePack,
} from '../api/marketplace'
import { getWallet } from '../api/wallet'
import { CatalogIconThumb } from '../components/CatalogIconThumb'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { StableButtonLabel } from '../components/StableButtonLabel'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { moodGlowFilter } from '../design'
import { catalogIconMatchesQuery, groupCatalogIconsByPack } from '../lib/catalogIcons'
import { ApiError, formatApiError } from '../lib/errors'
import type {
  CatalogIconWithPackPublic,
  SearchTagPublic,
} from '../types/marketplace'

const PACK_COLLAPSED_COUNT = 8

export function MarketPage() {
  const { t, locale } = useLocale()
  const { user } = useAuth()
  const marketplaceEnabled = Boolean(user?.features?.icon_marketplace)

  const [icons, setIcons] = useState<CatalogIconWithPackPublic[]>([])
  const [searchTags, setSearchTags] = useState<SearchTagPublic[]>([])
  const [activeTag, setActiveTag] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [expandedPackIds, setExpandedPackIds] = useState<Record<string, boolean>>({})
  const [balance, setBalance] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [unlockingPackId, setUnlockingPackId] = useState<string | null>(null)

  const glowColors = useMemo(() => {
    const colors = icons
      .map((icon) => icon.suggested_colors[0])
      .filter((color): color is string => Boolean(color))
    return colors.slice(0, 6)
  }, [icons])
  usePageAmbientGlow(glowColors.length > 0 ? glowColors : ['#60a5fa', '#f59e0b'])

  const reload = useCallback(async () => {
    const [iconsResponse, tagsResponse, wallet] = await Promise.all([
      listMarketplaceIcons({
        tag: activeTag ?? undefined,
        limit: 100,
      }),
      getMarketplaceSearchTags(),
      getWallet(),
    ])
    setIcons(iconsResponse.items)
    setSearchTags(tagsResponse.items)
    setBalance(wallet.balance)
  }, [activeTag])

  useEffect(() => {
    if (!marketplaceEnabled) {
      setIsLoading(false)
      return
    }

    let cancelled = false
    setIsLoading(true)
    void reload()
      .then(() => {
        if (!cancelled) {
          setError(null)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          if (err instanceof ApiError && err.status === 403) {
            setError(t('errors.verifyToUseMarket'))
          } else {
            setError(formatApiError(err, t, 'errors.failedLoadMarket'))
          }
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
  }, [marketplaceEnabled, reload, t])

  const handleUnlock = async (packId: string) => {
    setUnlockingPackId(packId)
    setError(null)
    try {
      await unlockMarketplacePack(packId)
      await reload()
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedUnlockPack'))
    } finally {
      setUnlockingPackId(null)
    }
  }

  const filteredIcons = useMemo(
    () => icons.filter((icon) => catalogIconMatchesQuery(icon, query)),
    [icons, query],
  )
  const groups = useMemo(() => groupCatalogIconsByPack(filteredIcons), [filteredIcons])
  const searching = query.trim().length > 0

  const balanceLabel =
    balance === null
      ? '—'
      : new Intl.NumberFormat(locale === 'ru' ? 'ru-RU' : 'en-US').format(balance)

  if (!marketplaceEnabled) {
    return (
      <section className="page page-market">
        <header className="page-header">
          <h1>{t('market.title')}</h1>
        </header>
        <p className="market-empty">{t('market.disabled')}</p>
      </section>
    )
  }

  return (
    <section className="page page-market">
      <EmailVerificationBanner />
      <header className="page-header page-header-compact market-header">
        <div className="market-header-copy">
          <h1>{t('market.title')}</h1>
          <p className="market-lead">{t('market.lead')}</p>
        </div>
        <div className="market-balance" aria-live="polite">
          <span className="market-balance-label">{t('market.balance')}</span>
          <strong className="market-balance-value">
            {isLoading && balance === null ? t('common.loading') : balanceLabel}
            <span className="market-balance-unit">{t('profile.walletTokens')}</span>
          </strong>
        </div>
      </header>

      <PageErrorAlert error={error} />

      <label className="market-search">
        <span className="visually-hidden">{t('market.search')}</span>
        <input
          className="form-input"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t('market.searchPlaceholder')}
          autoComplete="off"
        />
      </label>

      {searchTags.length > 0 ? (
        <div className="market-tag-chips" role="toolbar" aria-label={t('market.filterTags')}>
          <button
            type="button"
            className={`market-tag-chip${!activeTag ? ' is-active' : ''}`}
            onClick={() => setActiveTag(null)}
          >
            {t('market.allTags')}
          </button>
          {searchTags.map((tag) => (
            <button
              key={tag.id}
              type="button"
              className={`market-tag-chip${activeTag === tag.slug ? ' is-active' : ''}`}
              onClick={() => setActiveTag(tag.slug === activeTag ? null : tag.slug)}
            >
              {tag.label}
            </button>
          ))}
        </div>
      ) : null}

      {isLoading ? (
        <p className="muted">{t('common.loadingMarket')}</p>
      ) : groups.length === 0 ? (
        <p className="market-empty">
          {searching || activeTag ? t('market.searchEmpty') : t('market.empty')}
        </p>
      ) : (
        <div className="market-pack-list">
          {groups.map((group) => {
            const locked = !group.pack.unlocked && group.pack.price_tokens > 0
            const expanded = searching || Boolean(expandedPackIds[group.pack.id])
            const visibleIcons =
              expanded || group.icons.length <= PACK_COLLAPSED_COUNT
                ? group.icons
                : group.icons.slice(0, PACK_COLLAPSED_COUNT)
            const hiddenCount = group.icons.length - visibleIcons.length
            return (
              <section key={group.pack.id} className="market-pack">
                <header className="market-pack-header">
                  <div className="market-pack-copy">
                    <h2 className="market-pack-title">{group.pack.name}</h2>
                    {group.pack.description ? (
                      <p className="market-pack-description">{group.pack.description}</p>
                    ) : null}
                  </div>
                  <div className="market-pack-actions">
                    {locked ? (
                      <>
                        <span className="market-price">
                          {t('market.priceTokens', { count: String(group.pack.price_tokens) })}
                        </span>
                        <button
                          type="button"
                          className="button button-secondary button-small"
                          disabled={unlockingPackId === group.pack.id}
                          onClick={() => void handleUnlock(group.pack.id)}
                        >
                          <StableButtonLabel
                            active={
                              unlockingPackId === group.pack.id
                                ? t('market.unlocking')
                                : t('market.unlock')
                            }
                            labels={[t('market.unlock'), t('market.unlocking')]}
                          />
                        </button>
                      </>
                    ) : (
                      <span className="market-unlocked">{t('market.unlocked')}</span>
                    )}
                  </div>
                </header>
                <ul className="market-pack-icons">
                  {visibleIcons.map((icon) => {
                    const glow = icon.suggested_colors[0] ?? '#94a3b8'
                    return (
                      <li key={icon.id} className="market-pack-icon">
                        <div
                          className="market-icon-card-media"
                          style={{ filter: moodGlowFilter(glow) }}
                        >
                          <CatalogIconThumb
                            iconId={icon.id}
                            label={icon.label}
                            glowColor={glow}
                          />
                        </div>
                        <p className="market-pack-icon-label">{icon.label}</p>
                      </li>
                    )
                  })}
                  {hiddenCount > 0 ? (
                    <li className="market-pack-icon">
                      <button
                        type="button"
                        className="market-pack-more"
                        onClick={() =>
                          setExpandedPackIds((current) => ({
                            ...current,
                            [group.pack.id]: true,
                          }))
                        }
                      >
                        +{hiddenCount}
                      </button>
                    </li>
                  ) : null}
                  {expanded && group.icons.length > PACK_COLLAPSED_COUNT && !searching ? (
                    <li className="market-pack-icon">
                      <button
                        type="button"
                        className="market-pack-more is-open"
                        onClick={() =>
                          setExpandedPackIds((current) => ({
                            ...current,
                            [group.pack.id]: false,
                          }))
                        }
                        aria-label={t('common.close')}
                      >
                        ▴
                      </button>
                    </li>
                  ) : null}
                </ul>
              </section>
            )
          })}
        </div>
      )}
    </section>
  )
}
