import type { MoodScoreStylePublic } from '../types/moodPreferences'

type MoodScoreIconProps = {
  style: MoodScoreStylePublic
  className?: string
}

export function MoodScoreIcon({ style, className }: MoodScoreIconProps) {
  if (style.icon_type === 'upload') {
    return (
      <img
        src={style.icon}
        alt=""
        className={className}
        loading="lazy"
      />
    )
  }

  return <span className={className}>{style.icon}</span>
}
