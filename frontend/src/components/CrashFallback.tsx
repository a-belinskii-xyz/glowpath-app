import { t } from '../i18n/t'
import { getApiLocale } from '../lib/locale'

/**
 * Shown by the root Sentry.ErrorBoundary when React fails to render.
 * Lives outside LocaleProvider, so it reads the locale directly.
 */
export function CrashFallback() {
  const locale = getApiLocale()
  return (
    <div className="app-crash" role="alert">
      <p className="app-crash-title">{t(locale, 'errors.crashTitle')}</p>
      <button type="button" className="button" onClick={() => window.location.reload()}>
        {t(locale, 'errors.crashReload')}
      </button>
    </div>
  )
}
