import { useEffect, useState } from 'react'

import { getMarketplacePack } from '../../api/marketplace'
import { useLocale } from '../../context/LocaleContext'
import type { AchievementRewardKind } from '../../types/achievement'
import type { CatalogIconPublic, PackCardPublic } from '../../types/marketplace'
import type { RewardDraft } from './achievementDraft'

const REWARD_KINDS: AchievementRewardKind[] = ['tokens', 'icon_pack', 'catalog_icon']
const MAX_REWARDS = 10

type StaffRewardsFieldsProps = {
  rewards: RewardDraft[]
  packs: PackCardPublic[]
  onChange: (rewards: RewardDraft[]) => void
}

export function StaffRewardsFields({ rewards, packs, onChange }: StaffRewardsFieldsProps) {
  const { t } = useLocale()
  const [packIcons, setPackIcons] = useState<Record<string, CatalogIconPublic[]>>({})

  const neededPacks = rewards
    .filter((reward) => reward.kind === 'catalog_icon' && reward.packId)
    .map((reward) => reward.packId)
  const missingKey = neededPacks.filter((id) => !(id in packIcons)).join(',')

  useEffect(() => {
    if (!missingKey) return
    let cancelled = false
    for (const packId of missingKey.split(',')) {
      void getMarketplacePack(packId)
        .then((pack) => {
          if (!cancelled) setPackIcons((current) => ({ ...current, [packId]: pack.icons }))
        })
        .catch(() => {
          if (!cancelled) setPackIcons((current) => ({ ...current, [packId]: [] }))
        })
    }
    return () => {
      cancelled = true
    }
  }, [missingKey])

  const update = (index: number, patch: Partial<RewardDraft>) =>
    onChange(rewards.map((reward, i) => (i === index ? { ...reward, ...patch } : reward)))

  const packSelect = (reward: RewardDraft, index: number) => (
    <label className="form-field">
      <span className="form-label">{t('staffAchievements.pack')}</span>
      <select
        className="form-input"
        value={reward.packId}
        required
        onChange={(event) => update(index, { packId: event.target.value, iconId: '' })}
      >
        <option value="">{t('staffAchievements.choosePack')}</option>
        {packs.map((pack) => (
          <option key={pack.id} value={pack.id}>
            {pack.name} ({t(`staff.status.${pack.status}`)})
          </option>
        ))}
      </select>
    </label>
  )

  return (
    <div className="staff-rewards">
      {rewards.length === 0 ? <p className="muted">{t('staffAchievements.noRewards')}</p> : null}
      {rewards.map((reward, index) => (
        <div key={index} className="staff-reward-row">
          <label className="form-field">
            <span className="form-label">{t('staffAchievements.reward')}</span>
            <select
              className="form-input"
              value={reward.kind}
              onChange={(event) =>
                update(index, { kind: event.target.value as AchievementRewardKind })
              }
            >
              {REWARD_KINDS.map((kind) => (
                <option key={kind} value={kind}>
                  {t(`staffAchievements.rewardKind.${kind}`)}
                </option>
              ))}
            </select>
          </label>
          {reward.kind === 'tokens' ? (
            <label className="form-field">
              <span className="form-label">{t('staffAchievements.amount')}</span>
              <input
                className="form-input"
                type="number"
                inputMode="numeric"
                min={1}
                step={1}
                required
                value={reward.amount}
                onChange={(event) => update(index, { amount: event.target.value })}
              />
            </label>
          ) : (
            packSelect(reward, index)
          )}
          {reward.kind === 'catalog_icon' ? (
            <label className="form-field">
              <span className="form-label">{t('staffAchievements.icon')}</span>
              <select
                className="form-input"
                value={reward.iconId}
                required
                disabled={!reward.packId}
                onChange={(event) => update(index, { iconId: event.target.value })}
              >
                <option value="">{t('staffAchievements.chooseIcon')}</option>
                {(packIcons[reward.packId] ?? []).map((icon) => (
                  <option key={icon.id} value={icon.id}>
                    {icon.label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <button
            type="button"
            className="button button-secondary button-small staff-reward-remove"
            aria-label={t('staffAchievements.removeReward')}
            title={t('staffAchievements.removeReward')}
            onClick={() => onChange(rewards.filter((_, i) => i !== index))}
          >
            ×
          </button>
        </div>
      ))}
      {rewards.length < MAX_REWARDS ? (
        <button
          type="button"
          className="button button-secondary button-small"
          onClick={() =>
            onChange([...rewards, { kind: 'tokens', amount: '10', packId: '', iconId: '' }])
          }
        >
          {t('staffAchievements.addReward')}
        </button>
      ) : null}
    </div>
  )
}
