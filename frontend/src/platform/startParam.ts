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
    return '/settings/diary?tab=tags'
  }
  if (value === 'goals') {
    return '/goals'
  }
  if (value === 'goal_reminder') {
    return '/goals?from=telegram:goal_reminder'
  }
  if (value === 'profile') {
    return '/profile'
  }
  if (value === 'settings') {
    return '/settings'
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
    const id = uuidFromHex(value.slice('entry_'.length))
    return id ? `/entries/${id}` : null
  }
  // "Note and tags" under a mood logged from the Telegram chat (GP-65).
  if (value.startsWith('edit_')) {
    const id = uuidFromHex(value.slice('edit_'.length))
    return id ? `/entries/${id}/edit` : null
  }
  return null
}

function uuidFromHex(hex: string): string | null {
  if (!UUID_HEX.test(hex)) {
    return null
  }
  return [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20),
  ].join('-')
}
