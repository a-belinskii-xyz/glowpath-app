const UUID_HEX = /^[0-9a-f]{32}$/i

export function routeForStartParam(param: string): string | null {
  const value = param.trim()
  if (!value || value === 'home') {
    return '/'
  }
  if (value === 'create') {
    return '/entries/new'
  }
  if (value === 'create_daily') {
    return '/entries/new?from=telegram:daily_mood_reminder'
  }
  if (value === 'gallery') {
    return '/gallery'
  }
  if (value === 'tags') {
    return '/tags'
  }
  if (value === 'goals') {
    return '/goals'
  }
  if (value === 'profile') {
    return '/profile'
  }
  if (value === 'settings') {
    return '/tracker-settings'
  }
  if (value === 'onboarding') {
    return '/onboarding'
  }
  if (value === 'market') {
    return '/market'
  }
  if (value === 'achievements') {
    return '/achievements'
  }
  if (value.startsWith('entry_')) {
    const hex = value.slice('entry_'.length)
    if (!UUID_HEX.test(hex)) {
      return null
    }
    const id = [
      hex.slice(0, 8),
      hex.slice(8, 12),
      hex.slice(12, 16),
      hex.slice(16, 20),
      hex.slice(20),
    ].join('-')
    return `/entries/${id}`
  }
  return null
}
