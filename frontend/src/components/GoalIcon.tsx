import { useEffect, useState } from 'react'

import { getBuiltinMoodIconPath } from '../lib/moodBuiltinIcons'
import { getCachedGoalIconObjectUrl, getGoalIconObjectUrl } from '../lib/goalIconBlobUrl'
import { useCatalogIconBlobUrl } from '../lib/useCatalogIconBlobUrl'
import { DEFAULT_GOAL_STYLE, type GoalStyle } from '../types/goal'

type GoalIconProps = {
  style: GoalStyle
  className?: string
}

function useGoalIconBlobUrl(iconId: string | null): string | null {
  const [url, setUrl] = useState<string | null>(() =>
    iconId ? getCachedGoalIconObjectUrl(iconId) : null,
  )

  useEffect(() => {
    if (!iconId) {
      setUrl(null)
      return
    }

    const cached = getCachedGoalIconObjectUrl(iconId)
    if (cached) {
      setUrl(cached)
      return
    }

    let cancelled = false
    void getGoalIconObjectUrl(iconId)
      .then((objectUrl) => {
        if (!cancelled) {
          setUrl(objectUrl)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setUrl(null)
        }
      })

    return () => {
      cancelled = true
    }
  }, [iconId])

  return url
}

export function GoalIcon({ style, className }: GoalIconProps) {
  const uploadUrl = useGoalIconBlobUrl(style.icon_type === 'upload' ? style.icon : null)
  const catalogUrl = useCatalogIconBlobUrl(style.icon_type === 'catalog' ? style.icon : null)
  const fallbackEmoji = DEFAULT_GOAL_STYLE.icon

  if (style.icon_type === 'builtin') {
    return (
      <span className={className} aria-hidden>
        <img src={getBuiltinMoodIconPath(style.icon)} alt="" loading="lazy" />
      </span>
    )
  }

  if (style.icon_type === 'upload') {
    const uploadClassName = [className, 'mood-score-icon-upload'].filter(Boolean).join(' ')
    if (!uploadUrl) {
      return <span className={uploadClassName}>{fallbackEmoji}</span>
    }
    return (
      <span className={uploadClassName} aria-hidden>
        <img src={uploadUrl} alt="" loading="lazy" />
      </span>
    )
  }

  if (style.icon_type === 'catalog') {
    const catalogClassName = [className, 'mood-score-icon-upload'].filter(Boolean).join(' ')
    if (!catalogUrl) {
      return <span className={catalogClassName}>{fallbackEmoji}</span>
    }
    return (
      <span className={catalogClassName} aria-hidden>
        <img src={catalogUrl} alt="" loading="lazy" />
      </span>
    )
  }

  return <span className={className}>{style.icon}</span>
}
