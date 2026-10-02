import { useAchievementIconUrl } from '../lib/achievementIconBlobUrl'

const FALLBACK_ICON = '🏆'

type AchievementIconProps = {
  achievement: { id: string; icon_type?: string | null; icon?: string | null }
  /** Bumps the cached image after staff replace it. */
  version?: string
  className?: string
}

/** Emoji or uploaded image; the emoji shows while an image loads or if it fails. */
export function AchievementIcon({ achievement, version, className }: AchievementIconProps) {
  const isImage = achievement.icon_type === 'image'
  const url = useAchievementIconUrl(isImage ? achievement.id : null, version)
  const emoji = achievement.icon || FALLBACK_ICON
  return (
    <span className={['achievement-icon', className].filter(Boolean).join(' ')} aria-hidden="true">
      {isImage && url ? <img src={url} alt="" draggable={false} /> : emoji}
    </span>
  )
}
