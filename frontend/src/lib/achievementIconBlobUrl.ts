import { useEffect, useState } from 'react'

import { fetchAchievementIconBlob } from '../api/achievements'

const urlCache = new Map<string, string>()
const inflight = new Map<string, Promise<string>>()

/** Cache key: achievement id plus a version so staff see a replaced image at once. */
function cacheKey(achievementId: string, version?: string): string {
  return version ? `${achievementId}:${version}` : achievementId
}

function loadAchievementIconUrl(achievementId: string, version?: string): Promise<string> {
  const key = cacheKey(achievementId, version)
  const cached = urlCache.get(key)
  if (cached) return Promise.resolve(cached)
  const pending = inflight.get(key)
  if (pending) return pending
  const request = fetchAchievementIconBlob(achievementId)
    .then((blob) => {
      const url = URL.createObjectURL(blob)
      urlCache.set(key, url)
      return url
    })
    .finally(() => inflight.delete(key))
  inflight.set(key, request)
  return request
}

export function useAchievementIconUrl(
  achievementId: string | null,
  version?: string,
): string | null {
  const key = achievementId ? cacheKey(achievementId, version) : null
  const [loaded, setLoaded] = useState<{ key: string; url: string } | null>(null)

  useEffect(() => {
    if (!achievementId || !key || urlCache.has(key)) return undefined
    let cancelled = false
    loadAchievementIconUrl(achievementId, version)
      .then((url) => {
        if (!cancelled) setLoaded({ key, url })
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [achievementId, key, version])

  if (!key) return null
  return urlCache.get(key) ?? (loaded?.key === key ? loaded.url : null)
}
