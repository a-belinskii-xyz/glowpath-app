import { type MouseEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { listAchievements, markAchievementSeen } from '../api/achievements'
import { Alert } from '../components/Alert'
import { CatalogIconThumb } from '../components/CatalogIconThumb'
import { EditorDrawer } from '../components/EditorDrawer'
import { EmailVerificationBanner } from '../components/EmailVerificationBanner'
import { PageErrorAlert } from '../components/PageErrorAlert'
import { usePageAmbientGlow } from '../context/AmbientGlowContext'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { intlLocale } from '../i18n/t'
import { formatApiError } from '../lib/errors'
import type { AchievementPublic, AchievementRewardPublic } from '../types/achievement'

type FilterId = 'all' | 'in_progress' | 'unlocked'

const CATEGORY_ORDER = ['getting_started', 'streaks', 'collection', 'secrets'] as const

function isMystery(item: AchievementPublic): boolean {
  return item.visibility === 'secret' && !item.unlocked
}

function marketHrefForReward(reward: AchievementRewardPublic): string | null {
  if (reward.kind === 'icon_pack' && reward.pack_slug) {
    return `/market?pack=${encodeURIComponent(reward.pack_slug)}`
  }
  if (reward.kind === 'catalog_icon' && reward.pack_slug) {
    const params = new URLSearchParams({ pack: reward.pack_slug })
    if (reward.icon_slug) {
      params.set('icon', reward.icon_slug)
    }
    return `/market?${params.toString()}`
  }
  return null
}

function formatUnlockPercent(
  percent: number | null | undefined,
  t: (key: string, params?: Record<string, string | number>) => string,
): string | null {
  if (percent == null) {
    return null
  }
  const rounded = percent < 1 && percent > 0 ? percent.toFixed(1) : String(Math.round(percent))
  return t('achievements.unlockPercent', { percent: rounded })
}

function AchievementRewardChips({
  rewards,
  t,
  stopPropagation,
}: {
  rewards: AchievementRewardPublic[]
  t: (key: string, params?: Record<string, string | number>) => string
  stopPropagation?: boolean
}) {
  const onInteractiveClick = (event: MouseEvent) => {
    if (stopPropagation) {
      event.stopPropagation()
    }
  }

  return (
    <span className="achievement-rewards">
      {rewards.map((reward, index) => {
        const key = `${reward.kind}-${index}`
        if (reward.kind === 'tokens' && reward.amount != null) {
          return (
            <span key={key} className="achievement-reward-chip">
              {t('achievements.rewardTokens', { amount: reward.amount })}
            </span>
          )
        }

        if (reward.kind === 'icon_pack') {
          const href = marketHrefForReward(reward)
          const label = reward.pack_name || reward.pack_slug || '—'
          const previewIds = (
            reward.preview_icon_ids?.length
              ? reward.preview_icon_ids
              : reward.cover_icon_id
                ? [reward.cover_icon_id]
                : []
          ).slice(0, 3)
          const body = (
            <>
              <span className="achievement-reward-stack" aria-hidden="true">
                {previewIds.length > 0 ? (
                  previewIds.map((iconId, stackIndex) => (
                    <span
                      key={iconId}
                      className="achievement-reward-stack-item"
                      style={{ zIndex: previewIds.length - stackIndex }}
                    >
                      <CatalogIconThumb
                        iconId={iconId}
                        label=""
                        className="achievement-reward-thumb"
                      />
                    </span>
                  ))
                ) : (
                  <span className="achievement-reward-thumb achievement-reward-thumb--empty" />
                )}
              </span>
              <span className="achievement-reward-copy">
                <span className="achievement-reward-kind">{t('achievements.rewardPackLabel')}</span>
                <span className="achievement-reward-name">{label}</span>
              </span>
            </>
          )
          if (href) {
            return (
              <Link
                key={key}
                to={href}
                className="achievement-reward-chip achievement-reward-chip--media"
                onClick={onInteractiveClick}
              >
                {body}
              </Link>
            )
          }
          return (
            <span key={key} className="achievement-reward-chip achievement-reward-chip--media">
              {body}
            </span>
          )
        }

        if (reward.kind === 'catalog_icon') {
          const href = marketHrefForReward(reward)
          const label = reward.icon_name || reward.icon_slug || '—'
          const body = (
            <>
              {reward.catalog_icon_id ? (
                <CatalogIconThumb
                  iconId={reward.catalog_icon_id}
                  label={label}
                  className="achievement-reward-thumb"
                />
              ) : (
                <span className="achievement-reward-thumb achievement-reward-thumb--empty" aria-hidden="true" />
              )}
              <span className="achievement-reward-copy">
                <span className="achievement-reward-kind">{t('achievements.rewardIconLabel')}</span>
                <span className="achievement-reward-name">{label}</span>
              </span>
            </>
          )
          if (href) {
            return (
              <Link
                key={key}
                to={href}
                className="achievement-reward-chip achievement-reward-chip--media"
                onClick={onInteractiveClick}
              >
                {body}
              </Link>
            )
          }
          return (
            <span key={key} className="achievement-reward-chip achievement-reward-chip--media">
              {body}
            </span>
          )
        }

        return (
          <span key={key} className="achievement-reward-chip">
            {reward.kind}
          </span>
        )
      })}
    </span>
  )
}

export function AchievementsPage() {
  const { t, locale } = useLocale()
  const { user } = useAuth()
  const achievementsEnabled = Boolean(user?.features?.achievements)
  const dateLocale = intlLocale(locale)

  const [items, setItems] = useState<AchievementPublic[]>([])
  const [filter, setFilter] = useState<FilterId>('all')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [selected, setSelected] = useState<AchievementPublic | null>(null)

  usePageAmbientGlow(['#f59e0b', '#a78bfa', '#60a5fa'])

  const reload = useCallback(async () => {
    const response = await listAchievements()
    setItems(response.items)
  }, [])

  useEffect(() => {
    if (!achievementsEnabled) {
      setIsLoading(false)
      return
    }
    let cancelled = false
    setIsLoading(true)
    setError(null)
    void reload()
      .catch((err) => {
        if (!cancelled) {
          setError(formatApiError(err, t, 'errors.requestFailed'))
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
  }, [achievementsEnabled, reload, t])

  const summary = useMemo(() => {
    let unlockedVisible = 0
    let totalVisible = 0
    let secretUnlocked = 0
    let secretTotal = 0
    for (const item of items) {
      if (item.visibility === 'secret') {
        secretTotal += 1
        if (item.unlocked) {
          secretUnlocked += 1
        }
      } else {
        totalVisible += 1
        if (item.unlocked) {
          unlockedVisible += 1
        }
      }
    }
    return { unlockedVisible, totalVisible, secretUnlocked, secretTotal }
  }, [items])

  const filtered = useMemo(() => {
    return items.filter((item) => {
      if (filter === 'unlocked') {
        return item.unlocked
      }
      if (filter === 'in_progress') {
        return !item.unlocked && item.visibility !== 'secret'
      }
      return true
    })
  }, [items, filter])

  const grouped = useMemo(() => {
    const map = new Map<string, AchievementPublic[]>()
    for (const item of filtered) {
      const key = item.category || 'collection'
      const list = map.get(key) ?? []
      list.push(item)
      map.set(key, list)
    }
    const keys = [
      ...CATEGORY_ORDER.filter((key) => map.has(key)),
      ...[...map.keys()].filter((key) => !(CATEGORY_ORDER as readonly string[]).includes(key)),
    ]
    return keys.map((key) => ({ key, items: map.get(key) ?? [] }))
  }, [filtered])

  const openDetail = async (item: AchievementPublic) => {
    setSelected(item)
    if (item.unlocked && item.is_new) {
      try {
        const updated = await markAchievementSeen(item.id)
        setItems((current) =>
          current.map((row) => (row.id === updated.id ? { ...row, ...updated, is_new: false } : row)),
        )
        setSelected((current) =>
          current?.id === updated.id ? { ...current, ...updated, is_new: false } : current,
        )
      } catch {
        // non-blocking
      }
    }
  }

  if (!achievementsEnabled) {
    return (
      <section className="page page-achievements">
        <EmailVerificationBanner />
        <header className="page-header">
          <h1>{t('achievements.title')}</h1>
        </header>
        <Alert variant="info">{t('achievements.disabled')}</Alert>
      </section>
    )
  }

  return (
    <section className="page page-achievements">
      <EmailVerificationBanner />
      <header className="page-header">
        <h1>{t('achievements.title')}</h1>
        <p className="page-lead">
          {t('achievements.progress', {
            unlocked: summary.unlockedVisible,
            total: summary.totalVisible,
          })}
          {summary.secretTotal > 0
            ? ` · ${t('achievements.secretsProgress', {
                unlocked: summary.secretUnlocked,
                total: summary.secretTotal,
              })}`
            : null}
        </p>
      </header>

      <PageErrorAlert error={error} />

      <div className="achievements-filters" role="tablist" aria-label={t('achievements.filters')}>
        {(
          [
            ['all', t('achievements.filterAll')],
            ['in_progress', t('achievements.filterInProgress')],
            ['unlocked', t('achievements.filterUnlocked')],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={filter === id}
            className={`button button-small${filter === id ? '' : ' button-secondary'}`}
            onClick={() => setFilter(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {isLoading ? <p className="muted">{t('common.loading')}</p> : null}

      {!isLoading && grouped.length === 0 ? (
        <Alert variant="info">{t('achievements.empty')}</Alert>
      ) : null}

      {grouped.map((group) => (
        <section key={group.key} className="achievements-section" aria-labelledby={`ach-cat-${group.key}`}>
          <h2 id={`ach-cat-${group.key}`} className="achievements-section-title">
            {t(`achievements.category.${group.key}` as 'achievements.category.getting_started')}
          </h2>
          <div className="achievements-grid">
            {group.items.map((item) => {
              const mystery = isMystery(item)
              const progressPct = Math.min(
                100,
                Math.round((item.progress_current / Math.max(1, item.progress_target)) * 100),
              )
              const rarity = formatUnlockPercent(item.unlock_percent, t)
              return (
                <button
                  key={item.id}
                  type="button"
                  className={`achievement-card${item.unlocked ? ' is-unlocked' : ''}${
                    mystery ? ' is-mystery' : ''
                  }${item.is_new ? ' is-new' : ''}`}
                  onClick={() => void openDetail(item)}
                >
                  <span className="achievement-card-icon" aria-hidden="true">
                    {mystery ? '?' : item.icon || '🏆'}
                  </span>
                  <span className="achievement-card-body">
                    <span className="achievement-card-title">
                      {mystery ? t('achievements.mysteryTitle') : item.name}
                      {item.visibility === 'secret' && item.unlocked ? (
                        <span className="achievement-secret-badge">{t('achievements.secretBadge')}</span>
                      ) : null}
                      {item.is_new ? (
                        <span className="achievement-new-badge">{t('achievements.newBadge')}</span>
                      ) : null}
                    </span>
                    {!mystery ? (
                      <span className="achievement-card-desc">{item.description}</span>
                    ) : (
                      <span className="achievement-card-desc">{t('achievements.mysteryHint')}</span>
                    )}
                    {rarity ? <span className="achievement-rarity">{rarity}</span> : null}
                    {!mystery && !item.unlocked ? (
                      <span className="achievement-progress" aria-hidden="true">
                        <span className="achievement-progress-bar" style={{ width: `${progressPct}%` }} />
                      </span>
                    ) : null}
                    {!mystery && !item.unlocked ? (
                      <span className="achievement-progress-label">
                        {item.progress_current} / {item.progress_target}
                      </span>
                    ) : null}
                    {!mystery && item.rewards && item.rewards.length > 0 ? (
                      <AchievementRewardChips rewards={item.rewards} t={t} stopPropagation />
                    ) : null}
                    {item.unlocked && item.unlocked_by_entry_id ? (
                      <Link
                        to={`/entries/${item.unlocked_by_entry_id}`}
                        className="achievement-entry-link"
                        onClick={(event) => event.stopPropagation()}
                      >
                        {t('achievements.viewEntry')}
                      </Link>
                    ) : null}
                  </span>
                </button>
              )
            })}
          </div>
        </section>
      ))}

      <EditorDrawer
        open={selected !== null}
        title={
          selected && isMystery(selected)
            ? t('achievements.mysteryTitle')
            : selected?.name || t('achievements.title')
        }
        onClose={() => setSelected(null)}
      >
        {selected ? (
          <div className="achievement-detail">
            <p className="achievement-detail-icon" aria-hidden="true">
              {isMystery(selected) ? '?' : selected.icon || '🏆'}
            </p>
            {isMystery(selected) ? (
              <p>{t('achievements.mysteryHint')}</p>
            ) : (
              <>
                <p>{selected.description}</p>
                {formatUnlockPercent(selected.unlock_percent, t) ? (
                  <p className="muted">{formatUnlockPercent(selected.unlock_percent, t)}</p>
                ) : null}
                {selected.unlocked_at ? (
                  <p className="muted">
                    {t('achievements.unlockedAt', {
                      date: new Date(selected.unlocked_at).toLocaleString(dateLocale),
                    })}
                  </p>
                ) : (
                  <p className="muted">
                    {t('achievements.progressLabel', {
                      current: selected.progress_current,
                      target: selected.progress_target,
                    })}
                  </p>
                )}
                {selected.rewards && selected.rewards.length > 0 ? (
                  <AchievementRewardChips rewards={selected.rewards} t={t} />
                ) : null}
                {selected.unlocked_by_entry_id ? (
                  <p>
                    <Link to={`/entries/${selected.unlocked_by_entry_id}`}>
                      {t('achievements.viewEntry')}
                    </Link>
                  </p>
                ) : null}
              </>
            )}
          </div>
        ) : null}
      </EditorDrawer>
    </section>
  )
}
