import type {
  AchievementCategory,
  AchievementCriteria,
  AchievementRewardInput,
  AchievementVisibility,
  CriteriaSpec,
  StaffAchievementCreate,
  StaffAchievementPublic,
} from '../../types/achievement'

export const ACHIEVEMENT_CATEGORIES: AchievementCategory[] = [
  'getting_started',
  'streaks',
  'collection',
  'secrets',
]

/** Form state for one reward; the pack is kept for single icons so the icon list can load. */
export type RewardDraft = {
  kind: AchievementRewardInput['kind']
  amount: string
  packId: string
  iconId: string
}

export type AchievementDraft = {
  nameEn: string
  nameRu: string
  descriptionEn: string
  descriptionRu: string
  slug: string
  emoji: string
  category: AchievementCategory
  visibility: AchievementVisibility
  sortOrder: string
  criteriaType: string
  /** Criteria params as typed in the form; '' means not set. */
  params: Record<string, string>
  rewards: RewardDraft[]
}

export function defaultParams(spec: CriteriaSpec | undefined): Record<string, string> {
  if (!spec) return {}
  return Object.fromEntries(
    spec.params.map((param) => [
      param.name,
      param.required && param.default !== null ? String(param.default) : '',
    ]),
  )
}

export function emptyDraft(specs: CriteriaSpec[]): AchievementDraft {
  const first = specs[0]
  return {
    nameEn: '',
    nameRu: '',
    descriptionEn: '',
    descriptionRu: '',
    slug: '',
    emoji: '🏆',
    category: 'collection',
    visibility: 'visible',
    sortOrder: '',
    criteriaType: first?.type ?? 'entry_count',
    params: defaultParams(first),
    rewards: [{ kind: 'tokens', amount: '10', packId: '', iconId: '' }],
  }
}

export function draftFromAchievement(achievement: StaffAchievementPublic): AchievementDraft {
  const { type, ...params } = achievement.criteria
  return {
    nameEn: achievement.labels.en ?? achievement.name,
    nameRu: achievement.labels.ru === achievement.labels.en ? '' : (achievement.labels.ru ?? ''),
    descriptionEn: achievement.descriptions.en ?? '',
    descriptionRu:
      achievement.descriptions.ru === achievement.descriptions.en
        ? ''
        : (achievement.descriptions.ru ?? ''),
    slug: achievement.slug,
    emoji: achievement.icon,
    category: achievement.category,
    visibility: achievement.visibility,
    sortOrder: String(achievement.sort_order),
    criteriaType: type,
    params: Object.fromEntries(Object.entries(params).map(([key, value]) => [key, String(value)])),
    rewards: achievement.rewards.map((reward) => ({
      kind: reward.kind,
      amount: reward.amount ? String(reward.amount) : '',
      packId: reward.pack_id ?? reward.icon_pack_id ?? '',
      iconId: reward.catalog_icon_id ?? '',
    })),
  }
}

export function buildCriteria(
  draft: AchievementDraft,
  spec: CriteriaSpec | undefined,
): AchievementCriteria {
  const criteria: AchievementCriteria = { type: draft.criteriaType }
  for (const param of spec?.params ?? []) {
    const raw = (draft.params[param.name] ?? '').trim()
    if (!raw) continue
    if (param.kind === 'int') {
      criteria[param.name] = Number(raw)
    } else {
      // Keep the choice's own type: weekdays are numbers, channels are strings.
      criteria[param.name] = param.choices.find((choice) => String(choice) === raw) ?? raw
    }
  }
  return criteria
}

function buildRewards(rewards: RewardDraft[]): AchievementRewardInput[] {
  return rewards.map((reward) => {
    if (reward.kind === 'tokens') {
      return { kind: reward.kind, amount: Number.parseInt(reward.amount, 10) || 0 }
    }
    if (reward.kind === 'icon_pack') {
      return { kind: reward.kind, pack_id: reward.packId || null }
    }
    return { kind: reward.kind, catalog_icon_id: reward.iconId || null }
  })
}

export function buildPayload(
  draft: AchievementDraft,
  spec: CriteriaSpec | undefined,
): StaffAchievementCreate {
  const sortOrder = Number.parseInt(draft.sortOrder, 10)
  return {
    labels: { en: draft.nameEn.trim(), ru: draft.nameRu.trim() || null },
    descriptions: { en: draft.descriptionEn.trim(), ru: draft.descriptionRu.trim() || null },
    category: draft.category,
    visibility: draft.visibility,
    criteria: buildCriteria(draft, spec),
    rewards: buildRewards(draft.rewards),
    emoji: draft.emoji.trim() || null,
    slug: draft.slug.trim() || null,
    sort_order: Number.isFinite(sortOrder) ? sortOrder : null,
  }
}
