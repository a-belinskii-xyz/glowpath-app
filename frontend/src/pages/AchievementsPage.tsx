import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { listAchievements, markAchievementSeen } from '../api/achievements'
import { Alert } from '../components/Alert'
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

function rewardLabel(
  reward: AchievementRewardPublic,
  t: (key: string, params?: Record<string, string | number>) => string,
): string {
  if (reward.kind === 'tokens' && reward.amount != null) {
    return t('achievements.rewardTokens', { amount: reward.amount })
  }
  if (reward.kind === 'icon_pack') {
    return t('achievements.rewardPack', { name: reward.pack_name || reward.pack_slug || '—' })
  }
  if (reward.kind === 'catalog_icon') {
    return t('achievements.rewardIcon', { name: reward.icon_name || reward.icon_slug || '—' })
  }
  return reward.kind
}

function isMystery(item: AchievementPublic): boolean {
  return item.visibility === 'secret' && !item.unlocked
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
    let unlocked = 0
    let totalVisible = 0
    let secretUnlocked = 0
    let secretTotal = 0
    for (const item of items) {
      if (item.visibility === 'secret') {
        secretTotal += 1
        if (item.unlocked) {
          secretUnlocked += 1
          unlocked += 1
        }
      } else {
        totalVisible += 1
        if (item.unlocked) {
          unlocked += 1
        }
      }
    }
    return { unlocked, totalVisible, secretUnlocked, secretTotal }
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
            unlocked: summary.unlocked,
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
                      <span className="achievement-rewards">
                        {item.rewards.map((reward, index) => (
                          <span key={`${reward.kind}-${index}`} className="achievement-reward-chip">
                            {rewardLabel(reward, t)}
                          </span>
                        ))}
                      </span>
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
                  <ul className="achievement-detail-rewards">
                    {selected.rewards.map((reward, index) => (
                      <li key={`${reward.kind}-${index}`}>{rewardLabel(reward, t)}</li>
                    ))}
                  </ul>
                ) : null}
                <p>
                  <Link to="/market">{t('achievements.openMarket')}</Link>
                </p>
              </>
            )}
          </div>
        ) : null}
      </EditorDrawer>
    </section>
  )
}
