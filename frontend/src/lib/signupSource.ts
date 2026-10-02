import { getTelegramStartParam, isTelegramMiniApp } from '../platform/telegram'

/** Where a new account came from (GP-21): `?utm_source=` on the site, `src_<label>` in Telegram. */
const STORAGE_KEY = 'mt_signup_source'
const START_PARAM_PREFIX = 'src_'

/** Remember the first `utm_source` the browser arrived with, so it survives the sign-in redirect. */
export function rememberSignupSourceFromUrl(): void {
  try {
    const source = new URLSearchParams(window.location.search).get('utm_source')?.trim()
    if (source && !localStorage.getItem(STORAGE_KEY)) {
      localStorage.setItem(STORAGE_KEY, source.slice(0, 64))
    }
  } catch {
    // Storage can be blocked; the account then counts as direct.
  }
}

export function getSignupSource(): string | undefined {
  if (isTelegramMiniApp()) {
    const param = getTelegramStartParam()
    return param?.startsWith(START_PARAM_PREFIX) ? param : undefined
  }
  try {
    return localStorage.getItem(STORAGE_KEY) ?? undefined
  } catch {
    return undefined
  }
}
