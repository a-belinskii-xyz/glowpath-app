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
import { ApiError, formatApiError } from '../lib/errors'
import type {
  CatalogIconWithPackPublic,
  SearchTagPublic,
} from '../types/marketplace'

export function MarketPage() {
  const { t, locale } = useLocale()
  const { user } = useAuth()
  const marketplaceEnabled = Boolean(user?.features?.icon_marketplace)

  const [icons, setIcons] = useState<CatalogIconWithPackPublic[]>([])
  const [searchTags, setSearchTags] = useState<SearchTagPublic[]>([])
  const [activeTag, setActiveTag] = useState<string | null>(null)
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
      ) : icons.length === 0 ? (
        <p className="market-empty">{t('market.empty')}</p>
      ) : (
        <ul className="market-icon-grid">
          {icons.map((icon) => {
            const glow = icon.suggested_colors[0] ?? '#94a3b8'
            const locked = !icon.pack.unlocked && icon.pack.price_tokens > 0
            return (
              <li key={icon.id} className="market-icon-card">
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
                <div className="market-icon-card-body">
                  <p className="market-icon-card-title">{icon.label}</p>
                  <p className="market-icon-card-pack">{icon.pack.name}</p>
                  <div className="market-icon-card-meta">
                    {icon.suggested_colors.slice(0, 4).map((color) => (
                      <span
                        key={color}
                        className="market-color-dot"
                        style={{ background: color }}
                        title={color}
                      />
                    ))}
                    {locked ? (
                      <span className="market-price">
                        {t('market.priceTokens', { count: String(icon.pack.price_tokens) })}
                      </span>
                    ) : (
                      <span className="market-unlocked">{t('market.unlocked')}</span>
                    )}
                  </div>
                  {locked ? (
                    <button
                      type="button"
                      className="button button-secondary button-small market-unlock-button"
                      disabled={unlockingPackId === icon.pack.id}
                      onClick={() => void handleUnlock(icon.pack.id)}
                    >
                      <StableButtonLabel
                        active={
                          unlockingPackId === icon.pack.id
                            ? t('market.unlocking')
                            : t('market.unlock')
                        }
                        labels={[t('market.unlock'), t('market.unlocking')]}
                      />
                    </button>
                  ) : null}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
