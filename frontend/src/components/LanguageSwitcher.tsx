import { useLocale } from '../context/LocaleContext'
import { LOCALE_OPTIONS, type ApiLocale } from '../lib/locale'

type LanguageSwitcherProps = {
  id?: string
  className?: string
  /** Compact control for headers (no visible label). */
  compact?: boolean
}

export function LanguageSwitcher({
  id = 'language-switcher',
  className,
  compact = false,
}: LanguageSwitcherProps) {
  const { locale, setLocale, t } = useLocale()

  return (
    <label className={`language-switcher${compact ? ' language-switcher--compact' : ''}${className ? ` ${className}` : ''}`}>
      {!compact ? <span className="language-switcher-label">{t('common.language')}</span> : null}
      <select
        id={id}
        className="form-input language-switcher-select"
        value={locale}
        aria-label={t('common.language')}
        onChange={(event) => setLocale(event.target.value as ApiLocale)}
      >
        {LOCALE_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}
