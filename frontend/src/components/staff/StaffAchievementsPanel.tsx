import { useCallback, useEffect, useState } from 'react'

import { listStaffPacks } from '../../api/marketplace'
import { listCriteriaSpecs, listStaffAchievements } from '../../api/staff'
import { useLocale } from '../../context/LocaleContext'
import { formatApiError } from '../../lib/errors'
import type { CriteriaSpec, StaffAchievementPublic } from '../../types/achievement'
import type { PackCardPublic } from '../../types/marketplace'
import { AchievementIcon } from '../AchievementIcon'
import { PageErrorAlert } from '../PageErrorAlert'
import { PackStatusPill } from './PackStatusPill'
import { StaffAchievementEditor } from './StaffAchievementEditor'

const STATUS_FILTERS = ['', 'draft', 'published', 'archived'] as const

/**
 * "new" opens an empty editor; an id opens that achievement. ``key`` stays the same
 * after a new achievement is created so the editor keeps its state and message.
 */
type OpenState = { id: string | 'new'; key: string } | null

export function StaffAchievementsPanel() {
  const { t } = useLocale()
  const [status, setStatus] = useState<string>('')
  const [achievements, setAchievements] = useState<StaffAchievementPublic[]>([])
  const [specs, setSpecs] = useState<CriteriaSpec[]>([])
  const [packs, setPacks] = useState<PackCardPublic[]>([])
  const [open, setOpen] = useState<OpenState>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setIsLoading(true)
    try {
      const [achievementList, specList, packList] = await Promise.all([
        listStaffAchievements(),
        listCriteriaSpecs(),
        listStaffPacks({ limit: 100 }),
      ])
      setAchievements(achievementList.items)
      setSpecs(specList.items)
      setPacks(packList.items.filter((pack) => pack.status !== 'archived'))
      setError(null)
    } catch (err) {
      setError(formatApiError(err, t, 'errors.requestFailed'))
    } finally {
      setIsLoading(false)
    }
  }, [t])

  useEffect(() => {
    void reload()
  }, [reload])

  const upsert = (saved: StaffAchievementPublic) => {
    setAchievements((current) =>
      current.some((item) => item.id === saved.id)
        ? current.map((item) => (item.id === saved.id ? saved : item))
        : [...current, saved],
    )
    setOpen((current) => (current ? { ...current, id: saved.id } : current))
  }

  if (open && specs.length > 0) {
    const current =
      open.id === 'new' ? null : (achievements.find((item) => item.id === open.id) ?? null)
    return (
      <StaffAchievementEditor
        key={open.key}
        achievement={current}
        specs={specs}
        packs={packs}
        onSaved={upsert}
        onBack={() => setOpen(null)}
      />
    )
  }

  const visible = status ? achievements.filter((item) => item.status === status) : achievements

  return (
    <div className="staff-panel">
      <PageErrorAlert error={error} />
      <div className="staff-toolbar">
        <div className="staff-chip-row" role="toolbar">
          {STATUS_FILTERS.map((value) => (
            <button
              key={value || 'all'}
              type="button"
              className={`market-tag-chip${status === value ? ' is-active' : ''}`}
              onClick={() => setStatus(value)}
            >
              {value ? t(`staff.status.${value}`) : t('staff.statusAll')}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="button button-small"
          disabled={specs.length === 0}
          onClick={() => setOpen({ id: 'new', key: `new-${Date.now()}` })}
        >
          {t('staffAchievements.newAchievement')}
        </button>
      </div>

      {isLoading ? (
        <p className="muted">{t('common.loading')}</p>
      ) : visible.length === 0 ? (
        <p className="muted">{t('staffAchievements.empty')}</p>
      ) : (
        <ul className="staff-list">
          {visible.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className="staff-list-row staff-achievement-row"
                onClick={() => setOpen({ id: item.id, key: item.id })}
              >
                <AchievementIcon
                  achievement={item}
                  version={item.updated_at}
                  className="staff-achievement-row-icon"
                />
                <span className="staff-achievement-row-body">
                  <span className="staff-list-title">
                    {item.name}
                    <PackStatusPill status={item.status} />
                    {item.visibility === 'secret' ? (
                      <span className="status-pill status-pill--sm status-pill--muted">
                        {t('achievements.secretBadge')}
                      </span>
                    ) : null}
                  </span>
                  <span className="staff-list-meta">
                    {t(`staffAchievements.criteria.${item.criteria.type}`)} ·{' '}
                    {t('staffAchievements.unlockedCount', { count: item.unlocked_count })}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
