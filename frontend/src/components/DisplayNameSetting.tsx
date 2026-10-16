import { useEffect, useState } from 'react'

import { DisplayNameInput } from './DisplayNameInput'
import { PageErrorAlert } from './PageErrorAlert'
import { StableButtonLabel } from './StableButtonLabel'
import { useAuth } from '../context/AuthContext'
import { useLocale } from '../context/LocaleContext'
import { formatApiError } from '../lib/errors'

/** "What should we call you" card in account settings (GP-57). */
export function DisplayNameSetting() {
  const { t } = useLocale()
  const { user, updateDisplayName } = useAuth()
  const saved = user?.display_name ?? ''
  const [value, setValue] = useState(saved)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    setValue(saved)
  }, [saved])

  if (!user) {
    return null
  }

  const isDirty = value.trim() !== saved

  const handleSave = async () => {
    if (!isDirty || isSaving) {
      return
    }
    setError(null)
    setIsSaving(true)
    try {
      await updateDisplayName(value.trim())
    } catch (err) {
      setError(formatApiError(err, t, 'errors.failedSave'))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <section className="card profile-account" aria-labelledby="settings-name-heading">
      <h2 id="settings-name-heading" className="profile-settings-subheading">
        <label htmlFor="settings-display-name">{t('profile.displayNameTitle')}</label>
      </h2>
      <PageErrorAlert error={error} />
      <DisplayNameInput
        id="settings-display-name"
        value={value}
        disabled={isSaving}
        onChange={setValue}
        onSubmit={() => void handleSave()}
      />
      <p className="profile-field-hint">{t('profile.displayNameHint')}</p>
      {isDirty ? (
        <div className="display-name-actions">
          <button
            type="button"
            className="button"
            disabled={isSaving}
            onClick={() => void handleSave()}
          >
            <StableButtonLabel
              active={isSaving ? t('common.saving') : t('common.save')}
              labels={[t('common.save'), t('common.saving')]}
            />
          </button>
        </div>
      ) : null}
    </section>
  )
}
