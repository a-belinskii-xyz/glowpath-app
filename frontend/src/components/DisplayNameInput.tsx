import { useLocale } from '../context/LocaleContext'
import { getTelegramFirstName } from '../platform/telegram'

export const DISPLAY_NAME_MAX_LENGTH = 40

type DisplayNameInputProps = {
  id: string
  value: string
  disabled?: boolean
  onChange: (value: string) => void
  onSubmit?: () => void
}

/** Name field with a one-tap suggestion from the Telegram profile (GP-57). */
export function DisplayNameInput({ id, value, disabled, onChange, onSubmit }: DisplayNameInputProps) {
  const { t } = useLocale()
  const telegramName = getTelegramFirstName()?.slice(0, DISPLAY_NAME_MAX_LENGTH) ?? null
  const showSuggestion = Boolean(telegramName) && value.trim() === ''

  return (
    <div className="display-name-input">
      <input
        id={id}
        className="form-input"
        type="text"
        autoComplete="given-name"
        enterKeyHint="done"
        maxLength={DISPLAY_NAME_MAX_LENGTH}
        placeholder={t('profile.displayNamePlaceholder')}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && onSubmit) {
            event.preventDefault()
            onSubmit()
          }
        }}
      />
      {showSuggestion && telegramName ? (
        <button
          type="button"
          className="link-button display-name-suggestion"
          disabled={disabled}
          onClick={() => onChange(telegramName)}
        >
          {t('profile.displayNameFromTelegram', { name: telegramName })}
        </button>
      ) : null}
    </div>
  )
}
